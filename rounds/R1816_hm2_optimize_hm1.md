# R1816 (HM2→HM1): NOP — 全部失败为外部 NVCF 函数降级, 零可配置修复故障, glm5_2 100% SR

## 数据收集

### HM1 nv_gw Logs (最近100行)
- 零 error/warn/panic/exception
- 零 zombie/fallback/peer-fb 成功
- 2 SSLEOF tier self-recovery (glm5_2_nv pexec)
- glm5_2_nv: 全部 pexec, RR 均匀分布 k0-k4, timeout=55s
- kimi_nv: 4 次 ATE 全部 NV-TIER-DEGRADED-SKIP → peer-fb → peer 502 (NVCF 函数降级)

### HM1 nv_gw Env Config
```
UPSTREAM_TIMEOUT=55
KEY_COOLDOWN_S=65
TIER_COOLDOWN_S=65
TIER_TIMEOUT_BUDGET_S=180
MIN_OUTBOUND_INTERVAL_S=0
NVU_CONNECT_RESERVE_S=0
NVU_EMPTY_200_FASTBREAK=1
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_STREAM_FIRST_BYTE_DEADLINE_S=15
NVU_STREAM_TOTAL_DEADLINE_S=25
NVU_SSLEOF_RETRY_DELAY_S=0.2
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=122
NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006
NVU_PEER_FB_SKIP_MODELS=
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms
NVU_MS_GW_FALLBACK_TIMEOUT=120
NVU_TIER_BUDGET_DSV4P_NV=45
NVU_TIER_BUDGET_GLM5_2_NV=105
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_BIG_INPUT_COOLDOWN_S=7200
NVU_BIG_INPUT_FAIL_N=1
NVU_BIG_INPUT_MODELS=glm5_2_nv
NVU_BIG_INPUT_THRESHOLD=250000
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_KEY1-5: 全部 pexec via SOCKS5 mihomo 7894-7899
```

### DB Stats

| Window | Total | OK | Fail | SR | Avg | P50 |
|--------|-------|-----|------|------|------|------|
| 6h | 29 | 25 | 4 | 86.2% | 9738ms | — |

**6h per-model:**
| Model | Total | OK | Fail | SR | Avg | P50 |
|-------|-------|-----|------|------|------|------|
| glm5_2_nv | 24 | 24 | 0 | 100% | 10044ms | 9034ms |
| kimi_nv | 4 | 0 | 4 | 0% | — | — |
| dsv4p_nv | 1 | 1 | 0 | 100% | 2391ms | 2391ms |

**6h hourly trend (OK only):**
| Hour (UTC) | Req | OK | Avg |
|-----------|-----|-----|------|
| 11:00 | 4 | 4 | 8887ms |
| 12:00 | 4 | 4 | 10245ms |
| 13:00 | 4 | 4 | 14686ms |
| 14:00 | 4 | 4 | 10115ms |
| 15:00 | 4 | 4 | 8729ms |
| 16:00 | 9 | 5 | 6561ms |

**6h errors:**
- 4 ATE (status=502): 全部 kimi_nv, 16:47 UTC 2秒内 burst, tiers_tried=1, all_tiers_failed_in_mapped_tier
- 0 phantom ATE (status=200)
- 0 zombie/fallback/peer-fb/429/timeout

**6h tier_attempts:**
- 24 pexec_success: glm5_2_nv
- 2 pexec_SSLEOFError: glm5_2_nv (tier self-recovery)
- 0 other errors

**6h key_cycle_429s:**
- glm5_2_nv: 26 (normal key rotation on successful requests)
- kimi_nv: 0
- dsv4p_nv: 0

**12h errors:**
- 5 ATE (status=502): 全部 kimi_nv, 16:47 UTC burst (4) + 1 旧残余

## 分析

1. **glm5_2_nv 100% SR**: 24/24 OK, P50=9034ms, 零错误. 系统主力模型完美运行.

2. **kimi_nv 4 ATE = 外部 NVCF 函数降级**: 16:47 UTC 2秒内 burst 4连 ATE, 全部呈现 `NV-TIER-DEGRADED-SKIP` → `peer-fb` → `peer returned 502`. 本地 tier 立即进入 DEGRADED cooldown, peer-fb 到 HM2 也返回 502 (HM2 同样无 kimi 可用). 这是 NVCF kimi function_id 上游降级, 非 nv_gw 配置可修复. 失败路径已优化到极致: ATE 在 1ms 内检测到 tier degraded 并短路, peer-fb 在 686ms/16ms 内返回 502.

3. **SSLEOF tier self-recovery**: 2次 SSLEOF (glm5_2_nv pexec) 已通过 tier 内重试自愈, 零影响. NVU_SSLEOF_RETRY_DELAY_S=0.2 已是 floor.

4. **延迟健康**: glm5_2 P50=9034ms, P95 未超标. 小时级 avg 在 6561-14686ms 正常波动区间.

5. **零漂移**: 容器 env 与 compose 完全一致. 所有参数 floor/optimal.

6. **零可配置修复故障**: 4 个失败全部是外部 NVCF 函数降级, peer-fb 也失败证明是上游问题而非本地配置问题.

## 决策: NOP

九连 false trigger (R1808-R1816). HM1 新 commit 到 GitHub 触发脚本检测, 但所有失败均为外部 NVCF 函数降级, 零可配置修复故障. 无参数需调整.

## 评判

| 指标 | 6h | 评价 |
|------|------|------|
| 成功率 | 86.2% (25/29) | ⚠️ (全部为外部 NVCF 降级) |
| glm5_2 SR | 100% (24/24) | ✅ |
| glm5_2 P50 延迟 | 9034ms | ✅ |
| 错误数 | 4 (kimi ATE) | ⚠️ (外部不可控) |
| zombie/fallback/peer-fb | 0 | ✅ |
| 429/超时 | 0 | ✅ |
| SSLEOF | 2 (自愈) | ✅ |
| 参数漂移 | 0 | ✅ |
| 4192 key_cycle | 26 (正常轮转) | ✅ |

铁律:只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
