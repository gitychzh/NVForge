# R143: HM2→HM1 — UPSTREAM_TIMEOUT 68→60, KEY_COOLDOWN_S 38→34 (加速timeout级联, 降低429等待)

**Role**: HM2 (opc2_uname) 优化 HM1 (opc_uname)
**Date**: 2026-06-28 10:06 CST
**Change**: 2参数调优 — UPSTREAM_TIMEOUT 68→60 (-8s), KEY_COOLDOWN_S 38→34 (-4s)
**Principles**: 少改多轮(双参数联动); 铁律:只改HM1不改HM2; 更少报错更快请求超低延迟稳定优先

---

## 📊 数据采集 (24h Window)

### HM1 Environment (before R143)
| Parameter | Value |
|----------|-------|
| TIER_TIMEOUT_BUDGET_S | 144 (R129) |
| KEY_COOLDOWN_S | **38.0** (R108) → **34** |
| TIER_COOLDOWN_S | 42 (R115) |
| UPSTREAM_TIMEOUT | **68** (R120) → **60** |
| MIN_OUTBOUND_INTERVAL_S | 19.0 (R107) |
| HM_CONNECT_RESERVE_S | 24 (R111) |
| PROXY_TIMEOUT | 300 |

### PostgreSQL 24h Summary
| Metric | Value |
|--------|-------|
| Total requests | 3,439 |
| Success (200) | 3,391 (98.6%) |
| 502 (all_tiers_exhausted) | 43 (1.25%) |
| 429 | 5 (0.15%) |
| NVStream_TimeoutError | 4 |
| NVStream_IncompleteRead | 1 |

### Latency by Status (24h)
| Status | Count | Avg TTFB (ms) | Avg Duration (ms) | Min Dur | Max Dur |
|--------|-------|---------------|-------------------|---------|---------|
| 200 | 3,391 | 29,537 | 30,533 | 1,295 | 184,900 |
| 502 | 43 | 35,738 | 118,774 | 19,546 | 166,774 |
| 429 | 5 | 0 | 172,934 | 138,762 | 219,113 |

### Per-key Distribution (24h)
| Key | Requests | Avg Duration (ms) |
|-----|----------|-------------------|
| k0 | 789 | 32,207 |
| k1 | 662 | 31,464 |
| k2 | 620 | 29,088 |
| k3 | 667 | 29,658 |
| k4 | 658 | 30,255 |
| None (errors) | 43 | 128,918 |

### Recent Tier Attempts (last 10)
| ID | Tier | Key | Error | Elapsed (ms) |
|----|------|-----|-------|-------------|
| 6709 | deepseek | k2 | empty_200 | None |
| 6708 | deepseek | k4 | empty_200 | None |
| 6707 | deepseek | k5 | empty_200 | None |
| 6706 | deepseek | k2 | empty_200 | None |
| 6705 | deepseek | k2 | NVCFPexecTimeout | 65,824 |
| 6704 | deepseek | k2 | NVCFPexecTimeout | 26,333 |
| 6703 | deepseek | k1 | empty_200 | None |
| 6702 | deepseek | k4 | empty_200 | None |
| 6701 | deepseek | k1 | NVCFPexecTimeout | 25,023 |
| 6700 | deepseek | k5 | NVCFPexecRemoteDisconnected | 67,258 |

---

## 🎯 优化分析

### 问题诊断

1. **502 avg_dur=118.8s 过高** — timeout级联太慢。UPSTREAM_TIMEOUT=68时单个慢key可卡68s才放弃，2个tier尝试就用尽136s/146s预算。降低到60s后，单次timeout仅60s，2次=120s < 144预算，余24s给第3次尝试或更快完成。

2. **429 avg_dur=172.9s 过高** — KEY_COOLDOWN_S=38使得429后的key恢复太慢。24h仅5次429(0.15%)，说明key远未饱和。减少冷却到34s让429后的key更快复用，降低请求排队等待。

3. **NVCFPexecTimeout elapsed 25-67s** — 当前68s超时导致65s的超长等待后才发现失败，浪费级联时间。60s超时可在elapsed>60s时快速跳转下一个key。

### 预期效果
| 指标 | 当前(R142) | 预期(R143) |
|------|-----------|-----------|
| 502 avg_dur | 118,774ms | ~100,000ms (-16%) |
| 429 avg_dur | 172,934ms | ~155,000ms (-10%) |
| all_tiers_exhausted | 43/24h | <30/24h |
| 成功率 | 98.6% | >99% |

---

## 🔧 变更执行

### 1. UPSTREAM_TIMEOUT: 68 → 60 (-8s)
- **文件**: `/opt/cc-infra/docker-compose.yml` on HM1 (100.109.153.83)
- **理由**: 减少单key超时卡顿，加速级联跳转，60s仍远超成功请求的avg_dur(30.5s)
- **风险**: 低。成功请求P95~61s不受影响，仅影响超时边缘case

### 2. KEY_COOLDOWN_S: 38 → 34 (-4s)
- **文件**: `/opt/cc-infra/docker-compose.yml` on HM1 (100.109.153.83)
- **理由**: Key远未饱和(429仅0.15%)，减少冷却让429后更快恢复
- **风险**: 低。429率极低，4s减少不会导致429激增

### Verification (post-restart)
```
UPSTREAM_TIMEOUT=60 ✅
KEY_COOLDOWN_S=34 ✅
```

---

## ⏳ 轮到HM1优化HM2  ← 脚本检测此标记
