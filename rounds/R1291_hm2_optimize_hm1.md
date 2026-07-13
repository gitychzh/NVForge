# HM2 Optimize HM1 — Round R1291

## 1. 触发分析
cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch, 5th consecutive post-R1286)
- R1290 已由 pre-run 脚本写入并提交
- symlink RN_hm2_optimize_hm1.md → rounds/R1290_hm2_optimize_hm1.md 已正确

## 2. HM1 数据 (2026-07-14 06:50 UTC)
容器状态: nv_gw Up 37 minutes (healthy), restarted at 2026-07-13T22:14:51Z
compose md5: 6e1b58bc70eca49e500e3034b08376d9

### 6h 总体 (DB: nv_requests WHERE ts >= NOW() - INTERVAL '6 hours')
| 指标 | 值 |
|------|-----|
| 总请求 | 67 |
| 成功 | 52 |
| 失败 | 15 |
| 成功率 | 77.6% |

### 按路径
| upstream_type | cnt | ok | err | avg_ttfb | avg_dur | max_dur |
|---|---|---|---|---|---|---|
| nv_integrate | 54 | 42 | 12 | 6,817 | 7,176 | 15,747 |
| nvcf_pexec | 10 | 10 | 0 | 25,848 | 25,873 | 54,918 |
| (NULL=ATE) | 3 | 0 | 3 | 881 | 72,019 | 72,023 |

### 按模型
| mapped_model | cnt | ok | err | sr_pct | avg_dur |
|---|---|---|---|---|---|
| glm5_2_nv | 54 | 42 | 12 | 77.8% | 7,176 |
| dsv4p_nv | 13 | 10 | 3 | 76.9% | 36,522 |

### 错误详情
| error_type | cnt |
|---|---|
| zombie_empty_completion | 12 |
| all_tiers_exhausted | 3 |

### zombie 详情
- glm5_2_nv: 12× zombie_empty_completion, avg input_chars=204,971, avg dur=6,249ms
- NVCF content-filter stop+12chars — 非配置可修 (代码级 zombie 检测, fast abort 3-15s)

### ATE 详情
- dsv4p_nv: 3× all_tiers_exhausted, avg dur=72,019ms — 全部 pre-restart (容器重启于22:14 UTC)

### Post-restart (22:14 UTC → 现在, 37min)
- 4req: 3× glm5_2_nv integrate OK (4.8-5.0s), 1× zombie (3.1s)
- dsv4p_nv: 0 traffic post-restart
- 0 tier_attempts, 0 fallback_occurred, 0 NV-TIER-FAIL in logs
- ms_gw healthy: GLM-5.2 + deepseek-v4-pro both streaming OK

### 每小时 SR
| hour (UTC) | total | ok | fail | sr_pct |
|---|---|---|---|---|
| 2026-07-13 17:00 | 6 | 4 | 2 | 66.7% |
| 2026-07-13 18:00 | 36 | 31 | 5 | 86.1% |
| 2026-07-13 19:00 | 6 | 4 | 2 | 66.7% |
| 2026-07-13 20:00 | 6 | 4 | 2 | 66.7% |
| 2026-07-13 21:00 | 6 | 4 | 2 | 66.7% |
| 2026-07-13 22:00 | 7 | 5 | 2 | 71.4% |

### tier_chain
- `tier_chain=['glm5_2_nv'] (no fallback, 3model)` — 预期 (FALLBACK_GRAPH={} per R832)
- `NV-ZOMBIE-EMPTY` + `NV-ZOMBIE-ERROR-CHUNK` — 代码级 zombie 检测正常工作

### 24h 错误全景
| error_type | cnt |
|---|---|
| zombie_empty_completion | 33 |
| all_tiers_exhausted | 17 |
| NVStream_IncompleteRead | 2 |

## 3. 决策: NOP
- 数据与 R1290 相同: 67req/52OK 77.6%SR, 12 zombie + 3 ATE (pre-restart)
- zombie_empty_completion: NVCF content-filter, 非配置可修 (代码级检测, 已正确 abort)
- ATE: 全部 pre-restart 污染; post-restart 0 ATE
- all params at floor/optimal:
  - UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=205, TIER_COOLDOWN_S=15
  - KEY_COOLDOWN_S=25, MIN_OUTBOUND_INTERVAL_S=0, NVU_CONNECT_RESERVE_S=0
  - NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_EMPTY_200_FASTBREAK=2
  - NVU_INTEGRATE_TIMEOUT_FASTBREAK=1, NV_INTEGRATE_KEY_COOLDOWN_S=0
  - NVU_TIER_BUDGET_DSV4P_NV=72, NVU_TIER_BUDGET_GLM5_2_NV=96
  - NVU_MS_GW_FALLBACK_TIMEOUT=195, NVU_FALLBACK_HEALTH_THRESHOLD=0.05
  - NVU_PEER_FB_SKIP_MODELS="" (empty), NVU_PEER_FALLBACK_ENABLED=1
  - NVU_SSLEOF_RETRY_DELAY_S=1.0, KEY_AUTHFAIL_COOLDOWN_S=60
  - NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
- ms_gw healthy (GLM-5.2 + deepseek-v4-pro streaming OK)
- 0 tier_attempts 6h: 零 key 级错误
- 铁律:只改HM1不改HM2

## 4. 变更
零参数, 零 compose 修改, 零容器重启.

## 5. HM1 git 状态
HM1 git log 停留在 R1206 (84 轮落后 HM2), 正常 — HM1 未 pull

## ⏳ 轮到HM1优化HM2
