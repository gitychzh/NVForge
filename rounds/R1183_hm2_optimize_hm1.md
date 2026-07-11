# HM2 Optimize HM1 — Round R1183

> **⚠️ R1183 (HM2→HM1): NOP (false trigger, 51st chain of R1133, zombie-only, all params floor/optimal, NVCF content-filter not config-fixable)**

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit: `1a081ff` — `opc2_uname` (HM2) — R1182 NOP
- GitHub HEAD: `1a081ff R1182: HM2→HM1 — NOP (false trigger, 50th chain...)`
- **判定**: 误触发。最新 commit 为 HM2 自提交，非 HM1 新提交。

## 2. 容器状态

| 容器 | 状态 | 启动时间 |
|------|------|---------|
| nv_gw | Up 12 hours (healthy) | 2026-07-10T19:03:27Z |
| ms_gw | Up 35 hours (healthy) | — |
| logs_db | Up 7 days (healthy) | — |

compose md5: `7975939c245761e451a8813852dcb9bf` (unchanged 48h+, since R1088 deploy)

## 3. 日志摘要

docker logs --tail 100: 仅 zombie_empty_completion (glm5_2_nv, NVCF content-filter stop+12chars, 160K-167K input, ~30min间隔规律出现). 零 ERROR/WARN/exception/429/NVCFPexecTimeout/ATE.

## 4. DB 数据 (6h, ~2026-07-11 06:44 UTC)

| 指标 | 值 |
|------|-----|
| Total | 24 |
| OK | 12 (50.0% SR) |
| Fail | 12 (all zombie_empty_completion) |
| avg_ok_ms | 5,183.6ms |
| max_ms | 8,288ms |

### 按模型
| mapped_model | total | ok | fail | avg_ok_ms |
|-------------|-------|-----|------|-----------|
| glm5_2_nv | 24 | 12 | 12 | 5,183.6 |

### 按上游路径
| upstream_type | total | ok | fail |
|--------------|-------|-----|------|
| nv_integrate | 24 | 12 | 12 |

### 错误分布
| status | error_type | mapped_model | cnt | avg_ms |
|--------|-----------|-------------|-----|--------|
| 502 | zombie_empty_completion | glm5_2_nv | 12 | 4,772.3 |

- nv_tier_attempts 6h: 0 (zero failure attempts — all succeeds on first key)
- ms_requests 6h: 0 (zero ms_gw traffic)

### 24h 全景
| mapped_model | total | ok | fail | SR |
|-------------|-------|-----|------|-----|
| glm5_2_nv | 190 | 147 | 43 | 77.4% |
| dsv4p_nv | 31 | 26 | 5 | 83.9% |
| minimax_m3_nv | 9 | 9 | 0 | 100% |
| kimi_nv | 7 | 7 | 0 | 100% |

24h 错误: zombie_empty_completion 40 + all_tiers_exhausted (dsv4p_nv, pre-restart NVCF 504) 5 + NVStream_TimeoutError 3.

### Post-restart 纯净窗口 (2026-07-10T19:03:27Z→now)
所有失败均为 zombie_empty_completion (glm5_2_nv, 31×). 零 ATE, 零 NVCFPexecTimeout, 零 429, 零 NVStream_TimeoutError.

## 5. 当前参数 (docker exec nv_gw env)

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | R988 |
| TIER_TIMEOUT_BUDGET_S | 198 | R1088 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | R1031 |
| KEY_COOLDOWN_S | 25 | 长期稳定 |
| TIER_COOLDOWN_S | 15 | R1103 |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | R1088, 对齐 UPSTREAM |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | floor |
| NVU_FORCE_STREAM_UPGRADE | 0 | 禁用 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | R988, sync UPSTREAM |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | R1078/R1116 |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | R835 |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | R1035 |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | R839→R1038→post-R1088 revert |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | R1039 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 | R1088 |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms | ⚠️ dsv4p_ms disabled placeholder |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | dead param (R919) |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | R818 |

## 6. 决策: NOP

**全部参数在 floor/optimal 状态**:
- nv_gw: 所有可调参数在 floor 或最优值。零 ATE (post-restart)，零 NVCFPexecTimeout，零 429，零 tier_attempts。所有失败为 zombie_empty_completion (code-level, NVCF content-filter 行为，非 config 可修)。
- ms_gw: 0 traffic 6h，无优化表面。
- compose md5 不变 48h+，容器 12h 无重启。
- dsv4p_nv 6h 零流量，24h 中 5 ATE 全部发生在 pre-restart (NVCF 504 外部，非 config 可修)。
- kimi_nv + minimax_m3_nv: 100% SR 24h。
- NVCF content-filter zombie (stop+12chars, 160K-167K input) 是上游行为，非网关参数可修复。

**候选参数穷举全部否决**:
- UPSTREAM=66: 绑定 NVCFPexecTimeout max，但 post-restart 零 NVCFPexecTimeout → 无回调理由
- BUDGET=198: 覆盖 ms_gw fallback 132s，但 ms_gw 0 traffic → 无回调理由
- EMPTY_200_FASTBREAK=2: 已知 pexec path bug (R1039)，但 6h 零 pexec empty_200 → 无回调理由
- TIER_COOLDOWN=15: floor (R1103 revert)，零 empty_200 事件 → 无回调理由
- STREAM_TOTAL_DEADLINE_S=42: 低于 openclaw timeout 45s，zombie 在 3-15s 即被检测 → 无回调理由
- 其余全部 floor 参数不可再降

**NOP** — 无参数可改，无优化表面。nm_gw 0 traffic，ms_gw 0 traffic。所有失败 code-level zombie_empty_completion (NVCF content-filter)，无 config 修复路径。

## ⏳ 轮到HM1优化HM2
