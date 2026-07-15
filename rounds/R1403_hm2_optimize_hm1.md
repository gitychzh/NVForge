# HM2 Optimize HM1 — Round R1403

> **触发类型**: 误触发 (false trigger, double-dispatch) — 562nd chain of R1133
> **铁律**: 只改HM1不改HM2

## 1. 触发分析
cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch)
- HM1 本地 git log 停留在 R1206，196 轮落后
- R1402 已于 pre-run 脚本提交，symlink 已指向 R1402

## 2. 改前数据 (6h 窗口)
- **总请求**: 8
- **成功 (200)**: 6 (75.0% SR)
- **失败 (502)**: 2
- **错误分布**: 2 zombie_empty_completion (glm5_2_nv, NVCF content-filter, code-level, gateway detection+error-chunk correct)
- **tier_attempts**: 0
- **fallback**: 0
- **ms_gw**: 0/0
- **compose md5**: f493494e2b41b17fbf5d9cff9093648e (unchanged)
- **容器重启**: 2026-07-14T23:43:06Z

## 3. Hourly SR
| Hour (UTC) | Total | OK | Fail | SR% |
|------------|-------|-----|------|-----|
| 07-14 19:00 | 2 | 1 | 1 | 50.0 |
| 07-15 00:00 | 4 | 4 | 0 | 100.0 |
| 07-15 01:00 | 2 | 1 | 1 | 50.0 |

## 4. 参数状态 — All floor/optimal
- UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=205, TIER_COOLDOWN_S=15
- KEY_COOLDOWN_S=25, MIN_OUTBOUND_INTERVAL_S=0
- NVU_STREAM_FIRST_BYTE_DEADLINE_S=20, NVU_STREAM_TOTAL_DEADLINE_S=42
- NVU_CONNECT_RESERVE_S=0, NVU_EMPTY_200_FASTBREAK=2
- NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
- NVU_INTEGRATE_THINKING_TIMEOUT_S=90
- KEY_AUTHFAIL_COOLDOWN_S=60
- NVU_SSLEOF_RETRY_DELAY_S=1.0
- FALLBACK_HEALTH_THRESHOLD=0.05
- CHARS_PER_TOKEN_ESTIMATE=3.0

## 5. 决策 — NOP (零可修故障)
- zombie_empty_completion = NVCF content-filter (code-level, not config-fixable)
- Gateway detection + error-chunk 机制正确工作
- 所有参数处于 floor/optimal，无优化空间
- ms_gw 无流量，0 tier_attempts，0 fallback
- compose md5 未变，容器 2h 稳定运行

## 6. 修改
- **零参数修改** (zero param)
- **零 compose 修改**
- **零容器重启**

## ⏳ 轮到HM1优化HM2
