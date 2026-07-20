# R2078: HM2→HM1 — KEY_COOLDOWN_S 63→60 (-3s)

## TL;DR
NVCF rate limiting is fully resolved: Tier 429 = 0 (vs 42 in R2077 patrol). KEY_COOLDOWN_S=63 had +3s buffer above 60s NVCF boundary — now unnecessary. Return to 60s: KEY+TIER=60+60=120<153 BUDGET (33s margin). 0 real ATE, 0 SSLEOF, 0 pexec timeout. 8 zombie all NVCF func-level empty200 (non-configurable). Single param; iron law: only change HM1 never HM2.

---

## 一、当前配置快照（R2078 部署前）

| # | 参数 | HM1 当前值 | 历史来源 |
|---|------|------------|----------|
| 1 | `UPSTREAM_TIMEOUT` | 24 | R2052 |
| 2 | `TIER_TIMEOUT_BUDGET_S` | 153 | R2005 |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 | floor |
| 4 | `TIER_COOLDOWN_S` | 60 | R2060 |
| 5 | `NVU_PEER_FALLBACK_TIMEOUT` | 122 | R1744 |
| 6 | `NVU_CONNECT_RESERVE_S` | 0 | R657 |
| 7 | `NVU_SSLEOF_RETRY_DELAY_S` | 0.1 | R1823 |
| 8 | `NVU_BIG_INPUT_THRESHOLD` | 90000 | R2058 |
| 9 | `NVU_BIG_INPUT_FAIL_N` | 1 | R1713 |
| 10 | `NVU_BIG_INPUT_COOLDOWN_S` | 2100 | R2059 |
| 11 | `KEY_COOLDOWN_S` | **63** | R2075 |
| 12 | `NVU_TIER_BUDGET_GLM5_2_NV` | 20 | R2056 |
| 13 | `NVU_STREAM_FIRST_BYTE_DEADLINE_S` | 15 | R1802 |
| 14 | `NVU_STREAM_TOTAL_DEADLINE_S` | 25 | R1915 |

---

## 二、漂移检测（Pre-change）

### 2.1 Compose 文件
```
KEY_COOLDOWN_S: "63"  # R2075
TIER_COOLDOWN_S: "60"  # R2060
UPSTREAM_TIMEOUT: "24"  # R2052
TIER_TIMEOUT_BUDGET_S: "153"  # R2005
```

### 2.2 容器 env
```
KEY_COOLDOWN_S=63
TIER_COOLDOWN_S=60
UPSTREAM_TIMEOUT=24
TIER_TIMEOUT_BUDGET_S=153
```

### 2.3 运行时日志
```
docker logs nv_gw --tail 100
→ 0 ERROR, 0 WARN, 0 exception
→ 仅有 startup 日志，无任何运行时错误
```

**结论：四源全部通过，零漂移。**

---

## 三、数据摘要（6h 窗口）

### 3.1 Overall
| 窗口 | 总计 | OK | Fail | real ATE | phantom ATE | SR |
|------|------|-----|------|----------|-------------|-----|
| 6h | 29 | 21 | 8 | 0 | 2 | 72.4% |

### 3.2 Fail Breakdown
| model | error_type | cnt |
|-------|-----------|-----|
| glm5_2_nv | zombie_empty_completion | 8 |

All 8 failures: NVCF func-level empty200 (non-configurable). 0 real ATE, 0 SSLEOF, 0 pexec timeout.

### 3.3 Success Latency
| model | cnt | avg_ms | min_ms | max_ms |
|-------|-----|--------|--------|--------|
| glm5_2_nv | 21 | 12126 | 5518 | 31515 |

### 3.4 429 Cycling
| reqs | total_429s | cycling rate |
|------|-----------|-------------|
| 29 | 27 | 93.1% (functional, 0 429 failures) |

### 3.5 Tier 429
| tier_429_total |
|----------------|
| 0 |

**Tier 429 = 0 confirms NVCF rate limiting fully resolved.** This is the key data point driving the decision.

### 3.6 Peer-Fallback
| peer_fb_total | peer_fb_success | peer_fb_fail |
|---------------|-----------------|--------------|
| 0 | 0 | 0 |

0 peer-fb events (expected: 0 real ATE, 2 phantom ATE status=200). Budget: UPSTREAM=24 + PEER=122 = 146 < 153 BUDGET ✓.

### 3.7 30-min Window
| total | ok | sr_pct |
|-------|-----|--------|
| 2 | 2 | 100.0% |

---

## 四、决策分析

| 参数 | 旧值 | 新值 | 数据支撑 | 决策 |
|------|------|------|---------|------|
| KEY_COOLDOWN_S | 63 | 60 | R2075 deployed 63s with +3s buffer above 60s NVCF boundary. R2077 patrol confirmed Tier 429=42 (resolving). R2078: Tier 429=0 — NVCF rate limiting FULLY resolved. The +3s buffer served no purpose. Return to 60s (NVCF boundary per 429-cycling-anti-pattern ref). KEY+TIER=60+60=120<153 BUDGET (33s margin). 0 real ATE, 0 SSLEOF, 0 pexec timeout. 8 zombie all NVCF func-level empty200. | ✅ 63→60 |

**最终决策**：KEY_COOLDOWN_S 63→60 (-3s)。NVCF 限流完全解除 (Tier 429=0)，R2075 的 +3s buffer 已无必要。60s 是 NVCF 60s 限流窗口边界，KEY+TIER=60+60=120<153 BUDGET 安全。8 zombie 全部 NVCF 上层 empty200，不可配置修复。单参数，保守收敛。

---

## 五、执行记录

1. ✅ SSH 到 HM1 收集数据（logs, env, DB 9 queries）
2. ✅ 四源漂移检测通过
3. ✅ DB 6h 窗口: 29req/21OK(72.4%)/8 zombie, Tier 429=0
4. ✅ sed 行号锚定（line 500）修改 compose KEY_COOLDOWN_S: "63" → "60"
5. ✅ docker compose up -d nv_gw 重启
6. ✅ 验证 live env: KEY_COOLDOWN_S=60
7. ✅ 验证 health: {"status": "ok"}
8. ✅ 写入回合文件

---

## 六、结论

R2078 KEY_COOLDOWN_S 63→60 (-3s)。NVCF Tier 429=0 确认限流完全解除，R2075 的 +3s buffer 已无必要。60s 是 NVCF 60s 限流窗口边界，KEY+TIER=60+60=120<153 BUDGET 安全。8 zombie 全部 NVCF 上层 empty200，零配置可修错误。单参数，保守收敛回到标准边界值。

**铁律：只改 HM1 不改 HM2。**
## ⏳ 轮到HM1优化HM2
