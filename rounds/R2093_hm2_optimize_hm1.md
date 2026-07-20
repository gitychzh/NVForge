# R2093 (HM2→HM1): NOP — zero post-deploy traffic, NVCF platform-level failures only

## 数据 (HM1, 6h window)
- **30 req, 19 OK (63.3% SR), 11 fail**
- 8 zombie_empty_completion (502) — glm5_2, NVCF function 3b9748d8, not locally fixable
- 3 all_tiers_exhausted (502) — dsv4p_nv, NVCF function 74f02205 DEGRADED, not locally fixable
- 1 NVStream_IncompleteRead (502) — glm5_2, K5, pexec_success but stream truncated
- 0 peer-fallback events, 0 ms_gw fallback
- glm5_2_nv: 28 req, 19 OK (67.9%), 24/28 with key_cycle_429s (85.7% cycling, pre-R2091 KEY=62)
- dsv4p_nv: 3 req, 0 OK, all 3 ATE (DEGRADED), avg 6ms
- 429 cycling: 24/30 reqs (80.0%), total_kc429=36

## 1h window
- 8 req, 2 OK (25.0%), 6 fail
- 3 ATE dsv4p (DEGRADED), 2 zombie glm5_2, 1 IncompleteRead

## 容器状态
- nv_gw: Up 17 min (healthy), StartedAt 2026-07-20T15:14:03Z (R2091 deploy)
- **Zero post-deploy traffic** (0 req since restart)
- Clean startup, no errors in docker logs
- logs_db: healthy, 3 days uptime

## 当前参数 (docker exec env)
| 参数 | 值 | 说明 |
|------|-----|------|
| KEY_COOLDOWN_S | 65 | R2091: 62→65 (+3s) |
| TIER_COOLDOWN_S | 60 | |
| UPSTREAM_TIMEOUT | 24 | |
| TIER_TIMEOUT_BUDGET_S | 153 | |
| NVU_PEER_FALLBACK_TIMEOUT | 122 | |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 15 | |
| NVU_STREAM_TOTAL_DEADLINE_S | 25 | |
| NVU_BIG_INPUT_COOLDOWN_S | 2100 | |
| NVU_BIG_INPUT_FAIL_N | 1 | floor |
| NVU_BIG_INPUT_THRESHOLD | 90000 | |
| NVU_BIG_INPUT_MODELS | glm5_2_nv,dsv4p_nv | |
| NVU_TIER_BUDGET_DSV4P_NV | 20 | |
| NVU_TIER_BUDGET_GLM5_2_NV | 22 | |
| NVU_EMPTY_200_FASTBREAK | 1 | floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | |
| NV_INTEGRATE_MODELS | "" | integrate disabled |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_SSLEOF_RETRY_DELAY_S | 0.1 | |
| NVU_FORCE_STREAM_UPGRADE | 0 | disabled |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | |
| NVU_PEER_FALLBACK_ENABLED | 1 | |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | |
| CHARS_PER_TOKEN_ESTIMATE | 3.0 | |

## 分析
- **Zero post-deploy traffic**: 容器重启后（R2091 KEY 62→65）零流量，无数据评估新 regime
- 6h 窗口数据全部来自 R2091 deploy 前，反映的是 KEY_COOLDOWN=62 的旧 regime
- 所有 11 个失败均为 NVCF 平台级：
  - 8 zombie (glm5_2, 3b9748d8) — NVCF function 返回 empty200，非本地配置可修
  - 3 ATE (dsv4p, 74f02205) — NVCF function DEGRADED，R814 正确短接
  - 1 IncompleteRead — stream 中断，非配置可修
- 零 peer-fallback 事件 — dsv4p DEGRADED 时 R814 短接过快，无机会触发 peer-fb
- 429 cycling 率 85.7% 是 R2091 前 KEY=62 的数据；当前 KEY=65 待验证
- **NOP 铁律**: 零 post-deploy 流量 + 零可配置修复故障 → 禁止改动

## 决策: NOP
- 本轮不做任何参数修改
- 等待 R2091 regime (KEY=65) 产生足够数据后下一轮评估
- 若 dsv4p DEGRADED 持续，下一轮仍为 NOP（NVCF 平台问题，非本地可修）
- 若 dsv4p 恢复，重点评估 KEY=65 的 429 cycling 改善效果

## ⏳ 轮到HM1优化HM2