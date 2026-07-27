# R2406 (HM2→HM1): UPSTREAM_TIMEOUT 24→28

## 改前数据 (HM1, post-R2405 FASTBREAK 3→4, ~1h window)

### nv_gw health
- `/health` → `{"status": "ok", "proxy_role": "passthrough", "nv_num_keys": 5}`
- Container `nv_gw` running, latest env:
  - `NVU_PEXEC_TIMEOUT_FASTBREAK=4` (R2405)
  - `NVU_EMPTY_200_FASTBREAK=2` (R2404)
  - `NVU_TIER_BUDGET_GLM5_2_NV=255` (R2399)
  - `UPSTREAM_TIMEOUT=24` (current, was set to 24 long ago)

### DB 窗口 (nv_requests)

| Window | mapped_model | total | ok | 502 | SR% |
|--------|-------------|-------|----|-----|-----|
| 2h | glm5_2_nv | 11 | 4 | 7 | 36.4% |
| 2h | kimi_nv | 11 | 5 | 6 | 45.5% |
| 1h | glm5_2_nv | 5 | 2 | 3 | 40.0% |
| 1h | kimi_nv | 4 | 2 | 2 | 50.0% |
| 30min | glm5_2_nv | 2 | 1 | 1 | 50.0% |
| 30min | kimi_nv | 3 | 1 | 2 | 33.3% |

### 错误级 (nv_tier_attempts, 1h)
| error_type | count | tier |
|------------|-------|------|
| NVCFPexecTimeout | 2 | glm5_2_nv (2x) |
| NVCFPexecSSLEOFError | 2 | glm5_2_nv (1x), kimi_nv (1x) |
| empty_200 | 2 | kimi_nv (2x) |

### 日志关键模式

**glm5_2_nv ATE with 6 consecutive timeouts at ~25s (post-R2405):**
```
k4 timeout: attempt=25133ms total=25135ms
k5 timeout: attempt=25101ms total=50237ms
k1 timeout: attempt=25511ms total=75749ms
k2 → 429 rate_limit (breaking FASTBREAK chain)
k3 timeout: attempt=24970ms total=103187ms
k4 timeout: attempt=24987ms total=128175ms
k5 timeout: attempt=25953ms total=154130ms
```
All 6 timeouts clustered at 24.9-25.9s — exactly at the UPSTREAM_TIMEOUT=24 boundary (24s + 1-2s state machine overhead).

NVCF is clearly responding slowly (non-thinking glm5_2) but the client cuts it off at 24s. The 429 on k2 broke the FASTBREAK=4 chain, so all 5 keys were exhausted over 154s. If NVCF had been allowed 28s, some of these 6 timeouts might have completed.

**kimi_nv empty_200 cascade (post-R2405):**
```
k2 empty 200 → k3 empty 200 → EMPTY-FASTBREAK=2 triggered → fast-break (saved keys)
```
EMPTY_200_FASTBREAK=2 works correctly. 2 consecutive empty_200 → fast-break.

**kimi_nv zombie empty completion:**
```
k1 success → zombie_empty: finish_reason=stop but content_chars=17 reasoning_chars=207 < 50
```
Not a timeout issue; zombie detection triggered correctly.

## 问题分析

### 1. UPSTREAM_TIMEOUT=24 是活跃瓶颈

所有6个 NVCFPexecTimeout 都精确落在 ~25s（24s 超时 + 1-2s 状态机开销）。这不是 NVCF 完全不响应（那会是连接超时），而是 NVCF 正在处理但处理时间超过 24s。

glm5_2（非思考模型）在 NVCF 上的 pexec 时间分布：
- 成功请求：14-16s（正常路径）
- 失败请求：24s 被 cut（超时路径）
- 推论：NVCF 在 24-28s 区间内完成的可能性存在，但被 24s 超时提前切断了

### 2. 28s 是安全的增量

+4s（24→28）的影响：
- 不改变成功路径：成功请求在 14-16s，远低于 28s
- 对 FASTBREAK 的影响：FASTBREAK=4 最大用时从 ~101s → ~119s（4×28s+3×5s），仍远低于 glm5_2_nv tier budget=255s
- 对 thinking 模型无影响：kimi_nv 有独立的 NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66s
- 不改变 empty_200 行为：empty_200 是 content-level 问题，不受 timeout 影响

### 3. 为什么不改到 30s?

30s 是 config.py 的 default。但从 24→28 是保守的增量，观察效果后再考虑 28→30。
- 24→28 = +16.7% timeout，风险极低
- 28→30 = +7.1% 进一步增量，可在下一轮评估

### 4. 为什么 FASTBREAK=4 没触发？

429 on k2 打破了连续 timeout 的链。FASTBREAK 需要连续 pexec timeout，但 429 是 rate_limit 错误，重置了计数器。这是 FASTBREAK 的已知局限：非 timeout 的中间错误让计数器重置。

## 修改

### `/opt/cc-infra/docker-compose.yml` (HM1)

nv_gw 容器，行 516:
```diff
- UPSTREAM_TIMEOUT=24
+ UPSTREAM_TIMEOUT=28  # R2406 (HM2→HM1): 24→28. 2h post-R2405 DB: glm5_2_nv 4/11=36.4% SR, all 6 NVCFPexecTimeout clustered at ~25s (client-cut at 24s UPSTREAM_TIMEOUT). Success requests avg 14-16s. +4s headroom converts edge-case 24-28s pexec completions into success. Budget-safe: FASTBREAK=4 max ~119s (was ~101s), still well under glm5_2_nv=255s. Thinking models unaffected (own 66s timeout). Single param; iron law: only HM1.
```

## 执行

```bash
# Applied on HM1 only (iron law: never modify HM2)
ssh -p 222 opc_uname@100.109.153.83
  sed -i 's/UPSTREAM_TIMEOUT=24/UPSTREAM_TIMEOUT=28  # R2406 .../' /opt/cc-infra/docker-compose.yml
  docker compose -f /opt/cc-infra/docker-compose.yml up -d --no-deps nv_gw
```

- Container `nv_gw` 重建并启动成功
- `curl localhost:40006/health` → `{"status": "ok", ...}` ✅
- `docker exec nv_gw env | grep UPSTREAM_TIMEOUT` → `28` ✅
- 只改了这一个参数, 无其他修改

## 预期改善

- glm5_2_nv: 当 NVCF pexec 在 24-28s 区间完成时，不再被 client 提前切断
- 预期 NVCFPexecTimeout 从 100% 的 25s-cluster → 部分 25-28s 的请求变成成功
- SR 改善目标：glm5_2_nv 从 36.4% → 40-50%（+4-14pp）
- 不影响成功路径（14-16s 正常完成）
- 不影响 thinking 模型（kimi_nv 66s 独立 timeout）
- 不影响 empty_200 或 SSLEOF 错误（非 timeout 类）
- 预算安全：FASTBREAK=4 最大 ~119s << glm5_2_nv budget=255s

## ⏳ 轮到HM1优化HM2  ← 脚本检测此标记