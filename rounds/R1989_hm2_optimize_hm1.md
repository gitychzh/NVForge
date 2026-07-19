# R1989 (HM2→HM1): NOP — 数据与R1988完全一致，连续冻结第25轮

## 数据 (30min/6h window, 2026-07-19 22:19 UTC)

| 指标 | 值 |
|---|---|
| 总请求 (6h) | 38 |
| 成功 (200 genuine) | 34 (89.5%) |
| 失败 (502 zombie) | 4 (10.5%) |
| 真实 ATE (502) | 0 |
| Phantom ATE (200, rescued) | 24 |
| 30min 窗口 | 3 req, 3/3 (100%) |
| 最后请求 | 2026-07-19 22:03 UTC (~15min 前) |
| 新请求 (R1988后) | 0 |

### 失败明细

| 模型 | 错��类型 | 数量 | avg_ms |
|---|---|---|---|
| glm5_2_nv | zombie_empty_completion | 4 | 3,987 |

### 成功延迟

| 模型 | 数量 | avg_ms | min_ms | max_ms |
|---|---|---|---|---|
| glm5_2_nv | 24 | 6,726 | 3,325 | 16,935 |
| dsv4p_nv | 10 | 31,599 | 11,102 | 55,335 |

### Tier Attempts (6h)

| 错误类型 | 数量 |
|---|---|
| pexec_success | 10 |

### 429 分析

| 模型 | 429 请求数 | total_429s |
|---|---|---|
| glm5_2_nv | 10 | 10 |

### Fallback 分析 (6h)

38 fallback_occurred = false (全部无实际fallback)

### 容器状态

- nv_gw: 启动于 2026-07-19 21:14 UTC (healthy)
- 零漂移: 所有 env 与 compose 一致
- docker logs: 3 big_input breaker → peer-fallback → 200 OK (全部成功救援), 1 zombie_empty_completion (NVCF 级别), 无其他 error/warn
- 全参数在 floor/optimal

## 约束检查

- Tier budget: `28+122=150 < 151 BUDGET` ✓ (1s margin)
- Peer-fb: `30+122=152 > 151` → peer-fb 在边界正确触发
- PEER=122 ≥ HM2_GLM_BUDGET=120+2=122 ✓ (精确边界)
- 全参数 floor/optimal: KEY=60, TIER=60, UPSTREAM=30, BUDGET=151, FASTBREAK=1, SSLEOF=0.1, MIN_OUTBOUND=0, CONNECT_RESERVE=0, BIG_INPUT={FAIL_N=1, COOLDOWN=86400, THRESHOLD=115000}

## 判断

1. Cron false trigger: 数据与 R1988 完全一致，DB 总请求数(=800)不变，最后请求时间(=22:03 UTC)不变
2. 4 个 zombie 全部为 NVCF 级别 empty200 (glm5_2_nv)，非配置可修复
3. Big_input breaker + peer-fallback 有效救援 24 phantom ATE (全部 status=200)
4. Tier attempts 纯净: 10 pexec_success, 0 429, 0 SSLEOF, 0 timeout
5. 零 fallback 实际发生 (所有 38 条 fallback_occurred=false)
6. 零配置可修错误，全参数在 floor/optimal
7. 无可调空间，NOP
8. 连续冻结第 25 轮 (R1963→R1989, HM2→HM1)
9. 铁律: 只改 HM1 不改 HM2
## ⏳ 轮到HM1优化HM2
