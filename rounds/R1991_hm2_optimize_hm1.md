# R1991 (HM2→HM1): NOP — 数据与前轮一致，连续冻结第27轮

## 数据 (30min/6h window, 2026-07-20 06:35 CST ≈ 2026-07-19 22:35 UTC)

| 指标 | 值 |
|---|---|
| 总请求 (6h) | 42 |
| 成功 (200, ok) | 38 (90.5%) |
| 失败 (502, zombie) | 4 (9.5%) |
| 真实 ATE (502) | 0 |
| Phantom ATE (200, rescued) | 28 |
| 30min 窗口 | 7 req, 7/7 (100%) |
| 最后请求 | 2026-07-19 22:33 UTC (~2min 前) |

### 模型分布 (6h)

| 模型 | total | ok | fail | avg_ok_ms | sum_429s |
|---|---|---|---|---|---|
| glm5_2_nv | 32 | 28 | 4 | 5,948 | 10 |
| dsv4p_nv | 10 | 10 | 0 | 31,599 | 0 |

### 失败明细

| 模型 | 错误类型 | 数量 | avg_ms | tiers_tried |
|---|---|---|---|---|
| glm5_2_nv | zombie_empty_completion | 4 | 3,987 | 1 |
- 4 zombie 全部 NVCF 级别 empty completion (502)，非网关配置可修复
- 均含 key_cycle_429s=1（先 429 再 empty）

### glm5_2 429 分析

| key_cycle_429s | cnt | avg_ms | ok |
|---|---|---|---|---|
| 0 | 22 | 5,430 | 22 |
| 1 | 10 | 6,304 | 6 |

- 10/32 glm5_2 请求触发 429 (31%)，平均 +874ms 延迟
- 429 均为单次轮转 (key_cycle=1)，正常 NVCF rate-limit 行为
- 无 entegrate 路径错误 (NV_INTEGRATE_KEY_COOLDOWN_S=0 零问题)

### glm5_2 成功延迟

| 统计 | 值 |
|---|---|
| avg | 5,948ms |
| min | 1,696ms |
| max | 13,242ms |
| P50 | 5,340ms |
| P95 | 9,840ms |
| P99 | 12,940ms |

无 429 请求 avg=5,430ms vs 含 429 avg=6,304ms (+~16%)

### 容器状态

- nv_gw: 启动于 2026-07-19 21:14 UTC (healthy)
- 零漂移: 所有 env 与 compose 一致
- docker logs: 1 zombie_empty_completion, 3 big_input breaker → peer-fallback → 200 OK (全部救援成功)
- 全参数在 floor/optimal

### Phantom ATE

28 条 all_tiers_exhausted + status=200（全部 peer-fallback empty-200 救援成功）

## 约束检查

- Tier budget: `28+122=150 < 151 BUDGET` ✓ (1s margin)
- Peer-fb: `30+122=152 > 151` → peer-fb 在边界正确触发
- KEY_COOLDOWN=TIER_COOLDOWN=60（NVCF 60s 窗口对齐）✓
- FASTBREAK=1 ✓, SSLEOF=0.1 ✓, MIN_OUTBOUND=0 ✓, CONNECT_RESERVE=0 ✓
- BIG_INPUT: FAIL_N=1, COOLDOWN=86400, THRESHOLD=115000 ✓
- NV_INTEGRATE_KEY_COOLDOWN_S=0 ✓

## 判断

1. Cron false trigger: 触发源为 HM2 CC2 巡检 commit (R1991 cc2: "NOP 巡检 R100")，非 HM1 新 commit
2. 4 个 zombie 全部 NVCF 级别 empty terminal，非本地配置可修复
3. 10 次 429 均为单次轮转 (0 次级联)，KEY_COOLDOWN=60 在 NVCF 窗口边界安全
4. 28 phantom ATE 全部 peer-fallback 救援成功
5. 零 fallback 实际发生 (fallback_occurred=false 100%)
6. 全参数在 floor/optimal，零配置可修错误，零漂移
7. NOP — 连续冻结第 **27** 轮 (R1963→R1991, HM2→HM1)
8. 铁律: 只改 HM1 不改 HM2
## ⏳ 轮到HM1优化HM2
