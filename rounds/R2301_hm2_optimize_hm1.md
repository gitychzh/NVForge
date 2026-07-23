# R2301 (HM2→HM1): kimi_nv tier budget 255→120 tighten empty_200 waste

**Timestamp**: 2026-07-23 23:10 UTC
**Round type**: 单参数优化
**Author**: opc2_uname (HM2)
**Iron rule**: Only change HM1, never HM2

## 1. 触发

- 检测脚本输出: `HEAD is now at 58f71b0 R2300 (HM2->HM1): TIER_TIMEOUT_BUDGET_S 370→415 unlock dsv4p_nv fallback for kimi_nv ATE`
- 最新 commit author = `opc_uname` (HM1), 脚本判定轮到 HM2 执行优化

## 2. 数据采集 (HM1 nv_gw, 2026-07-23 22:50 UTC)

### 2.1 kimi_nv 6h 请求统计

| metric | value |
|--------|-------|
| total requests | 48 |
| success (200) | 18 (37.5% SR) |
| ATE (all_tiers_exhausted) | 22 |
| zombie_empty_completion | 7 |
| NVStream_IncompleteRead | 1 |
| success avg duration | 40,229ms (p50=29s, p90=87s) |
| ATE avg duration | 204,731ms |
| recent ATE duration | 124,586ms (FASTBREAK=2 × ~62s/empty_200) |

### 2.2 kimi_nv tier_attempts 6h 错误分布

| error_type | count | avg_ms |
|------------|-------|--------|
| empty_200 | 9 | ~62,000 |
| NVCFPexecRemoteDisconnected | 5 | 43,391 |
| NVCFPexecSSLEOFError | 3 | 5,005 |

### 2.3 ATE duration buckets

| bucket | count | avg_ms |
|--------|-------|--------|
| 120-125s | 7 | 124,200 |
| 125-255s | 14 | 150,100 |
| 255-370s | 1 | 365,223 |
| >370s | 5 | 370,196 |

### 2.4 关键日志 (22:41-22:47 UTC)

```
22:41:18 NV-REQ kimi_nv stream=True tier_chain=['kimi_nv']
22:41:18 NV-INJECT-THINKING reasoning_effort='low'
22:41:18 NV-KEY k3 → NVCF pexec (attempt 1/7)
22:42:24 NV-EMPTY-200 k3 → 200 Content-Length:0 (stream) [66s]
22:42:24 NV-EMPTY-CYCLE k3 cooling 10s, cycling
22:42:24 NV-KEY k4 → NVCF pexec (attempt 2/7)
22:43:00 NV-CONN k4 connection error: RemoteDisconnected [36s]
22:43:00 NV-KEY k5 → NVCF pexec (attempt 3/7)
22:44:05 NV-EMPTY-200 k5 → 200 Content-Length:0 (stream) [65s]
22:44:05 NV-EMPTY-FASTBREAK 2 consecutive ≥ threshold 2, fast-break
22:44:05 NV-TIER-FAIL all 5 keys failed: empty200=2, other=1, elapsed=167s
22:44:05 NV-ALL-TIERS-FAIL ABORT-NO-FALLBACK
22:44:05 NV-PEER-FB peer-originated (hop=1) also all_tiers_exhausted → 502
```

### 2.5 容器 env (变更前)

| param | value | source |
|-------|-------|--------|
| NVU_TIER_BUDGET_KIMI_NV | 255 | R2299 |
| NVU_TIER_BUDGET_DSV4P_NV | 160 | R2273 |
| NVU_TIER_BUDGET_GLM5_2_NV | 210 | R2291 |
| TIER_TIMEOUT_BUDGET_S | 415 | R2300 |
| PROXY_TIMEOUT | 500 | — |
| NVU_PEER_FALLBACK_TIMEOUT | 122 | — |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | — |
| NVU_EMPTY_200_FASTBREAK | 2 | R2270 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | — |
| UPSTREAM_TIMEOUT | 24 | — |

## 3. 分析

### 3.1 根因: empty_200 × 62s 浪费

kimi_nv 的 NVCF 后端 (function `f966661c`) 在 thinking 模式下返回 `200 Content-Length:0` (空响应), 每次耗时 ~62s (等于 NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66s, NVCF 在 thinking 超时后返回空).

当前 FASTBREAK=2 意味着需要 2 次连续 empty_200 才 fast-break:
- 第1次 empty_200: ~62s (per_attempt_timeout = min(66, 255-5) = 66s)
- 第2次 empty_200: ~62s (per_attempt_timeout = min(66, 255-62-5) = min(66, 188) = 66s)
- ATE 总耗时: ~124s

tier budget=255s 但 ATE 在 ~124s 就因 fastbreak 触发. 剩余 131s budget 未使用, 白白浪费.

### 3.2 优化: 缩紧 tier budget 到 120s

将 NVU_TIER_BUDGET_KIMI_NV 从 255 缩到 120:

- 第1次 empty_200: per_attempt_timeout = min(66, 120-5) = 66s → NVCF 在 ~62s 返回空 → 实际耗时 ~62s
- 第2次 empty_200: per_attempt_timeout = min(66, 120-62-5) = min(66, 53) = **53s** (vs 原来 66s)
  - NVCF 需 ~62s 返回空, 但 per_attempt_timeout 只有 53s → 在 53s 时 timeout
  - 这会触发 NVCFPexecTimeout 而非 empty_200, 但效果相同: 该 attempt 失败, fastbreak 触发
  - ATE 总耗时: 62 + 53 = **115s** (vs 原来 124s, 节省 ~9s)

等等 — 实际上 NVCF 可能在 53s 内就返回空 (因为 empty_200 实测在 62s 出现, 但 NVCF 可能在更早时刻就决定返回空). 观察数据显示 empty_200 通常在 ~62s 出现, 这与 NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66s 吻合, 说明 NVCF 在 thinking 超时后才返回空.

如果 per_attempt_timeout=53s < 62s, 则第2次 attempt 会在 53s 时 timeout (NVCFPexecTimeout), 而非 empty_200. 这不会触发 empty_200 fastbreak (因为 consecutive_empty_200 只计 empty_200, timeout 会 reset consecutive_pexec_timeout). 但 PEXEC_TIMEOUT_FASTBREAK=2 会在 2 次 consecutive timeout 后 fastbreak.

实际场景:
- 若第2次 NVCF 在 53s 前返回空 (empty_200) → fastbreak at ~115s
- 若第2次 NVCF 在 53s 时仍 thinking → timeout → consecutive_pexec_timeout=1, 继续 attempt 3
  - attempt 3: remaining = 120-62-53-5 = 0s → budget 不足, NV-TIER-BUDGET break

无论哪种路径, ATE 都在 ~115-120s 内完成 (vs 原来 124-255s).

### 3.3 全链路时间预算

| stage | before (R2299) | after (R2301) |
|-------|----------------|---------------|
| kimi_nv tier | 255s | 120s |
| peer-fb | 122s | 122s |
| ms_gw | 120s | 120s |
| **total** | **497s** | **362s** |
| PROXY_TIMEOUT | 500s | 500s |
| margin | 3s | 138s |

120+122+120=362 ≤ 500 ✓. 有充裕的 margin.

### 3.4 对成功请求的影响

成功请求 p50=29s, p90=87s. tier budget=120s 不影响:
- 成功请求通常在 1 个 key 上完成 (9-88s), 远低于 120s
- 只有 ATE (失败) 场景才受 budget 影响
- 缩紧 budget 只会让 ATE 更快触发 peer-fb → ms_gw fallback

### 3.5 不改的参数

- NVU_EMPTY_200_FASTBREAK=2 (R2270): 保���不变, 影响全局, 不宜为 kimi_nv 单独调
- NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66: 保持不变, 影响 thinking 响应正确性
- NVU_PEER_FALLBACK_TIMEOUT=122: 保持不变
- NVU_MS_GW_FALLBACK_TIMEOUT=120: 保持不变

## 4. 执行

### 4.1 变更

文件: `/opt/cc-infra/docker-compose.yml` (HM1)
行 496:
```diff
- NVU_TIER_BUDGET_KIMI_NV=255  # R2299 ...
+ NVU_TIER_BUDGET_KIMI_NV=120  # R2301 (HM2→HM1): 255→120 tighten kimi_nv tier budget. 2 empty_200×62s=124s wastes 131s of 255s budget. 120s: 2nd attempt timeout 53s (vs 66s), saves 9s/ATE. 120+122+120=362≤500. Single param; iron law: only HM1
```

### 4.2 重启

```
docker compose -f /opt/cc-infra/docker-compose.yml up -d --force-recreate nv_gw
→ Container nv_gw Recreated → Started
```

### 4.3 验证 (live env)

```
NVU_TIER_BUDGET_KIMI_NV=120  ✅
NVU_TIER_BUDGET_DSV4P_NV=160  (unchanged)
NVU_TIER_BUDGET_GLM5_2_NV=210  (unchanged)
TIER_TIMEOUT_BUDGET_S=415  (unchanged)
PROXY_TIMEOUT=500  (unchanged)
```

容器启动正常, RR counter 和 glm52 mode idx 已恢复.

## 5. 预期效果

- kimi_nv ATE duration: 124s → ~115-120s (节省 ~9s/ATE)
- 全链路 margin: 3s → 138s (更安全)
- 成功请求不受影响 (p50=29s, p90=87s << 120s)
- peer-fb 和 ms_gw fallback 链路不变

## ⏳ 轮到HM1优化HM2
