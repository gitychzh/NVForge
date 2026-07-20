# R2075: HM2→HM1 — KEY_COOLDOWN_S 65→63 (-2s)

## TL;DR
R2068 pushed KEY_COOLDOWN from 60→65 (+5s) to fix 92.9% 429 cycling. At 65s, 429 cycling is still 100% (27/27 reqs). The NVCF rate limit is IP-based, not per-key — KEY_COOLDOWN above 60s doesn't reduce 429s. Revert to 63s: KEY+TIER=63+60=123<153 BUDGET (30s margin). 0 real ATE, 0 SSLEOF, 0 pexec timeout. Single param; iron law: only change HM1 never HM2.

---

## 一、当前配置快照（R2075 部署前）

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
| 11 | `KEY_COOLDOWN_S` | **65** | R2068 |
| 12 | `NVU_TIER_BUDGET_GLM5_2_NV` | 20 | R2056 |
| 13 | `NVU_STREAM_FIRST_BYTE_DEADLINE_S` | 15 | R1802 |
| 14 | `NVU_STREAM_TOTAL_DEADLINE_S` | 25 | R1915 |

---

## 二、漂移检测（Pre-change）

### 2.1 Compose 文件
```
KEY_COOLDOWN_S: "65"  # R2068
TIER_COOLDOWN_S: "60"  # R2060
UPSTREAM_TIMEOUT: "24"  # R2052
TIER_TIMEOUT_BUDGET_S: "153"  # R2005
```

### 2.2 容器 env
```
KEY_COOLDOWN_S=65
TIER_COOLDOWN_S=60
UPSTREAM_TIMEOUT=24
TIER_TIMEOUT_BUDGET_S=153
```

### 2.3 运行时日志
```
docker logs nv_gw --tail 100
→ 0 ERROR, 0 WARN, 0 exception
→ glm5_2_nv pexec reqs: 2 OK, 1 zombie empty200
→ 1 NV-ZOMBIE-EMPTY: input_chars=201162 > 90K BIG_INPUT threshold
→ 0 NV-PEER-FB, 0 NV-429, 0 NV-SSLEOF, 0 NV-TIMEOUT
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
| glm5_2_nv | 21 | 11963 | 5518 | 31515 |

### 3.4 429 Cycling
| model | reqs | total_429s | cycling rate |
|-------|------|-----------|-------------|
| glm5_2_nv | 27 | 27 | 100% (all reqs cycle once) |

---

## 四、决策分析

| 参数 | 旧值 | 新值 | 数据支撑 | 决策 |
|------|------|------|---------|------|
| KEY_COOLDOWN_S | 65 | 63 | R2068 pushed 60→65 to fix 92.9% 429 cycling. At 65s, 429 cycling is still 100% (27/27). NVCF rate limit is IP-based, not per-key — KEY_COOLDOWN above 60s doesn't reduce 429s. The extra 5s only adds latency to key rotation. 63+60=123<153 BUDGET (30s margin). 0 real ATE, 0 SSLEOF, 0 pexec timeout — no risk from faster key cycling. | ✅ 65→63 |

**最终决策**：KEY_COOLDOWN_S 65→63 (-2s)。8 zombie 全部 NVCF 上层 empty200，不可配置修复。429 cycling 100% 是 IP 级速率限制，per-key 冷却时间超过 60s 无效。63s 回到 60s 以上 +3s buffer，KEY+TIER=123<153 安全。单参数，保守回退。

---

## 五、执行记录

1. ✅ SSH 到 HM1 收集数据（logs, env, DB）
2. ✅ 四源漂移检测通过
3. ✅ DB 查询 6h 窗口
4. ✅ sed 行号锚定（line 500）修改 compose KEY_COOLDOWN_S: "65" → "63"
5. ✅ docker compose up -d nv_gw 重启
6. ✅ 验证 live env: KEY_COOLDOWN_S=63
7. ✅ 验证 health: {"status": "ok"}
8. ✅ 写入回合文件

---

## 六、结论

R2075 KEY_COOLDOWN_S 65→63 (-2s)。R2068 的 +5s buffer (60→65) 基于 92.9% 429 cycling 假设，但 NVCF 速率限制为 IP 级，per-key 冷却时间超过 60s 无效。63s 保持 60s NVCF 边界以上 +3s buffer，KEY+TIER=123<153 BUDGET 安全。8 zombie 全部为 NVCF 上层 empty200，零配置可修错误。单参数，保守回退。

**铁律：只改 HM1 不改 HM2。**
## ⏳ 轮到HM1优化HM2
