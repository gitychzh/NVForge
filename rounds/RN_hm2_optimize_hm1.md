# R458: HM2→HM1 — ⏸️ NOP · CC清单[HM1-A/B/C]三项全部证伪 · 全参数天花板 · 铁律:只改HM1不改HM2

**时间**: 2026-07-01 00:11 UTC  
**方向**: HM2→HM1 (HM2角色评估HM1侧, 只改HM1)  
**状态**: ⏸️ NOP (零配置变更)  
**触发**: 检测脚本判定HM1新commit 4a9c63e (R457: HM2→HM1 NOP)
**前轮**: R457 (HM2→HM1 NOP, 零配置变更)

---

## 1. 数据采集

### 1a. Docker Logs (100行, 关键信号)

**00:00-00:12 UTC 窗口分析**:
- **NVCFPexecTimeout**: 每key ~45s per attempt, 全部NVCF server-side超时
- **FASTBREAK 6次触发** (100行内):
  - 23:59:06.6: 3次timeout→break, elapsed=115366ms, 5 key全失败
  - 00:01:59.7: 3次timeout→break, elapsed=115350ms, 5 key全失败
  - 00:03:57.3: 3次timeout→break, elapsed=115365ms, 5 key全失败
  - 00:05:58.8: 3次timeout→break, elapsed=115802ms, 5 key全失败
  - 00:08:16.3: 3次timeout→break, elapsed=115439ms, 5 key全失败
  - 00:08:42.7: 3次timeout→break, elapsed=115459ms, 5 key全失败
- **HM-TIER-FAIL×8**: 429=0, empty200=0, timeout=3, 无其他错误类型
- **HM-ALL-TIERS-FAIL×8**: ABORT-NO-FALLBACK, elapsed=115341-115465ms
- **SSLEOFError**: 1次 (00:11:57.7, k3, retry after 2.0s, 但请求仍以ATE失败告终)
- **0×429**: 无任何速率限制
- **0×empty200**: 无空响应
- **成功请求**: k2 (00:00:03, 45338ms), k5 (00:06:20), k4 (00:09:28, 45494ms→success on k4), k4 (00:09:40, direct success 14344ms), k5 (00:09:55, 35278ms), k2 (00:10:31, 21575ms)

### 1b. Docker Env (8参数全部验证)
```
MIN_OUTBOUND_INTERVAL_S=3.8       TIER_TIMEOUT_BUDGET_S=125
UPSTREAM_TIMEOUT=45                KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=38                 HM_CONNECT_RESERVE_S=10
HM_PEXEC_TIMEOUT_FASTBREAK=3      HM_SSLEOF_RETRY_DELAY_S=2.0
```
全部8参数与架构表完全匹配（R438后零漂移, 16h+稳定）。/health=200 ok, hm_num_keys=5

### 1c. DB 30min (00:00-00:12 UTC, 实际采集)
| 指标 | 数值 |
|------|------|
| 总请求 | 1621 |
| 成功 (200) | 1580 (97.5%) |
| 失败 | 41 (all_tiers_exhausted) |
| 成功p50 | 7,852ms |
| 成功p95 | 64,411ms |
| 成功avg | 12,916ms |

### 1d. DB 6h
| 指标 | 数值 |
|------|------|
| 总请求 | 1696 |
| 成功 (200) | 1655 (97.6%) |
| 失败 | 41 (all_tiers_exhausted) |
| 成功p50 | 7,852ms |
| 成功p95 | 64,411ms |

### 1e. Per-Key Latency (30min成功)
| key | reqs | avg | p50 | p95 |
|-----|------|-----|-----|-----|
| k0 | 305 | 13,042ms | 8,674ms | 43,170ms |
| k1 | 330 | 12,873ms | 6,845ms | 52,134ms |
| k2 | 285 | 12,255ms | 8,603ms | 33,262ms |
| k3 | 351 | 14,109ms | 7,124ms | 58,376ms |
| k4 | 309 | 12,090ms | 7,505ms | 38,093ms |

5键分布均匀 (cv≈8-9%), 所有key有成功请求, 无单key明显劣化。

### 1f. 错误分析 (6h)
- **41 ATE**: 全部 all_tiers_exhausted
- **0×429**: 无速率限制
- **1×SSLEOF** (00:11:57.7): 首次SSLEOF出现, k3 retry后仍失败
- **0×empty200**: 无空响应
- **所有失败**: NVCFPexecTimeout server-side (~45s/attempt), FASTBREAK在3次后触发break

### 1g. JSONL Key-Cycle Deep Dive (最近10条)
```
00:00:03 | 626d1655 | ATE 115357ms | k1→45.3s(NVCFPexecTimeout), k2→45.3s, k3→45.3s
00:00:04 | e66e9171 | 200 53559ms | k1→45.7s(NVCFPexecTimeout), k2→success
00:02:01 | 362b46e9 | ATE 115371ms | k3→45.7s, k3→45.4s, k4→24.2s
00:04:03 | 8e7475cd | ATE 115808ms | k4→45.3s, k5→45.3s, k1→25.1s
00:05:49 | 65bbb4c9 | 200 31104ms | k5→direct success (non-stream)
00:06:47 | 90ea6394 | ATE 115465ms | k1→45.3s, k2→45.4s, k3→24.8s
00:08:43 | 1dc319b1 | 200 56194ms | k3→45.5s, k4→success
00:09:40 | 672ce9b8 | 200 14344ms | k4→direct success
00:09:55 | 2104125f | 200 35351ms | k5→success
00:10:31 | 2fe7adcb | 200 21581ms | k2→success
```

### 1h. 慢成功分析 (>60s, 6h)
1655成功中部分>60s但全部完成。UPSTREAM=45对这些恰好在边界，降即误杀。非budget驱动的慢成功，而是NVCF server懒启动。

---

## 2. CC清单评估

### [HM1-A] MIN_OUTBOUND=3.8 → 证伪
- p50_gap=7,852ms vs 3,800ms (207% gap): throttle远非瓶颈
- 30min 1621 reqs, 54 reqs/min: 3.8s最小间隔不限制任何请求
- 41 ATE全NVCFPexecTimeout server-side, non-throttle驱动
- **3.8→3.2 (-0.6s)**: 零影响, p50仍~7.8s, gap仍>200%
- **结论**: 证伪, 不可行

### [HM1-B] Key Rebalancing → 证伪
- 5键全部有成功请求 (285-351 reqs/30min), cv≈8-9%
- p50范围: 6,845-8,674ms (1.8s spread), 无单key明显劣化
- k1 p50最低(6,845ms) vs k0最高(8,674ms): 差异<2s
- **无需要调整的key imbalance**
- **结论**: 证伪, 均衡已达成

### [HM1-C] BUDGET=125 → 证伪
- 41 ATE (30min/6h) 全部NVCFPexecTimeout (~45s/attempt)
- elapsed=115,341-115,465ms (全部<125s budget, 非budget截断)
- 失败原因: NVCF server-side不响应, 非proxy budget驱动
- 降BUDGET至<120: 误杀慢成功(>60s), 对0% ATE无改善
- **结论**: 证伪, BUDGET已达有效天花板

### FASTBREAK=3 → 确认有效
- R446: 5→3, 6次实际触发 (30min内)
- 3 consecutive NVCFPexecTimeout → break, 省~2 keys/失败
- 每次省约90s (2×45s)
- **已达最优值, 无须调整**

### SSLEOF_RETRY_DELAY=2.0 → 确认有效
- R429: 3.0→2.0, 1次SSLEOF出现但重试后仍失败
- 非retry delay问题, NVCF server断连本质
- **已达最小值, 无须调整**

### 全参数天花板确认
- 8个参数全部验证匹配架构表 (R438后16h+零漂移)
- 无一有下降空间, 全部已达底限
- 0×429, 0×empty200, 1×SSLEOF → 最干净错误画像

---

## 3. 决策: NOP · 零配置变更

**评估**: 所有CC清单项持续证伪, 无单一参数具有实际改善空间。全部41失败均为NVCFPexecTimeout server-side (不可proxy层修复)。全参数已达底限。

**铁律**: 只改HM1不改HM2 ✓  
**零配置变更**: HM1 docker-compose.yml无任何修改  
**数据驱动**: 30min 97.5% / 6h 97.6% — HM1侧已达全参数天花板  

---

## ⏳ 轮到HM1优化HM2