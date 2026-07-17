# R1673: nv_gw 超大 input big-input breaker (283k 死循环根治)

**状态**: 已部署 HM2, 端到端验证通过 (115s/req → ~9s/req). 只改 HM2 (R1648 系列豁免铁律).
**提交**: (本轮 commit)

## 背景 (R1672 补遗深挖的根因)

R1672 缩了 first-byte deadline (90→45/120→60), 但只治了"两阶段挂死"的第 2 阶段
(integrate 200-then-hang ~45s). 第 1 阶段 (pexec getresponse() ~62s, deadline 触不到)
无法简单缩短 — 正常 >200k 成功请求 TTFB max=58s, 缩 getresponse 超时会误杀正常大请求.

最深根因: **NVCF glm5.2 对 ~250k+ chars (~8万 token) 超大 input 系统性 200-then-hang**
(或 200+极少内容+stop = zombie_empty_completion). CC 反复发同一个 283k 请求 (283274/284370
两值反复), 每次拖满 ~115s (pexec 62s + integrate 45s 两段叠加), 死循环达 1h+, DB 8 条
同 input_chars 全 502, 整体 SR 骤降至 43.8% (基线 95.7%).

止血走不通 (R1672 已证) → 本轮走"快速失败": 检测到超大 input 系统性坏 → 跳过 nv 链
直走 ms_gw (ModelScope glm5_2_ms, 实测能服务 400k input), 省 ~115s/次 → ~9s.

## 数据锚点 (HM2 近6h, 改前)

| input 段 | 请求数 | 成功 | SR |
|---|---|---|---|
| <250k 各档 | 多 | 多 | 71-100% |
| 250-300k | 24 | 7 | **29.2%** (17 hang) |
| 283274 (精确值) | 10 | 0 | **0%** (10/10 失败, max 115s) |
| >300k | 少 | — | 87.5% (样本少, 非系统性) |

→ 触发判据必须是"连续失败"而非单纯大小 (>300k 偶发成功, 不能一刀切).
→ 阈值 250000 (250-300k 桶 SR 骤降的拐点).
→ ms_gw 能服务 280k/400k input (200 OK 返内容), 是可行降级目标.

## 改动 (只 HM2 `/opt/cc-infra/proxy/nv-gw/gateway/`)

### 1. 新增 `big_input_breaker.py` (3707B)
独立于 R1648c `nv_breaker.py`. 两者维度互补:
- `nv_breaker` (R1648c): 看"全 key 挂"(整体健康), 阈值 15 次, cooldown 30s.
- `big_input_breaker` (本轮): 看"特定 input 段系统性坏"(按 input 维度), 阈值 3 次,
  cooldown 180s.

模块级状态 (`_lock`/`_fail_count`/`_open_until`), 同 nv_breaker 模式. 接口:
- `is_big_input(input_chars)` — input > NVU_BIG_INPUT_THRESHOLD (默认 250000)?
- `is_big_input_open()` — breaker 是否 OPEN (cooldown 内)?
- `record_big_input_failure(error_type)` — 超大 input nv 链 hang 失败累计; 达 N → OPEN.
- `record_big_input_success()` — 超大 input nv 链成功 → CLOSED 重置.
- `big_input_breaker_state()` — 调试快照 (注意: docker exec 起新进程看的是 fresh 状态,
  非 live nv_gw 进程真实状态, 同 R1648c nv_breaker 坑).

`_HANG_ERRORS` 计入的失败类型 (R1673b 补 `zombie_empty_completion`):
```python
{"stream_first_byte_timeout", "stream_no_content_gap", "empty_200",
 "all_keys_exhausted", "zombie_empty_completion"}  # 283k 实测多走 zombie 路径
```
(全 429 是 key 级限流, 非 hang, 不计入 — 走 nv_breaker 维度.)

### 2. `upstream.py` 4 处集成
- **import**: `from . import big_input_breaker`
- **execute_request 入口** (R1648c nv_breaker OPEN 块之后, R753 tier_order 之前):
  若 input>250k 且 big_input breaker OPEN → 直走 `_ms_fallback_request` (复用 R1648c),
  跳过 nv 链 (省 ~115s). ms 失败则落回 nv 链 (HALF_OPEN 探活语义).
- **tier 成功路径** (NV-GLM52-SUCCESS 后): 超大 input nv 链成功 → `record_big_input_success`
  → CLOSED. (HALF_OPEN probe 成功也经此.)
- **final_result 失败路径** (R1648c ms fallback 块后): 超大 input nv 链 hang (empty_200/
  all_keys_exhausted) → `record_big_input_failure`. (全 429 不计.)

### 3. `handlers.py` 5 处集成 (zombie 路径记录)
**关键发现**: 283k 死循环的主路径是 `zombie_empty_completion` — execute_request 返
success (NVCF 200+极少内容+stop), 但 handlers 层 R840/R852b 判 zombie (content_chars<50
+ 无真 tool_calls + 大 input) → 发 content_filter error chunk 让 CC 重试. 这个失败在
execute_request 出口记不到 (execute 返 success), 必须在 handlers 的 zombie 检测点记.
5 处:
- L481: 非流式 zombie (openai /v1/chat/completions)
- L1025: /v1/messages 流式 zombie (NV-ANTH-ZOMBIE)
- L1175: /v1/messages 非流式 zombie (collection)
- L1561: 透传流式 zombie error-chunk 发射点 (NV-UPSTREAM-ERROR-CHUNK, zombie_detected=True)
- import: `from . import big_input_breaker`

**坑1 (已修)**: `_stream_openai_passthrough(self, resp, conn, metrics, t_start, request_model)`
函数签名无 `request_id` 参数, edit3 `_log` 引用 `request_id` → NameError. 改用
`metrics.get('request_id','?')`. (NameError 被 `except Exception` 吞, 但 record 在 _log 前
已执行, breaker 仍记到 — 只是日志行没出.)

### 4. `config.py` env (4 个)
```python
NVU_BIG_INPUT_THRESHOLD = int(os.environ.get('NVU_BIG_INPUT_THRESHOLD', '250000'))
NVU_BIG_INPUT_FAIL_N    = int(os.environ.get('NVU_BIG_INPUT_FAIL_N', '3'))
NVU_BIG_INPUT_COOLDOWN_S= int(os.environ.get('NVU_BIG_INPUT_COOLDOWN_S', '180'))
NVU_BIG_INPUT_MODELS    = {... 'glm5_2_nv'}  # 仅 glm5_2_nv (其他模型无 ms 对应)
```

### 5. `docker-compose.yml` env (4 个 + 启用 ms fallback)
```yaml
- NVU_MS_FALLBACK_ENABLED=1   # R1648c 之前=0, 本轮开 (big_input 无处可降则无效)
- NVU_BIG_INPUT_THRESHOLD=250000
- NVU_BIG_INPUT_FAIL_N=3
- NVU_BIG_INPUT_COOLDOWN_S=180
- NVU_BIG_INPUT_MODELS=glm5_2_nv
```
**副作用**: 开 `NVU_MS_FALLBACK_ENABLED=1` 同时激活 R1648c nv_breaker (全 key 挂→ms,
阈值 15). 这是 R1648c 的自然完成 (设计本就为此, 之前关是待验证). 与 R1673 互不冲突.

## 验证 (HM2, 改后)

### 单元 (breaker 逻辑)
```
init: CLOSED (0)
2 fails (need 3): CLOSED (2) open? False
3 fails: OPEN (3, 179) open? True
after success: CLOSED (0)
429 not counted: CLOSED (0)
```
✅ 3 次 hang → OPEN (179s cooldown), 成功 → CLOSED, 429 不计.

### 端到端 (FAIL_N=1 加速验证, 后恢复 3)
两个 283k stream 请求:
- req1 (probe): 18.3s, content_filter chunk (zombie 检测 → record failure → OPEN)
- req2 (OPEN 后): **9.3s** (vs ~115s), 5708B 真内容, id=`chatcmpl-ff2963e9...` → **ms_gw 服务**

日志三段完整:
```
NV-BIGINPUT-FAIL    stream zombie glm5_2_nv input=283147c breaker=('OPEN',1,179)
NV-BIGINPUT-FB-OPEN breaker OPEN input=283147c skipping nv chain (~115s hang) serving ms_gw
NV-MS-FB-OK         ms_gw fallback success after 9241ms relaying openai SSE
```
✅ 死循环 115s/req → ~9s/req.

### ms_gw 可达性 + 大 input 服务能力
- `curl ms_gw:40007/health` 200 ✅
- nv_gw 容器内 `http://ms_gw:40007/health` 200 (cc-net 互通) ✅
- ms_gw 服务 280k input: status 200, 返内容 ✅ (降级目标可行)

## 参数表

| 参数 | 值 | 含义 |
|---|---|---|
| NVU_BIG_INPUT_THRESHOLD | 250000 | input chars 超大段阈值 (250-300k SR 骤降拐点) |
| NVU_BIG_INPUT_FAIL_N | 3 | 连续 hang 失败次数 → OPEN (保守, 避免偶发误拒) |
| NVU_BIG_INPUT_COOLDOWN_S | 180 | OPEN 后冷却 (直走 ms 的窗口) |
| NVU_BIG_INPUT_MODELS | glm5_2_nv | 仅 glm5.2 (有 ms 对应) |
| NVU_MS_FALLBACK_ENABLED | 1 | (副作用) 激活 R1648c nv_breaker |

## 风险与回退
- **误拒**: 正常 >250k 请求偶发 hang 累计 3 次 → 180s 内直走 ms (ms 是 glm5.2 同系,
  内容质量近似, 非降级到弱模型). 可接受.
- **回退**: `NVU_MS_FALLBACK_ENABLED=0` 同时关掉 R1648c + R1673 (big_input 无处可降则
  不触发 fast-fail, 落回原 nv 链).
- **HM1 未同步**: 本轮只改 HM2 (R1648 系列). HM1 nv_gw 仍无 big_input breaker.

## 后续
- R1648e: cc4101 纯透传 (删 R1643 fallback + breaker; handlers 转发到 nv_gw:40006/v1/messages
  主 + ms_gw:40007/v1/messages 备; 启用 NVU_MS_FALLBACK_ENABLED=1 长跑).
- R1648f: 切换 + ≥6h 长跑, 更新 compose + memory, HM1 同步.
