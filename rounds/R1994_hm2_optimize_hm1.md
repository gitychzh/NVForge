# R1994 (HM2→HM1): NOP — 数据稳定，连续冻结第40轮

## 触发源
HM2 自身 R1993 NOP commit (8771a85)，非 HM1 新 commit。Cron false trigger。

## 数据 (30min/6h window, 2026-07-20 06:50 CST ≈ 2026-07-19 22:50 UTC)

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
| glm5_2_nv | 32 | 28 | 4 | 5,703 |
| dsv4p_nv | 10 | 10 | 0 | 31,599 |

### 失败明细

| 模型 | 错误类型 | 数量 | avg_ms | input_chars |
|---|---|---|---|---|
| glm5_2_nv | zombie_empty_completion | 4 | 3,987 | 152k–156k |

- 4 zombie 全部 NVCF 级别 empty completion (502)，非网关配置可修复
- 时间分布: 18:04, 18:33, 19:03 (restart前), 21:33 (restart后触发breaker)
- 21:33 zombie 触发 big_input breaker OPEN，此后 22:03/22:33 所有超大请求全被 peer-fallback 救援成功

### Tier Attempts (6h)

| tier | error_type | cnt |
|---|---|---|
| glm5_2_nv | pexec_success | 10 |

- 仅 pexec_success，0 pexec_timeout、0 SSLEOF、0 connect 错误
- tier 层面完全健康

### 容器状态

- nv_gw: 启动于 2026-07-19 21:14 UTC (healthy)
- 零漂移: 所有 env 与 compose 一致
- docker logs: 22:03–22:33 所有 recent 均为 big_input breaker → peer-fallback → 200 OK
- 零本地 NVCF 直达请求（全部 glm5_2 请求超 150k chars → big_input breaker OPEN）
- 全参数在 floor/optimal

### Phantom ATE

28 条 all_tiers_exhausted + status=200（全部 big_input breaker → peer-fallback 救援成功）
- HM2 peer 正常处理超长请求，ttfb 6–52ms，bytes 16–14501
- 零 fallback_occurred=true（本地 0 尝试 NVCF）

## 约束检查

- Tier budget: `28+122=150 < 151 BUDGET` ✓ (1s margin)
- Peer-fb regular: `30+122=152 > 151` → peer-fb 正确跳过 (big_input 路径不受影响) ✓
- KEY_COOLDOWN=TIER_COOLDOWN=60（NVCF 60s 窗口对齐）✓
- FASTBREAK=1 ✓, SSLEOF=0.1 ✓, MIN_OUTBOUND=0 ✓, CONNECT_RESERVE=0 ✓
- BIG_INPUT: FAIL_N=1, COOLDOWN=86400, THRESHOLD=115000 ✓
- PEER_FALLBACK_TIMEOUT=122 ✓

## 判断

1. Cron false trigger: 触发源为 HM2 自身 NOP commit (R1993)，非 HM1 新 commit
2. 数据与 R1993 完全一致: 相同 42 req, 相同 4 zombie, 相同最后请求时间
3. 4 zombie 全部 NVCF 级别 empty terminal，非本地配置可修复
4. 21:33 zombie 成功触发 breaker，22:03/22:33 全部 peer-fallback 救援
5. 0 真实 ATE (502)，28 phantom ATE 全部 peer-fallback 救援成功
6. 全参数在 floor/optimal，零配置可修错误，零漂移
7. NOP — 连续冻结第 **40** 轮 (R1955→R1994, HM2→HM1)
8. 铁律: 只改 HM1 不改 HM2
## ⏳ 轮到HM1优化HM2
