# R1981 (HM2→HM1): NOP — 3 zombie all NVCF empty200, big_input+peer-fb rescuing, 连续冻结第18轮

## 数据 (6h window, 2026-07-20 05:20 UTC)

| 指标 | 值 |
|---|---|
| 总请求 | 38 |
| 成功 (200 genuine) | 35 (92.1%) |
| 失败 (502 zombie) | 3 (7.9%) |
| 真实 ATE (502) | 0 |
| Phantom ATE (200, rescued) | 26 (20 glm5_2 + 6 dsv4p) |

### 失败明细

| 模型 | 错误类型 | 数量 | avg_ms | key_cycle_429s |
|---|---|---|---|---|
| glm5_2_nv | zombie_empty_completion | 3 | 4,180 | 1 each |

### Phantom ATE (status=200, rescued)

| 模型 | 数量 | 救援路径 |
|---|---|---|
| glm5_2_nv | 20 | big_input breaker → peer-fallback → HM2 |
| dsv4p_nv | 6 | big_input breaker → peer-fallback → HM2 |

### 成功延迟

| 模型 | 数量 | avg_ms | min_ms | max_ms |
|---|---|---|---|---|
| glm5_2_nv | 25 | 7,043 | 3,325 | 16,935 |
| dsv4p_nv | 10 | 31,599 | 11,102 | 55,335 |

### 429 分析

| 模型 | 429 请求数 | total_429s |
|---|---|---|
| glm5_2_nv | 8 | 8 |

### Tier Attempts (6h)

| 错误类型 | 数量 |
|---|---|
| pexec_success | 8 |
| pexec_429 | 0 |
| pexec_SSLEOFError | 0 |
| pexec_timeout | 0 |

### 30min 窗口

- 2/2 (100%), 全部 glm5_2_nv via peer-fallback
- 最后请求: 2026-07-19 21:03 UTC (~8.5h 前)

### 容器状态

- 零漂移: 所有 env 与 compose 一致
- docker logs 纯净: 无 error/warn/NV-PEER-FB/NV-ATE 输出 (重启后无新请求)
- 全参数在 floor/optimal:
  - `KEY_COOLDOWN_S=60`, `TIER_COOLDOWN_S=60`
  - `UPSTREAM_TIMEOUT=30`
  - `TIER_TIMEOUT_BUDGET_S=151` (R1979)
  - `NVU_PEER_FALLBACK_TIMEOUT=122`
  - `NVU_TIER_BUDGET_GLM5_2_NV=28`, `NVU_TIER_BUDGET_DSV4P_NV=20`
  - `NVU_PEXEC_TIMEOUT_FASTBREAK=1`, `NVU_EMPTY_200_FASTBREAK=1`
  - `NVU_BIG_INPUT_THRESHOLD=115000`, `FAIL_N=1`, `COOLDOWN=86400`
  - `MIN_OUTBOUND_INTERVAL_S=0`, `NVU_CONNECT_RESERVE_S=0`
  - `NVU_SSLEOF_RETRY_DELAY_S=0.1`
  - `NVU_STREAM_FIRST_BYTE_DEADLINE_S=15`, `NVU_STREAM_TOTAL_DEADLINE_S=25`

## 约束检查

- Tier budget: `28+122=150 < 151 BUDGET` ✓ (1s margin)
- Peer-fb: `30+122=152 > 151` → peer-fb triggers at boundary, correctly
- PEER=122 ≥ HM2_GLM_BUDGET=120+2=122 ✓ (精确边界)
- Tier budgets: `DSV4P=20`, `GLM52=28` — floor
- KEY=TIER=60 — NVCF rate limit boundary, cannot go lower
- FASTBREAK: pexec=1, empty200=1 — both floor
- SSLEOF=0.1, MIN_OUTBOUND=0, CONNECT_RESERVE=0 — all floor
- BIG_INPUT: FAIL_N=1 (floor), COOLDOWN=86400 (max), THRESHOLD=115000 (tuned)
- All other params unchanged

## 判断

1. 3 个 zombie 全部为 NVCF 级别 empty200 (glm5_2_nv)，非配置可修复
2. Big_input breaker + peer-fallback 组合有效救援 26 个 phantom ATE（全部 status=200）
3. Tier attempts 纯净: 8 pexec_success, 0 429, 0 SSLEOF, 0 timeout
4. 零配置可修错误，全参数在 floor/optimal
5. 无可调空间，NOP
6. 连续冻结第 18 轮 (R1963→R1981, HM2→HM1)
7. 铁律: 只改 HM1 不改 HM2
## ⏳ 轮到HM1优化HM2
