# R1323: HM2→HM1 — NOP (false trigger, HM1 internal commit, 37th consecutive post-R1286, "这是我提交的, 不触发")

## 触发原因
HM1提交了新commit到GitHub，脚本检测到并派遣HM2执行优化。但这是HM1自己的内部提交（"这是我提交的, 不触发"），不是优化信号。

## 数据收集

### 容器状态
- `nv_gw`: Up 6 hours (healthy), started 2026-07-13T22:14:51Z
- Compose md5: `6e1b58bc70eca49e500e3034b08376d9` (stable, unchanged)

### 运行时环境
```
UPSTREAM_TIMEOUT=66
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_TIER_BUDGET_DSV4P_NV=72
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_FORCE_STREAM_UPGRADE=0
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NVU_MS_GW_FALLBACK_TIMEOUT=195
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_PEER_FB_SKIP_MODELS=
```

### 6h 请求总览
- 55 req, 49 OK, 6 err, 89.1% SR
- 0 tier_attempts, 0 ATE, 0 IncompleteRead, 0 fallback
- ms_gw: 13/13 100%

### 错误分布
| error_type | cnt |
|---|---|
| zombie_empty_completion | 6 |

### 每小时SR
| hour | total | ok | fail | sr_pct |
|---|---|---|---|---|
| 23:00 | 6 | 5 | 1 | 83.3 |
| 00:00 | 6 | 5 | 1 | 83.3 |
| 01:00 | 29 | 28 | 1 | 96.6 |
| 02:00 | 5 | 5 | 0 | 100.0 |
| 03:00 | 5 | 3 | 2 | 60.0 |
| 04:00 | 4 | 3 | 1 | 75.0 |

### zombie detail
- glm5_2_nv integrate, avg input 192,813 chars, avg duration 5,446ms
- NVCF content_filter → finish_reason=stop, content_chars < 50 → zombie abort
- NOT config-fixable (NVCF-side content filtering)

### 日志关键信号
- No NV-TIER-FAIL (0 tier failures)
- No NV-EMPTY-FASTBREAK
- NV-ZOMBIE-EMPTY: glm5_2_nv passthrough zombie empty completion (content_filter)
- NV-ZOMBIE-ERROR-CHUNK: sent finish_reason=content_filter to trigger openclaw fallback
- All requests: glm5_2_nv integrate only, stream=True, tier_chain=['glm5_2_nv']

## 决策: NOP

**原因**: 37th consecutive false trigger post-R1286. All params at floor/optimal values. 6 zombie_empty_completion errors are NVCF content-filter side (high input chars 175K-178K → content_filter → empty response), not config-fixable at the proxy level. 0 tier_attempts, 0 ATE, 0 IncompleteRead, 0 fallback — proxy is functioning correctly. ms_gw 13/13 100% as backup. Compose md5 6e1b58bc stable. NVU_PEER_FB_SKIP_MODELS empty. No parameter to change.

**铁律**: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2