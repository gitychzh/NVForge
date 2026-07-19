# R1973 (HM2→HM1): NOP — 4 zombie all NVCF empty200, big_input breaker+peer-fb rescuing, 连续冻结第12轮

## 📊 数据总览 (2026-07-20 04:25 UTC)

| 窗口 | Total | OK | Fail | SR |
|------|-------|-----|------|-----|
| 6h | 39 | 35 | 4 | 89.7% |
| 30min | 2 | 2 | 0 | 100% |

## 📊 按模型 (6h)

| Model | OK | Fail | SR | avg_ms | max_ms |
|-------|-----|------|-----|--------|--------|
| glm5_2_nv | 25 | 4 | 86.2% | 8,404 | 17,786 |
| dsv4p_nv | 10 | 0 | 100% | 31,599 | 55,335 |

## 🔴 错误分析 (6h)

| Error Type | Count | Model | 根因 |
|-----------|-------|-------|------|
| zombie_empty_completion | 4 | glm5_2_nv | NVCF function-level empty200 degradation |

- 所有 4 个 zombie 均为 glm5_2_nv NVCF 函数级退化 (empty200)，非本地配置可修
- Big_input breaker (threshold=115K, FAIL_N=1, cooldown=86400s) 捕获 ~153K-char 僵尸请求
- 前 4 个 zombie 触发 breaker OPEN，后续请求 all_tiers_exhausted → peer-fallback → HM2 救援全部 OK
- dsv4p_nv: 10/10 OK 全部 peer-fb 救援 (TIER_BUDGET=20s 快速失败)，NVCF 函数完全死亡
- 0 SSLEOF, 0 pexec timeout, 0 key_cycle_429s, 0 ATE true failures

## 📋 当前配置 (env ↔ compose 无漂移)

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 30 | floor |
| TIER_TIMEOUT_BUDGET_S | 153 | optimal |
| KEY_COOLDOWN_S | 60 | floor (NVCF boundary) |
| TIER_COOLDOWN_S | 60 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_TIER_BUDGET_DSV4P_NV | 20 | floor (fast-fail dead func) |
| NVU_TIER_BUDGET_GLM5_2_NV | 28 | floor (max OK 17.8s + 10s margin) |
| NVU_PEER_FALLBACK_TIMEOUT | 122 | optimal (≥HM2_BUDGET+2=72 ✓) |
| NVU_BIG_INPUT_THRESHOLD | 115000 | catching ~153K zombies |
| NVU_BIG_INPUT_COOLDOWN_S | 86400 | 24h full-day coverage |
| NVU_EMPTY_200_FASTBREAK | 1 | floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_SSLEOF_RETRY_DELAY_S | 0.1 | floor |
| NVU_STREAM_TOTAL_DEADLINE_S | 25 | optimal |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 15 | optimal |

## 🧊 决策: NOP (冻结)

- 所有 4 失败均为 NVCF 上游函数级退化 (empty200)，非本地配置可修
- Big_input breaker + peer-fallback 组合有效处理救援路径
- 所有参数已在 floor/optimal，无可调空间
- 连续冻结第 12 轮 (R1962→R1973)
- 铁律: 只改 HM1 不改 HM2
## ⏳ 轮到HM1优化HM2
