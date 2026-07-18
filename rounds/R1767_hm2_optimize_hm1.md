# R1767: HM2→HM1 — NOP (100% SR零故障, 全参数 floor/optimal, false trigger)

## 数据收集

### 6h DB (nv_requests)
| 指标 | 值 |
|------|-----|
| 总请求 | 24 |
| 成功 (200) | 24 (100.0% SR) |
| 失败 (502) | 0 |
| ATE (status=502) | 0 |
| zombie | 0 |
| 504 | 0 |
| cascade429 | 24 (key_cycle_429s=1, all succeeded) |

### 1h DB
| 指标 | 值 |
|------|-----|
| 总请求 | 4 |
| 成功 | 4 (100.0% SR) |
| 失败 | 0 |

### 模型分布 (6h)
| mapped_model | cnt | ok | fail |
|-------------|-----|----|------|
| glm5_2_nv | 24 | 24 | 0 |

### 错误分布 (6h)
| error_type | cnt |
|------------|-----|
| (none) | — |

### Tier Attempts (6h)
| tier | error_type | cnt |
|------|-----------|-----|
| glm5_2_nv | pexec_success | 23 |
| glm5_2_nv | pexec_500 | 1 |

唯一1次 pexec_500 在上一轮窗口 (03:03:20, tiers_tried=2) — 网关自动重试下一个key成功。本轮无新增。

### 延迟统计 (6h, 200 only)
| 指标 | 值 |
|------|-----|
| P50 | 7,577ms |
| P95 | 14,469ms |
| Max | 19,968ms |
| Avg | 8,203ms |

### 最近10条请求延迟
| ts | model | status | dur_ms | key_cycle_429s |
|----|-------|--------|--------|----------------|
| 06:33 | glm5_2_nv | 200 | 8670 | 1 |
| 06:33 | glm5_2_nv | 200 | 18918 | 1 |
| 06:03 | glm5_2_nv | 200 | 6002 | 1 |
| 06:03 | glm5_2_nv | 200 | 7825 | 1 |
| 05:33 | glm5_2_nv | 200 | 7712 | 1 |
| 05:33 | glm5_2_nv | 200 | 12422 | 1 |
| 05:03 | glm5_2_nv | 200 | 6120 | 1 |
| 05:03 | glm5_2_nv | 200 | 9018 | 1 |
| 04:33 | glm5_2_nv | 200 | 5291 | 1 |
| 04:33 | glm5_2_nv | 200 | 6238 | 1 |

全部 glm5_2_nv 单模型流量。所有请求 key_cycle_429s=1 — NVCF per-key rate limiting 正常行为，网关透明轮转5个key后全部成功。

### Docker Logs (nv_gw, tail 30)
- 零 error/warn/fail/ATE/zombie/504/429
- 全部 NV-GLM52-ATTEMPT pexec_us_rr 正常轮转 k1-k5
- 55s timeout, 全部成功
- NV-STREAM-BUFFER-FLUSH 正常

### Health Check
- nv_gw: ok (5 keys, 3 models: kimi_nv/dsv4p_nv/glm5_2_nv)

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
| STREAM_FIRST_BYTE_DEADLINE_S | 17 | 17 | ✓ |
| STREAM_TOTAL_DEADLINE_S | 25 | 25 | ✓ |
| CONNECT_RESERVE_S | 0 | 0 | ✓ |
| MIN_OUTBOUND_INTERVAL_S | 0 | 0 | ✓ |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | 0.05 | ✓ |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | 0.05 | ✓ |

**零容器漂移!** 24参数全部 compose=container 匹配。

## 决策分析

**NOP — 零参数变更, 零 compose 变更, 零容器重启**

### 理由
1. **100% SR 零故障**: 6h 24/24, 1h 4/4 — 无任何可配置故障
2. **全参数 floor/optimal**: 三 FASTBREAK=1 (floor), 所有 BUDGET 已触底, SSLEOF=0.5 (floor), KEY/TIER=65 (R1740 boundary-aligned), INTEGRATE_COOLDOWN=0 (floor), CONNECT_RESERVE=0 (floor), MIN_OUTBOUND=0 (floor)
3. **零容器漂移**: 24个参数全部 compose=container 匹配
4. **零 zombie/ATE/504**: 仅 glm5_2_nv 单模型流量, 全正常
5. **key_cycle_429s=1 全请求**: NVCF per-key rate limiting 正常行为, 5-key轮转透明处理, 全部成功 — 非配置问题
6. **唯一 pexec_500**: 03:03:20 一次key返回500, 网关自动重试下一个key成功 (tiers_tried=2) — 自动恢复, 不需配置干预
7. **False trigger**: R1763/R1764/R1765/R1766 连续 NOP, cron 再次派遣 → R1767 继续 NOP
8. **PEER_FALLBACK_TIMEOUT=122**: ≥ HM2 BUDGET(60)+2 ✓, 安全冗余
9. **BUDGET=195**: dsv4p ATE→peer-fb: 60+122=182<195 ✓; glm5_2 zombie→peer-fb: 0+122=122<195 ✓
10. **cc4101 healthy**: 零错误
11. **ms_gw healthy**: 零 error/warn, 0 cooldowns

### 铁律验证
- ✅ 只改HM1不改HM2 — 本轮零配置修改
- ✅ 零容器漂移 — 24参数全部匹配

## Commit
Git commit & push to `gitychzh/NVForge` main. Author=opc2_uname.
## ⏳ 轮到HM1优化HM2
