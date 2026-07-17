# R1648c: nv_gw 5key全坏→ms_gw fallback (glm5_2_nv 专) + nv breaker

> R1648 框架第 3 轮 (a→**c**→d→e→f)。承接 R1648b (nv_gw `/v1/messages` anthropic 端点)。
> 本轮把 nv→ms fallback 责任从 cc4101 **下沉回 nv_gw**（R753 曾把跨后端 fallback 移到适配器层,
> 现框架反向归位）。只改 **HM2**, 铁律 "只改 HM1 不改 HM2" 本系列破例豁免。

## 一、动机

R1648 目标架构: cc4101 瘦成纯透传 (R1648e), 所有 nv↔ms 兜底逻辑下沉到 nv_gw (40006)。
本轮先把 fallback 能力搬进 nv_gw 本体, 让 40006 在 NVCF 5key×mode 全挂时直接切 ms_gw
返回 200, 不再依赖 cc4101 兜底。R1643 的 cc4101 fallback 暂留 (R1648e 删除)。

NVCF pexec/integrate 间歇降级 (R1444 记录): empty200/SSL_EOF 风暴期单 mode 无退路会死循环。
R1421 单 mode_pexec_us_rr → R1444 改 5mode 递进链救回, 但若 5key 全坏 NVCF 整体挂,
nv_gw 仍返 all_keys_exhausted 致 5xx。本轮加 ms_gw 兜底 + breaker 短路。

## 二、改动 (4 文件 + compose env)

### 1. `gateway/config.py` (md5 d61ce83786f946165e0af6f6fb761af3)
PEER_FALLBACK 块后、stream-deadline 块前新增:
```python
NVU_MS_FALLBACK_ENABLED = os.environ.get('NVU_MS_FALLBACK_ENABLED', '0') == '1'
NVU_MS_FALLBACK_URL = os.environ.get('NVU_MS_FALLBACK_URL', 'http://ms_gw:40007/v1/chat/completions').rstrip('/')
NVU_MS_FALLBACK_TOKEN = os.environ.get('NVU_MS_FALLBACK_TOKEN', 'ms-gw-token')
NVU_MS_FALLBACK_MODEL = os.environ.get('NVU_MS_FALLBACK_MODEL', 'glm5_2_ms')
NVU_MS_FALLBACK_TIMEOUT = int(os.environ.get('NVU_MS_FALLBACK_TIMEOUT', '120'))
NVU_MS_FALLBACK_FAIL_THRESHOLD = int(os.environ.get('NVU_MS_FALLBACK_FAIL_THRESHOLD', '15'))
NVU_MS_FALLBACK_SKIP_S = int(os.environ.get('NVU_MS_FALLBACK_SKIP_S', '30'))
NVU_MS_FALLBACK_MODELS = {m.strip() for m in os.environ.get('NVU_MS_FALLBACK_MODELS', 'glm5_2_nv').split(',') if m.strip()}
```

### 2. `gateway/nv_breaker.py` (新, md5 edfee0dad9967c13764cade8b7935415)
镜像 cc4101 `circuit.py` (R824d)。`_lock`/`_fail_count`/`_open_until` 模块级状态。
- `is_ms_fallback_open()`: True iff OPEN 在 cooldown 内 (CLOSED/HALF_OPEN 返 False, 允许 probe nv)
- `record_nv_success()`: nv 链真成功 → CLOSED
- `record_nv_failure()`: all_keys_exhausted → CLOSED 累加到 threshold 则 OPEN; OPEN/HALF_OPEN 失败 re-arm
- `breaker_state()`: (state, fail_count, seconds_left) 调试用
- **只 all_keys_exhausted 计数** (chain-level); 单 key SSL/timeout 链内自愈不算, client_4xx 不入

### 3. `gateway/upstream.py` (md5 1e247423a619a7fd27337cdfd2082e24)
- import NVU_MS_FALLBACK_* + `from . import nv_breaker`
- 新增 `_ms_fallback_request(oai_body, mapped_model, request_id, metrics, t_start)` → `(success, UpstreamResult|None)`:
  深拷贝 oai_body, 设 `fb_body["model"]=NVU_MS_FALLBACK_MODEL` (避免 ms_gw 404), POST ms_gw
  (Authorization: Bearer {token}), 5xx/429 返 (False,None); 成功返 UpstreamResult (.resp/.conn
  指向 ms_gw openai 流, .upstream_type="ms_fallback", .tier_model=glm5_2_ms, .nv_key_idx=-1,
  填 metrics ms_fallback_used/ms_fallback_ms/ms_fallback_status/upstream_type/tier_model/
  fallback_occurred/fallback_from/fallback_to)
- `execute_request` START (breaker OPEN 短路): glm5_2_nv + breaker open → `_ms_fallback_request`,
  成功则 return (直走 ms 省 120s 链等待); ms 失败 fall through 走 nv 链
- `execute_request` END (return final_result 前): glm5_2_nv + MS_ENABLED + not all_429 →
  `_ms_fallback_request`; 成功 → record_nv_failure + return ms_result; 失败 → record_nv_failure + return nv final_result
- 日志 tag: NV-MS-FB-ATTEMPT / NV-MS-FB-OK / NV-MS-FB-FAIL / NV-MS-FB-SERVED

### 4. `gateway/handlers.py` (md5 e910b110cc1f8b88f9b0eb6ab5a38bfa)
- import `record_nv_success as _nv_breaker_record_success`
- `_handle_openai_nv` 与 `_handle_messages_anthropic` 两处 execute_request 后加:
  ```python
  # R1648c: nv-chain success closes the nv→ms breaker (HALF_OPEN probe → CLOSED).
  if result.success and getattr(result, "upstream_type", "") != "ms_fallback":
      _nv_breaker_record_success()
  ```
  (ms_fallback 成功不算 nv 成功, 不关 breaker)

### 5. `docker-compose.yml` nv_gw 段 (PEER_FALLBACK_TIMEOUT 后)
```yaml
- NVU_MS_FALLBACK_ENABLED=0          # 默认关, R1648c 验证时临时开
- NVU_MS_FALLBACK_URL=http://ms_gw:40007/v1/chat/completions
- NVU_MS_FALLBACK_TOKEN=ms-gw-token
- NVU_MS_FALLBACK_MODEL=glm5_2_ms
- NVU_MS_FALLBACK_TIMEOUT=120
- NVU_MS_FALLBACK_FAIL_THRESHOLD=15
- NVU_MS_FALLBACK_SKIP_S=30
- NVU_MS_FALLBACK_MODELS=glm5_2_nv
```

## 三、架构决策

- **没整搬 cc4101 stream.py** (897 行缠结 conversion+stall-watcher+breaker)。只抽纯转换
  (R1648b 的 OaiSseToAnthropicConverter), 复用 nv_gw 自己更新的 stream 基建 (R850/R1407/R1627)。
- **fallback 在 execute_request 内做** (返 UpstreamResult, .resp 指向 ms_gw openai 流),
  而非 handler 层。这样 handler 现有 stream/collect+convert 路径同时服务 openai 和
  `/v1/messages` 两条路, 不重复 fallback 逻辑。
- **record_nv_success 在 handler 层** (2 处) 而非 execute_request 的 N 个成功 return 点。
- **只 glm5_2_nv fallback**: dsv4p_nv/kimi_nv 模型不对应 ms_gw (ms_gw 有 glm5_2_ms + dsv4p_ms,
  但 dsv4p 走 ms 语义不同, 本轮保守只兜 glm5.2 同族)。

## 四、验证 (HM2, 2026-07-17 10:57)

用 `docker-compose.override.yml` 临时把 5 NV key 全设坏值 + `ENABLED=1` + `FAIL_THRESHOLD=1`,
recreate nv_gw:

| # | 测试 | 结果 |
|---|---|---|
| 1 | openai path glm5_2_nv (ENABLED=0 回归) | ✅ model=z-ai/glm-5.2 content=pong |
| 2 | /v1/messages anthropic path (ENABLED=0 回归) | ✅ anthropic message JSON, content=pong |
| 3 | 5坏key + ENABLED=1 + THRESHOLD=1, openai path | ✅ **model=glm5_2_ms** 200 (ms 兜底) |
| 4 | 同上 /v1/messages path | ✅ anthropic 200, thinking 块+signature, 走 ms |
| 5 | 连续 2nd 请求 (42s 后, HALF_OPEN) | ✅ probe nv 失败→re-OPEN, 仍 ms 200 |
| 6 | 撤 override + 恢复真 key + ENABLED=0 | ✅ nv 正常返 200 model=z-ai/glm-5.2 |

日志确认 (3 次触发):
```
[NV-MS-FB-ATTEMPT] nv chain all_keys_exhausted for glm5_2_nv (req=763f3778), attempting ms_gw fallback (breaker=CLOSED)
[NV-MS-FB-OK] ms_gw fallback success for glm5_2_nv after 1895ms (req=763f3778), relaying openai SSE via UpstreamResult
[NV-MS-FB-SERVED] ms_gw served glm5_2_nv fallback (req=763f3778), nv breaker recorded failure (state=OPEN)
[NV-MS-FB-ATTEMPT] ... (breaker=HALF_OPEN)   ← 30s skip 后 probe
[NV-MS-FB-SERVED] ... state=OPEN             ← probe 失败 re-OPEN
```
breaker 状态机: CLOSED →(1 fail, threshold=1)→ OPEN →(30s)→ HALF_OPEN →(probe fail)→ re-OPEN. ✅ 符合设计.

> 调试坑: `docker exec nv_gw python3 -c "...breaker_state()"` 报 CLOSED 是**新进程**模块级
> 状态 (每个 `docker exec python3` 起 fresh interpreter, `_fail_count=0`)。live nv_gw 进程
> 的真实状态以日志为准 (state=OPEN/HALF_OPEN)。

## 五、参数表

| 参数 | 值 | 说明 |
|---|---|---|
| NVU_MS_FALLBACK_ENABLED | 0 | 默认关; R1648e 后长跑观察再开 |
| NVU_MS_FALLBACK_URL | http://ms_gw:40007/v1/chat/completions | ms_gw openai 端点 |
| NVU_MS_FALLBACK_MODEL | glm5_2_ms | model 字段换这个避免 ms_gw 404 |
| NVU_MS_FALLBACK_TIMEOUT | 120 | ms_gw 请求超时 |
| NVU_MS_FALLBACK_FAIL_THRESHOLD | 15 | 连续 15 次 all_keys_exhausted → OPEN |
| NVU_MS_FALLBACK_SKIP_S | 30 | OPEN 冷却后 HALF_OPEN probe |
| NVU_MS_FALLBACK_MODELS | {glm5_2_nv} | 只 glm5_2_nv 走 fallback |

## 六、后续

- **R1648d**: ms_gw 加 `/v1/messages` anthropic 端点 (copy format pkg, 同 R1648b 结构)。
- **R1648e**: cc4101 瘦成纯透传 (删 R1643 fallback + breaker, handlers 透传 anthropic body 到 nv_gw:40006/v1/messages)。届时开 NVU_MS_FALLBACK_ENABLED=1 长跑。
- **R1648f**: 切换 + ≥6h 长跑观察, 更新 compose + memory。HM1 不同步 (后续轮)。
- HM1 nv_gw 代码仅到 R1416, 未含 R1648b/c — 本轮不推 HM1。
