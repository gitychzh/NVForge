# HM2 Optimize HM1 — Round R965

**日期**: 2026-07-09 13:05 UTC
**触发**: HM2 cron 派遣 (false trigger — 自提交检测)
**类型**: NOP (无参数调整)

---

## 1. 触发分析

- cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author: `opc2_uname` (HM2)
- 脚本正确检测到自提交 — 误触发
- 最新 commit: `6cfa040 R964: HM2→HM1 — NOP (...)` — 上一轮提交
- Symlink 已指向 R964，turn marker 正确 `## ⏳ 轮到HM1优化HM2`

---

## 2. 改前数据 (HM1)

### 2.1 nv_gw env (当前参数)

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 64 | floor |
| TIER_TIMEOUT_BUDGET_S | 114 | floor |
| KEY_COOLDOWN_S | 25 | floor |
| TIER_COOLDOWN_S | 25 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | optimal |
| NVU_EMPTY_200_FASTBREAK | 3 | optimal |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 | sync |
| NVU_FORCE_STREAM_UPGRADE | 0 | disabled |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | defensive |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | standard |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | standard |
| NVU_PEER_FALLBACK_ENABLED | 1 | enabled |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv,dsv4p_nv | data-backed |

### 2.2 nv_requests 6h

| 总计 | 200 | 失败 | SR |
|------|-----|------|----|
| 30 | 30 | 0 | **100%** |

### 2.3 按 upstream_type

| 路径 | 总数 | 200 | avg_ttfb | avg_dur | max_dur |
|------|------|-----|----------|---------|---------|
| nvcf_pexec | 30 | 30 | 47627ms | 47628ms | 173278ms |

### 2.4 错误分类 (6h)

零错误。

### 2.5 nv_tier_attempts 6h

| tier | error_type | cnt | avg_ms | max_ms |
|------|-----------|-----|--------|--------|
| glm5_2_nv | 504_nv_gateway_timeout | 5 | - | - |
| glm5_2_nv | NVCFPexecTimeout | 5 | 51492 | 51796 |
| glm5_2_nv | empty_200 | 2 | - | - |
| glm5_2_nv | budget_exhausted_after_connect | 1 | 51838 | 51838 |

NVCFPexecTimeout ~51.5s << UPSTREAM_TIMEOUT=64 → FASTBREAK=1 正确介入。

### 2.6 最新 10 条请求

3 条 fallback (glm5_2_nv→dsv4p_nv)，2 条 key_cycle_429s=2。全部最终 200。

### 2.7 容器日志 (最新 relevant)

```
[13:04:24] [NV-CYCLE] tier=glm5_2_nv k2 → 504 (504_nv_gateway_timeout), cycling
[13:05:15] [NV-TIMEOUT] tier=glm5_2_nv k3 NVCF pexec timeout: attempt=51312ms total=114055ms
[13:05:15] [NV-PEXEC-FASTBREAK] tier=glm5_2_nv 1 consecutive NVCFPexecTimeout → fast-break
[13:05:15] [NV-TIER-FAIL] tier=glm5_2_nv all 5 keys failed
[13:05:15] [NV-FALLBACK] Tier glm5_2_nv all-failed → falling back to dsv4p_nv
[13:05:18] [NV-FALLBACK-SUCCESS] Success on fallback tier dsv4p_nv
```

### 2.8 ms_gw (40007)

| 6h 总计 | 200 | 失败 | SR |
|---------|-----|------|----|
| 0 | 0 | 0 | N/A |

ms_gw 目前空闲，无优化空间。

---

## 3. 决策

**NOP — 无需参数调整。**

- nv_gw 所有参数已在 floor/optimal 状态
- 6h: 30/30 (100% SR)，零错误
- NVCFPexecTimeout ~51.5s << UPSTREAM_TIMEOUT=64，FASTBREAK=1 正确
- ms_gw 空闲，无优化机会
- 无任何参数需要调整

---

## 4. 验证

- HM1 nv_gw 配置未改动
- 数据与上轮一致 (R964: 27/27 100% SR)
- 所有参数已在 floor
- 铁律遵守: 只观察不改动

---

## 5. 总结

False trigger (double-dispatch) — cron 自提交检测正确标记 "不触发"，但 cron 仍被派遣。
数据稳定，无退化，无优化空间。NOP。

---

## ⏳ 轮到HM1优化HM2