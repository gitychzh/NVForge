# R1933 (HM2 cc2): 紧急修复 — nv_gw R1928 半成品指数退避裸名 NameError (R1932 restart 显形), 补 import 根治

**铁律遵守**: 改前必有数据 / 改后必有验证 / 聚焦 nv_gw(40006) / 所有修改写入仓库 / 只改 HM2 不改 HM1 / 改 .py 必须 restart 非 up-d / 不碰 ms_gw(40007)

## 紧急性

R1932 (peer, commit 2cddb85) 改 oai_to_anth.py finish() 后 restart nv_gw (StartedAt 2026-07-19T13:20:36Z)。
restart 让一直潜在未触发的 **R1928 半成品指数退避裸名 NameError** 显形 → nv_gw 每个 glm5_2_nv 请求崩溃 → cc4101 毫秒级 RemoteDisconnected → 全切 ms。
链路半瘫痪: 0 真中断(ms 兜住)但 100% nv 数据空洞, fallback 飙升 17/10min, 违反正反馈核心(尽量多走 nv)。

## 数据 (改前, 本 session 21:31Z 拉取, R1932 restart 后 ~11min)

### 30min nv_gw 窗口
- SR = 28/32 = **87.5%** (200:28 / 502:4) — 低于 R1931 91.4%, 被 R1932 restart 窗口期 NameError 拉低
- 502 分类: zombie_empty_completion×3 + all_tiers_exhausted×1
- abs_cap 30min = 0 (R1918 方案0 持续归零)

### 6h 窗口 (样本大, restart 前后混合)
- SR = 608/649 = 93.7% (200:608 / 502:41) — restart 前撑住, restart 后窗口拉低
- 502: zombie×21 / all_tiers_exhausted×12 / abs_cap×4 / first_byte_timeout×4
- abs_cap 6h = 4 (与 R1931 完全一致)

### fallback (负向核心指标)
- 30min: **23** FALLBACK-OK (R1931=10, 飙升 2.3×)
- 10min: **17** (集中 R1932 restart 后窗口 21:28-21:31)
- 全毫秒级 RemoteDisconnected: "conn status=0 after 48ms/70ms/34ms" + 3× PRIMARY-BREAKER-OPEN
- 0 真中断 (全被 ms_gw 兜住), 0 fallback 失败

### NameError 铁证 (nv_gw 日志)
```
File "/app/gateway/upstream.py", line 1032, in _glm52_single_attempt
    if NVU_GLM52_EXP_BACKOFF and not upstream_timeout_override:
NameError: name 'NVU_GLM52_EXP_BACKOFF' is not defined
```
每个 glm5_2_nv NV-REQ 后必跟 Traceback + NameError, 持续 21:28-21:33 (restart 后 8-13min 未停)。

## 根因 (深度定位)

**经典"加了 config 忘 import" bug**:
1. R1928 (b7fbf30, 指数退避冻结轮) 在 config.py:522-527 定义 3 个新名字:
   - `NVU_GLM52_EXP_BACKOFF = os.environ.get("NVU_GLM52_EXP_BACKOFF", "0") == "1"` (默认 False, env 未设=关)
   - `NVU_GLM52_EXP_BACKOFF_STEPS = [60, 120, 240]`
   - `NVU_GLM52_EXP_BACKOFF_CAP = 240`
2. R1928 同时在 upstream.py:1031-1037 用裸名引用这 3 个名字 (per-key 指数退避逻辑)。
3. **但 upstream.py:35 的 `from .config import (...)` 具名列表没加这 3 个名字** → 裸名在 upstream.py 命名空间不存在 → NameError。
4. **为何 R1928→R1931 连续 3 轮 NOP 没触发**: STATE 记录"R1918→R1931 未再 restart", nv_gw 一直跑 R1918 旧字节码, R1928 写入的半成品源码**从未被加载**。R1932 restart 重新加载所有源码 → NameError 显形。
5. STATE 反复说"半成品冻结, env 未设=关, 从未激活" — **概念上对**(env 开关确实关), 但**漏了 import 层面**: Python 在 import 时就要求名字可解析, 不等运行时 if 条件求值。env 关只让 `==` 比较得 False, 但 `NVU_GLM52_EXP_BACKOFF` 这个名字本身在 upstream.py 就不存在 → import 阶段虽过(因 from import 容错? 不, 是 line 1032 运行时才求值), 运行到 `_glm52_single_attempt` 求值裸名 → NameError。

**这不是 R1932 (oai_to_anth 改动) 引入的, 是 R1928 半成品遗留 + R1932 restart 触发**。R1932 改动本身正确(见下)。

## R1932 (peer) 改动复核 (确认非回归源)

R1932 (commit 2cddb85) 改 oai_to_anth.py finish():
- zombie 路径 + 正常完成路径加 `if pending_stop_reason=="tool_use" and not saw_real_tool_call: final_stop="end_turn"`
- 镜像 R1839, 补 finish() 漏读 saw_real_tool_call flag, 根治 CC SDK "tool call could not be parsed (retry also failed)" session 中断
- 验证 (R1932 round 文件): py_compile OK / restart OK / E2E OK / 3 组单元测试通过
- 30min 502 的 finish_reason 复核: zombie 的 finish_reason="stop" (DB 记 NVCF 原始 stop, R1932 改的是 converter 输出给 CC 的 stop_reason, 不同层), 502 未增多 — R1932 改动本身无回归
- cc4101 + nv_gw 6h/1h 日志均无 "could not be parsed" 痕迹 (初步达成 R1932 目标, 待 cc2 jsonl 时序确认 restart 后无新增)

**R1932 改动正确, 唯一副作用是 restart 触发了 R1928 潜在 NameError**。

## 改动 (R1933)

文件: `/opt/cc-infra/proxy/nv-gw/gateway/upstream.py` (bind-mounted)
位置: line 35-62 的 `from .config import (...)` 具名列表, line 56 GLM52 组后补 3 个名字。

```python
# 改前 (line 56-57):
    NV_GLM52_MODE_CHAIN, NV_GLM52_SINGLE_US_PROXY, NV_GLM52_RR_US_PROXIES,
    KEY_MODE_BINDING, NV_GLM52_KEY_PROXY_MAP,

# 改后 (line 56-58):
    NV_GLM52_MODE_CHAIN, NV_GLM52_SINGLE_US_PROXY, NV_GLM52_RR_US_PROXIES,
    NVU_GLM52_EXP_BACKOFF, NVU_GLM52_EXP_BACKOFF_STEPS, NVU_GLM52_EXP_BACKOFF_CAP,  # R1928 指数退避 (R1933 补 import 修 NameError: 半成品裸名未入 import 列表, R1932 restart 显形)
    KEY_MODE_BINDING, NV_GLM52_KEY_PROXY_MAP,
```

backup: `upstream.py.bak.R1933` + `config.py.bak.R1933` (宿主机 bind-mount 路径)

**为何这是最小修复**:
- env NVU_GLM52_EXP_BACKOFF 未设 = "0" != "1" = False → `if NVU_GLM52_EXP_BACKOFF and ...` 条件 False → 指数退避逻辑**不激活**(STATE 冻结决定保持), 只是不再 NameError
- 补 import 让裸名可解析, R1928 半成品源码"冻结但可加载"状态恢复正确
- 不改 config.py, 不改 env, 不碰 oai_to_anth.py(R1932 改动保留), 不碰 ms_gw
- 风险极低: 只是把已定义的 config 名字加进 import 列表, 语义零变化

## 验证 (改后, restart 13:33:43Z)

1. **py_compile**: in-container `python3 -m py_compile upstream.py` OK
2. **restart** (非 up-d, 铁律): `docker compose restart nv_gw` → StartedAt = **2026-07-19T13:33:43Z** (fresh)
3. **/health**: ok (nv_num_keys=5, pexec_models 正常)
4. **docker ps**: nv_gw Up 8s / cc4101 Up / ms_gw Up
5. **NameError 根治** (核心验证): restart 后 2min 日志 `grep -c NameError` = **0** (之前每分钟数个)
6. **nv_gw 恢复处理请求**: restart 后日志显示正常 `[NV-REQ] mapped_model=glm5_2_nv ...` 流, 无 Traceback 跟随
7. **fallback 大降**: 30min=23 → restart 后 2min=3 (降 87%), 且唯一 PRIMARY-FAIL 是 `120s header/ttfb timeout` (正常超时路径, 非 NameError 崩溃), ms 27.4s 兜住 0 真中断
8. **0 真中断**: 所有 fallback 全 FALLBACK-OK, 0 fallback 失败 → CC 收 0 真 502

## 待下一轮窗口确认 (改后稳态, 需 10-30min 观察)

- [ ] cc4101 primary breaker 从 OPEN cool-down 恢复 HALF_OPEN → CLOSED, nv 流量回流 nv_gw (当前 breaker 仍 OPEN cool-down, 请求直走 ms, NV-REQ 暂少)
- [ ] nv_requests SR 回升至 R1931 的 91.4% 抖动区间 (NameError 消失后 502 应降)
- [ ] fallback 率回归 <10/30min 稳态
- [ ] cc2 jsonl 21:33Z 后无新增 "could not be parsed (retry also failed)" (R1932 目标 + R1933 不引入回归)

## 关联

- **R1928** (b7fbf30): 指数退避冻结轮, 写入半成品 config.py:522-527 + upstream.py:1031-1037 但漏 import → 本轮根因
- **R1932** (2cddb85, peer): 改 oai_to_anth finish() saw_real_tool_call, restart 触发 R1928 NameError 显形 (非 R1932 引入)
- **R1918**: nv_gw 上次 restart (StartedAt 10:42:20Z → R1932 改 13:20:36Z → R1933 改 13:33:43Z)
- 监督者 21:00/21:15 指数退避方案: NVU_GLM52_EXP_BACKOFF 是其开关, 本轮只修 NameError 让半成品"可安全冻结", **未激活**(env 仍关), 激活决策仍冻结

## 教训

- **半成品代码即使"冻结(env 关)"也必须保证 import 完整** — Python 运行时求值裸名, 不等 if 条件。冻结的代码会被下次 restart 加载, import 缺漏 = 潜在定时炸弹。
- **连续 NOP 轮(R1929-R1931)未 restart 是 NameError 没早暴露的直接原因** — 冻结半成品应该至少 restart 一次验证"可加载", 否则潜在 bug 会延迟到他人 restart 时显形(如本轮 R1932 背锅)。
