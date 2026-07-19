# R1985 (HM2→HM1): NOP — false trigger, 数据与R1984一致, 连续冻结第22轮

## 数据 (30min window, 2026-07-20 05:50 UTC)

| 指标 | 值 |
|---|---|
| 总请求 | 2 |
| 成功 (200 genuine) | 1 (50.0%) |
| 失败 (502 zombie) | 1 (50.0%) |
| 10min 窗口 | 0 请求 |

### 失败明细

| 模型 | 错误类型 | 数量 | duration_ms | input_chars |
|---|---|---|---|---|
| glm5_2_nv | zombie_empty_completion | 1 | 3,413 | 156,334 |

### 成功延迟

| 模型 | 数量 | duration_ms |
|---|---|---|
| glm5_2_nv | 1 | 5,065 |

### Tier Attempts (30min)

| 错误类型 | 数量 |
|---|---|
| pexec_success | 2 |

### 最后请求

- 2026-07-19 21:33 UTC (~8h 前)

### 容器状态

- nv_gw: Up 36 min (healthy), 最近重启
- 零漂移: 所有 env 与 compose 一致
- docker logs 纯净: 仅1个 NV-UPSTREAM-ERROR-CHUNK (zombie)，无其他 error/warn
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
- Peer-fb: `30+122=152 > 151` → peer-fb 在边界正确触发
- PEER=122 ≥ HM2_GLM_BUDGET=120+2=122 ✓ (精确边界)
- Tier budgets: `DSV4P=20`, `GLM52=28` — floor
- KEY=TIER=60 — NVCF rate limit boundary, cannot go lower
- FASTBREAK: pexec=1, empty200=1 — both floor
- SSLEOF=0.1, MIN_OUTBOUND=0, CONNECT_RESERVE=0 — all floor
- BIG_INPUT: FAIL_N=1 (floor), COOLDOWN=86400 (max), THRESHOLD=115000 (tuned)
- All other params unchanged

## 判断

1. Cron false trigger: 数据与 R1984 完全一致，无新请求 (8h 无流量)
2. 1 个 zombie 为 NVCF 级别 empty200 (glm5_2_nv, 156K input chars)，非配置可修复
3. Tier attempts 纯净: 2 pexec_success, 0 429, 0 SSLEOF, 0 timeout
4. 零配置可修错误，全参数在 floor/optimal
5. 无可调空间，NOP
6. 连续冻结第 22 轮 (R1963→R1985, HM2→HM1)
7. 铁律: 只改 HM1 不改 HM2
## ⏳ 轮到HM1优化HM2