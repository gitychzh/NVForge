# R1006: NOP — dsv4f0731_nv 当前健康，无参数修改

**日期**: 2026-08-07 21:36 UTC  
**容器**: dsvf0731_nv (port 40666)  
**模型**: dsv4f0731_nv (DeepSeek V4 Pro via NVCF)  

## 数据摘要

### 30min 窗口
| 指标 | 值 |
|------|----|
| 总数 | 124 |
| 成功 | 124 |
| 失败 | 0 |
| 无内容 | 0 |
| SR% | **100%** |
| Avg(ms) | 12692 |
| P50(ms) | 10099 |
| P95(ms) | 31595 |
| Max(ms) | 55657 |

### 错误分布
- 无任何错误 (0 429, 0 timeout, 0 other)

### Per-key 延迟
| Key | Count | Avg(ms) | P95(ms) |
|-----|-------|---------|---------|
| k0 | 24 | 10198 | 22914 |
| k1 | 23 | 11426 | 22120 |
| k2 | 26 | 12737 | 28290 |
| k3 | 26 | 15570 | 36187 |
| k4 | 25 | 13210 | 21215 |

### Upstream 分布
- nvcf_pexec: 124/124 (100%)

### Finish Reason
- tool_calls: 100 (80.6%)
- stop: 24 (19.4%)

### 趋势
- **6h**: 1845 total, 1817 success, 28 无内容 → SR=98.5%
- **3h 逐小时**: 100%/99%/98%/100%
- **24h all_tiers_exhausted**: 212

### hm4104 fallback
- 最近 5min: 无 fallback 日志

## 评估
当前状态完全健康：
- 30min SR=100%, 6h SR=98.5%
- 无任何错误
- 无 fallback
- 延迟稳定 (avg 12.7s, P95 31.6s — 对 dsv4f 合理)
- k3 略慢 (avg 15.6s vs 12.7s 整体)，但无错误，不构成优化理由

## 决策
**NOP** — 不改任何参数。持续监控。

## 参数当前值 (未改动)
| 参数 | 值 |
|------|----|
| UPSTREAM_TIMEOUT | 90 |
| TIER_TIMEOUT_BUDGET_S | 180 |
| TIER_COOLDOWN_S | 90 |
| KEY_COOLDOWN_S | 30 |
| NVU_TIER_BUDGET_DSV4F_NV | 180 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 3 |
| NVU_EMPTY_200_FASTBREAK | 3 |
| NVU_KEYMGR_429_BASE_COOLDOWN | 120 |
| NVU_KEYMGR_429_MAX_COOLDOWN | 120 |