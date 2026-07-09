# HM2 Optimize HM1 — Round R978

**Date**: 2026-07-09 16:15 UTC
**Author**: opc2_uname (HM2)
**Type**: NOP (false trigger, double-dispatch)

---

## 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = opc2_uname (HM2), commit cd4fb1d (R977 NOP)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — double-dispatch (R977 pre-run script already committed NOP + symlink)
- 本轮为 R978，继续 NOP

---

## 6h 数据收集 (2026-07-09 08:15–16:15 UTC)

### 全局聚合
| 指标 | 值 |
|------|-----|
| 总请求 | 33 |
| 成功 (200) | 31 (93.9% SR) |
| 失败 | 2 (ATE) |
| req_with_429cycle | 20 |
| 平均延迟 (成功) | 74,994ms |

### 按模型分布
| 模型 | 请求 | 成功 | 失败 | SR | avg_ok_ms | max_ok_ms |
|------|------|------|------|----|-----------|-----------|
| glm5_2_nv | 29 | 27 | 2 | 93.1% | 82,198 | 173,278 |
| dsv4p_nv | 5 | 5 | 0 | 100% | 21,356 | 44,652 |

### 错误分布
| error_type | error_subcategory | upstream_type | cnt | avg_ms |
|------------|-------------------|---------------|-----|--------|
| all_tiers_exhausted | all_tiers_failed_in_mapped_tier | NULL | 2 | 174,417 |

### Tier 级别尝试 (nv_tier_attempts)
| tier | error_type | cnt | avg_elapsed_ms | max_elapsed_ms |
|------|------------|-----|----------------|----------------|
| glm5_2_nv | NVCFPexecTimeout | 19 | 57,151 | 62,606 |
| glm5_2_nv | 504_nv_gateway_timeout | 6 | — | — |
| glm5_2_nv | empty_200 | 3 | — | — |
| glm5_2_nv | budget_exhausted_after_connect | 1 | 51,838 | 51,838 |

### 最近 10 条请求
| 时间 | 模型 | 状态 | error_type | upstream | dur_ms | fallback | tiers |
|------|------|------|------------|----------|--------|----------|-------|
| 08:19 | glm5_2_nv | 200 | all_tiers_exhausted | NULL | 1,311 | yes | 1 |
| 08:05 | glm5_2_nv | 200 | | nvcf_pexec | 139,129 | yes | 2 |
| 08:03 | glm5_2_nv | 200 | | nvcf_pexec | 113,885 | yes | 2 |
| 07:39 | glm5_2_nv | 502 | all_tiers_exhausted | NULL | 174,468 | no | 2 |
| 07:38 | glm5_2_nv | 200 | | nvcf_pexec | 70,207 | yes | 2 |
| 07:36 | glm5_2_nv | 502 | all_tiers_exhausted | NULL | 174,366 | no | 2 |
| 07:33 | glm5_2_nv | 200 | | nvcf_pexec | 114,393 | yes | 2 |
| 07:31 | glm5_2_nv | 200 | | nvcf_pexec | 83,188 | yes | 2 |
| 07:30 | glm5_2_nv | 200 | | nvcf_pexec | 79,212 | yes | 2 |
| 07:04 | glm5_2_nv | 200 | | nvcf_pexec | 79,869 | yes | 2 |

### 容器日志
```
docker logs nv_gw --tail 100 | grep -iE 'error|warn': (no error/warn found)
```

### 当前 HM1 配置 (env)
| 参数 | 值 |
|------|-----|
| UPSTREAM_TIMEOUT | 64 |
| TIER_TIMEOUT_BUDGET_S | 112 |
| MIN_OUTBOUND_INTERVAL_S | 0 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 |
| KEY_COOLDOWN_S | 25 |
| TIER_COOLDOWN_S | 25 |
| NVU_PEER_FALLBACK_TIMEOUT | 45 |
| NVU_CONNECT_RESERVE_S | 0 |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 |
| NVU_FORCE_STREAM_UPGRADE | 0 |
| NVU_EMPTY_200_FASTBREAK | 3 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 |
| FALLBACK_HEALTH_THRESHOLD | 0.05 |
| KEY_AUTHFAIL_COOLDOWN_S | 60 |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv,dsv4p_nv |

---

## ms_gw 检查

ms_gw 6h: 9 req / 6 ok (status=ok) / 3 error. EMPTY_200_FASTBREAK_THRESHOLD=3 at floor. No optimization opportunity.

---

## 决策: NOP

**数据几乎与 R976/R977 相同**:
- 33 请求 (vs R976 32), 31 OK (93.9% vs 93.8%)
- 2 ATE: 双 tier 耗尽, upstream_type=NULL, ~174s = BUDGET=112 耗尽
- NVCFPexecTimeout max=62,606ms 在 UPSTREAM=64 内 (1,394ms buffer) — R976 变更正在稳定
- FASTBREAK=1 正确 (function-level timeout, 非 per-key)
- EMPTY_200=3, 所有参数在 floor/optimal

**候选参数评估**:
- UPSTREAM_TIMEOUT: 64 已足够 (NVCFPexecTimeout max=62,606ms within buffer)
- BUDGET: 112>>64 safe, 无需调整
- PEER_FALLBACK: 45, 匹配 UPSTREAM+安全余量
- FORCE_STREAM_UPGRADE_TIMEOUT: 64, 与 UPSTREAM=64 对齐
- 所有其他参数在 floor: FASTBREAK=1, CONNECT=0, MIN_OUTBOUND=0, INTEGRATE_COOLDOWN=0
- EMPTY_200=3 已稳定

**结论**: 零变更。R976 UPSTREAM 62→64 变更正在稳定中，NVCFPexecTimeout 已完全在范围内。2 ATE 为 NVCF 上游双 tier 同时不可用，非网关参数可修。

**铁律**: 只改 HM1 不改 HM2。单参数每轮。改前必有数据。

---

## ⏳ 轮到HM1优化HM2