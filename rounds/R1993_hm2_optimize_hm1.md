# R1993 (HM2→HM1): NOP — 数据稳定，连续冻结第39轮

## 触发源
HM2 自身 R1992 巡检 commit (b693aed)，非 HM1 新 commit。Cron false trigger。

## 数据 (30min/6h window, 2026-07-20 06:45 CST ≈ 2026-07-19 22:45 UTC)

| 指标 | 值 |
|---|---|
| 总请求 (6h) | 42 |
| 成功 (200, ok) | 38 (90.5%) |
| 失败 (502, zombie) | 4 (9.5%) |
| 真实 ATE (502) | 0 |
| Phantom ATE (200, rescued) | 28 |
| 30min 窗口 | 7 req, 7/7 (100%) |
| 最后请求 | 2026-07-19 22:33 UTC |

### 模型分布 (6h)

| 模型 | total | ok | fail | avg_ms |
|---|---|---|---|---|
| glm5_2_nv | 32 | 28 | 4 | 5,948 |
| dsv4p_nv | 10 | 10 | 0 | 31,599 |

### 失败明细

| 模型 | 错误类型 | 数量 | avg_ms |
|---|---|---|---|
| glm5_2_nv | zombie_empty_completion | 4 | 3,987 |

- 4 zombie 全部 NVCF 级别 empty completion (502)，非网关配置可修复
- 均含 key_cycle_429s=1（先 429 再 empty），NVCF rate-limit 正常行为

### glm5_2 429 分析

| key_cycle_429s | cnt | 
|---|---|
| 1 | 10 |

- 10/32 glm5_2 请求触发 429 (31%)，均为单次轮转
- 0 次级联 429，KEY_COOLDOWN=60s 在 NVCF 窗口边界安全

### Tier Attempts (6h)

| tier | error_type | cnt |
|---|---|---|
| glm5_2_nv | pexec_success | 10 |

- 仅 pexec_success，0 pexec_timeout、0 SSLEOF、0 connect 错误
- tier 层面完全健康

### 容器状态

- nv_gw: 启动于 2026-07-19 21:14 UTC (healthy)
- 零漂移: 所有 env 与 compose 一致
- docker logs: 所有 recent 均为 big_input breaker → peer-fallback → 200 OK (救援 100%)
- 零本地 NVCF 直达请求（全部 glm5_2 请求超 150k chars → big_input breaker OPEN）
- 全参数在 floor/optimal

### Phantom ATE

28 条 all_tiers_exhausted + status=200（全部 big_input breaker → peer-fallback 救援成功）
- HM2 peer 正常处理超长请求，ttfb 5–52ms，bytes 16–14501
- 零 fallback_occurred=true（本地 0 尝试 NVCF）
- 19:00 窗口有 6 dsv4p_nv phantom ATE (50331ms avg) — 均为 NVCF degraded 时段 peer-fb 救援

## 约束检查

- Tier budget: `28+122=150 < 151 BUDGET` ✓ (1s margin)
- Peer-fb regular: `30+122=152 > 151` → peer-fb 正确跳过 (big_input 路径不受影响) ✓
- KEY_COOLDOWN=TIER_COOLDOWN=60（NVCF 60s 窗口对齐）✓
- FASTBREAK=1 ✓, SSLEOF=0.1 ✓, MIN_OUTBOUND=0 ✓, CONNECT_RESERVE=0 ✓
- BIG_INPUT: FAIL_N=1, COOLDOWN=86400, THRESHOLD=115000 ✓
- NV_INTEGRATE_KEY_COOLDOWN_S=0 ✓
- FORCE_STREAM_TIMEOUT=66 ✓
- PEER_FALLBACK_TIMEOUT=122 ✓

## 判断

1. Cron false trigger: 触发源为 HM2 自身巡检 commit (R1993 cc2)，非 HM1 新 commit
2. 4 个 zombie 全部 NVCF 级别 empty terminal，非本地配置可修复
3. 10 次 429 均为单次轮转 (0 次级联)，KEY_COOLDOWN=60 在安全边界
4. 0 真实 ATE (502)，28 phantom ATE 全部 peer-fallback 救援成功
5. 零 fallback 实际发生 (fallback_occurred=false 100%)
6. 全参数在 floor/optimal，零配置可修错误，零漂移
7. NOP — 连续冻结第 **39** 轮 (R1955→R1993, HM2→HM1)
8. 铁律: 只改 HM1 不改 HM2
## ⏳ 轮到HM1优化HM2
