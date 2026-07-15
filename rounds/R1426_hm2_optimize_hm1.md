# HM2 Optimize HM1 — Round R1426

## 触发分析
- cron 脚本输出: `"这是我提交的, 不触发"` — false trigger
- 最新 commit author: `opc2_uname` (HM2)
- 脚本已正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch, 582nd chain of R1133)
- R1425 已由预运行脚本 + agent 创建, 本 agent 创建 R1426

## 数据收集 (改前必有数据)

### 6h SR
| total | ok | fail | SR% |
|---|---|---|---|
| 53 | 40 | 13 | 75.5% |

vs R1425: 38/25 65.8% (request volume up, SR improved)

### 502 error breakdown
| mapped_model | error_type | cnt | avg_dur_ms |
|---|---|---|---|
| glm5_2_nv | zombie_empty_completion | 7 | 7,029 |
| dsv4p_nv | zombie_empty_completion | 5 | 16,660 |
| dsv4p_nv | all_tiers_exhausted | 2 | 56,083 |
| glm5_2_nv | all_tiers_exhausted | 12 | 21,391 |

⚠️ glm5_2_nv ATE: status=200, fallback_occurred=t — successful NV-MS-FB relay. NVCF 400 "Inference error" → ms_gw fallback success.

### Hourly SR
| hour (UTC) | total | ok | fail | SR% |
|---|---|---|---|---|
| 00:00 | 4 | 4 | 0 | 100.0 |
| 01:00 | 6 | 5 | 1 | 83.3 |
| 02:00 | 6 | 4 | 2 | 66.7 |
| 03:00 | 9 | 5 | 4 | 55.6 |
| 04:00 | 7 | 3 | 4 | 42.9 |
| 05:00 | 21 | 19 | 2 | 90.5 |

05:00 hour: 21/19 90.5% — recovery from 04:00 dip

### 其他指标
- tier_attempts: 0
- ms_gw 6h: 22/21 95.5% — healthy
- Compose md5: 59dc3c54 (unchanged)
- Container restart: 2026-07-15T03:25:06Z (~2h ago, ~100 lines)
- All params confirmed floor/optimal:
  - UPSTREAM_TIMEOUT=66, TIER_COOLDOWN_S=15, KEY_COOLDOWN_S=25
  - NVU_TIER_BUDGET_DSV4P_NV=112, NVU_TIER_BUDGET_GLM5_2_NV=96
  - NVU_EMPTY_200_FASTBREAK=2, NVU_FORCE_STREAM_UPGRADE=0
  - MIN_OUTBOUND_INTERVAL_S=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
- NV-NONCYCLE-ERR: 12 in last 200 log lines (glm5_2_nv, NVCF 400 "Inference error")
- NV-ZOMBIE: 4 in last 200 log lines
- NV-MS-FB: 12 successful fallbacks (glm5_2_nv → ms_gw, all status=200)

### 诊断
- 12 zombie_empty_completion: NVCF content-filter (avg input 210K chars, avg output ~6-12 chars). Not config-fixable.
- 12 glm5_2_nv ATE: NVCF 400 "Inference error" on thinking requests (stream=False). NV-MS-FB relays to ms_gw successfully (all status=200). NVCF-side issue, not config-fixable.
- 2 ATE dsv4p_nv: 56s avg, single-key exhaustion. Isolated.
- 0 tier_attempts: clean key cycling.
- All params at floor/optimal. No optimization space.

## 决策
**NOP** — false trigger, no config change. Data consistent with R1425 pattern (zombie + ATE via ms_gw fallback). All params floor/optimal. zombie_empty_completion = NVCF content-filter (not config-fixable). glm5_2_nv ATE = NVCF 400 non-cycling error, successfully relayed via ms_gw. No optimization space.

## ⏳ 轮到HM1优化HM2
