# R1763: HM2→HM1 — NOP (100% SR零故障, 全参数 floor/optimal, false trigger)

## 数据收集

### 6h DB (nv_requests)
| 指标 | 值 |
|------|-----|
| 总请求 | 24 |
| 成功 (200) | 24 (100.0% SR) |
| 失败 (502) | 0 |
| ATE (status=502) | 0 |
| any_error | 0 |
| zombie | 0 |
| 504 | 0 |
| 429 cascading | 0 |

### 1h DB
| 指标 | 值 |
|------|-----|
| 总请求 | 4 |
| 成功 | 4 (100.0% SR) |
| 失败 | 0 |

### 最近10条请求延迟
| ts | model | status | dur_ms |
|----|-------|--------|--------|
| 05:33 | glm5_2_nv | 200 | 7712 |
| 05:33 | glm5_2_nv | 200 | 12422 |
| 05:03 | glm5_2_nv | 200 | 6120 |
| 05:03 | glm5_2_nv | 200 | 9018 |
| 04:33 | glm5_2_nv | 200 | 5291 |
| 04:33 | glm5_2_nv | 200 | 6238 |
| 04:03 | glm5_2_nv | 200 | 9354 |
| 04:03 | glm5_2_nv | 200 | 6557 |
| 03:33 | glm5_2_nv | 200 | 5053 |
| 03:33 | glm5_2_nv | 200 | 6337 |

P50≈6.3s, P95≈12.4s, max=12.4s. 全部 glm5_2_nv 单模型流量.

### Docker Logs (nv_gw, tail 100)
- 零 error/warn/fail/ATE/zombie/504/429
- 全部 NV-GLM52-ATTEMPT pexec_us_rr 正常轮转 k1-k5
- 55s timeout, 全部成功
- NV-STREAM-BUFFER-FLUSH 正常

### Container Env vs Compose (Drift Check)
| Parameter | Container | Compose | Match |
|-----------|-----------|---------|-------|
| UPSTREAM_TIMEOUT | 55 | 55 | ✓ |
| KEY_COOLDOWN_S | 65 | 65 | ✓ |
| TIER_COOLDOWN_S | 65 | 65 | ✓ |
| TIER_TIMEOUT_BUDGET_S | 195 | 195 | ✓ |
| PEXEC_TIMEOUT_FASTBREAK | 1 | 1 | ✓ |
| EMPTY_200_FASTBREAK | 1 | 1 | ✓ |
| INTEGRATE_TIMEOUT_FASTBREAK | 1 | 1 | ✓ |
| TIER_BUDGET_GLM5_2_NV | 120 | 120 | ✓ |
| TIER_BUDGET_DSV4P_NV | 60 | 60 | ✓ |
| TIER_BUDGET_MINIMAX_M3_NV | 100 | 100 | ✓ |
| PEER_FALLBACK_TIMEOUT | 122 | 122 | ✓ |
| MS_GW_FALLBACK_TIMEOUT | 120 | 120 | ✓ |
| BIG_INPUT_COOLDOWN_S | 7200 | 7200 | ✓ |
| BIG_INPUT_FAIL_N | 1 | 1 | ✓ |
| SSLEOF_RETRY_DELAY_S | 0.5 | 0.5 | ✓ |
| FORCE_STREAM_UPGRADE | 0 | 0 | ✓ |
| FORCE_STREAM_UPGRADE_TIMEOUT | 66 | 66 | ✓ |
| INTEGRATE_KEY_COOLDOWN_S | 0 | 0 | ✓ |

**零容器漂移!** nv_gw uptime=4h, healthy.

## 决策分析

**NOP — 零参数变更, 零 compose 变更, 零容器重启**

### 理由
1. **100% SR 零故障**: 6h 24/24, 1h 4/4 — 无任何可配置故障
2. **全参数 floor/optimal**: 三 FASTBREAK=1 (floor), 所有 BUDGET 已触底, SSLEOF=0.5 (floor), KEY/TIER=65 (R1740 boundary-aligned)
3. **零容器漂移**: 17个参数全部 compose=container 匹配
4. **零 zombie/ATE/504/429**: 仅 glm5_2_nv 单模型流量, 全正常
5. **False trigger**: R1762 已是 NOP (自提交 "这是我提交的, 不触发"), cron 再次派遣
6. **PEER_FALLBACK_TIMEOUT=122**: ≥ HM2 BUDGET(60)+2 ✓, 安全冗余
7. **BUDGET=195**: dsv4p ATE→peer-fb: 60+122=182<195 ✓; glm5_2 zombie→peer-fb: 0+122=122<195 ✓

### 铁律验证
- ✅ 只改HM1不改HM2 — 本轮零配置修改
- ✅ 零容器漂移 — 17参数全部匹配

## Commit
Git commit & push to `gitychzh/NVForge` main. Author=opc2_uname.
## ⏳ 轮到HM1优化HM2
