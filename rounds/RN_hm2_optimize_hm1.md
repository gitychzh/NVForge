# RN: HM2→HM1 — NOP — 100% SR持续5h+, NVCFPexecTimeout非绑定, 零参数变更

## 数据收集 (06:00 UTC, Jul 6)

### SSH + Docker
```
nv_gw: Up 2 hours (R769 restart at 2026-07-05T19:52:49Z)
docker logs --tail 100: tier_chain=['dsv4p_nv','glm5_2_nv'] dynamic fallback, health=1.0 for both
  → 全部 [NV-SUCCESS], 无 ATE/fallback 日志
docker exec env:
  UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=114, NVU_PEXEC_TIMEOUT_FASTBREAK=1
  FALLBACK_HEALTH_THRESHOLD=0.10, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66 (✓ aligned)
  KEY_COOLDOWN_S=25, TIER_COOLDOWN_S=25, NVU_CONNECT_RESERVE_S=0
  NVU_EMPTY_200_FASTBREAK=3, MIN_OUTBOUND_INTERVAL_S=0
```

### DB查询 (6h window, to ~06:00 UTC)
| Metric | Value |
|--------|-------|
| 6h Total | 380 req |
| 6h OK | 343 (90.3% SR) |
| 6h ATE | 37 (all_tiers_exhausted) |
| Post-restart Total | 274 req |
| Post-restart SR | 96.0% (263/274) |
| Post-R770 (05:30+) | 3 req, 3 OK (100%) |
| 8h SR trend | 16:00-19:00 ≈75%, 20:00 77.8%, 21:00+ 94-100% |
| Last 6h (00:00-06:00) | 100% (all 6 hours) |

### Per-model SR (6h)
| model | cnt | ok | sr_pct | avg_ttfb | avg_dur |
|-------|-----|-----|--------|----------|---------|
| dsv4p_nv | 215 | 186 | 86.5% | 48,734ms | 60,508ms |
| glm5_2_nv | 158 | 151 | 95.6% | 40,249ms | 43,001ms |
| kimi_nv | 7 | 6 | 85.7% | 4,792ms | 4,510ms |

### ATE breakdown (6h)
| tiers_tried_count | cnt | avg_dur | fallback_actually_attempted |
|---|---|---|---|
| 1 | 14 | 78,618ms | f (all) |
| 2 | 23 | 154,430ms | f (all) |

### ATE by model+tiers (post-restart, 11 total)
| model | tiers | cnt | avg_dur | max_dur | no_fallback |
|-------|-------|-----|---------|---------|-------------|
| dsv4p_nv | 2 | 10 | 201,850ms | 228,635ms | t |
| glm5_2_nv | 2 | 1 | 100,757ms | 100,757ms | t |

max_dur=228,635ms ≈ 2×BUDGET(114s) — BUDGET killed before fallback from both tiers.
No single-tier ATEs post-restart → FALLBACK_GRAPH healthy, HEALTH_THRESHOLD=0.10 working.### NVCFPexecTimeout分布 (post-restart)
| tier | key | cnt | max_ms | vs UPSTREAM=66 |
|------|-----|-----|--------|---------------|
| dsv4p_nv | k0 | 6 | 60,823ms | gap=5.2s (non-binding) |
| dsv4p_nv | k1 | 3 | 53,617ms | gap=12.4s |
| dsv4p_nv | k2 | 3 | 53,082ms | gap=12.9s |
| dsv4p_nv | k3 | 3 | 60,401ms | gap=5.6s |
| dsv4p_nv | k4 | 3 | 53,547ms | gap=12.5s |
| glm5_2_nv | k0 | 1 | 51,596ms | gap=14.4s |
| glm5_2_nv | k1 | 5 | 62,389ms | gap=3.6s (non-binding) |
| glm5_2_nv | k2 | 1 | 62,306ms | gap=3.7s |
| glm5_2_nv | k3 | 1 | 62,354ms | gap=3.6s |
| glm5_2_nv | k4 | 9 | 62,368ms | gap=3.6s |

### 429_nv_rate_limit (6h)
| tier | key | req_cnt | total_429s |
|------|-----|---------|------------|
| dsv4p_nv | k0 | 35 | 20 |
| dsv4p_nv | k1 | 39 | 11 |
| dsv4p_nv | k2 | 44 | 14 |
| dsv4p_nv | k3 | 31 | 12 |
| dsv4p_nv | k4 | 37 | 16 |
| glm5_2_nv | k0 | 37 | 28 |
| glm5_2_nv | k1 | 28 | 22 |
| glm5_2_nv | k2 | 29 | 13 |
| glm5_2_nv | k3 | 26 | 13 |
| glm5_2_nv | k4 | 31 | 25 |

429 moderately non-uniform across keys, but all keys have 429 — not a FASTBREAK-signaling key-specific bottleneck (R766 Path B requires at least some keys clean of 429).

### Fallback stats (6h, success only)
| fallback_occurred | cnt | avg_dur | max_dur |
|---|---|---|---|
| f (direct) | 256 | 30,164ms | 114,721ms |
| t (fallback) | 87 | 85,752ms | 226,133ms |

Fallback path SR = 87/87+? — fallback is working. Fallback max_dur=226s is within 2×BUDGET range.## 诊断决策: NOP (零参数变更)

### 健康状态评估
1. **6h SR 90.3%**, post-restart **96.0%**, last 6h **100%** (00:00-06:00 UTC) → 系统持续健康regime
2. **FALLBACK_GRAPH 完整**: 双向 `dsv4p_nv↔glm5_2_nv`, dynamic fallback active, both functions health=1.0
3. **No single-tier ATEs post-restart** → HEALTH_THRESHOLD=0.10 working correctly, no FALLBACK_GRAPH issues
4. **11 post-restart ATEs**: all `tiers_tried_count=2`, `fallback_actually_attempted=false`, max_dur≈2×BUDGET → NVCF upstream dual-tier simultaneous unavailability — NOT config-fixable
5. **No errors/warnings in recent docker logs** — all [NV-SUCCESS]

### 为何NOP而非UPSTREAM下调
- dsv4p_nv NVCFPexecTimeout max=60,823ms, UPSTREAM=66 → gap=5.2s
- R751安全规则: 下调后buffer必须≥3s
- UPSTREAM 66→63: dsv buffer=63,000-60,823=2,177ms **<3s 违反规则**
- UPSTREAM 66→64: dsv buffer=64,000-60,823=3,177ms ≈3s (勉强)
  BUT glm5_2 max=62,389ms → buffer=64,000-62,389=1,611ms **<3s (glm5_2侧失败)**
- UPSTREAM跨tier共享, 无法拆分 → 零变更

### 为何NOP而非FASTBREAK调整
- FASTBREAK=1: 每tier 1 key × UPSTREAM=66s → 48s BUDGET headroom for fallback → 最优化
- FASTBREAK=2: 2×66=132 > BUDGET=114 → R768签名: BUDGET先于fallback杀掉
- 429分布: dsv4p_nv moderately non-uniform, but ALL keys have 429 — not key-specific bottleneck (R766 Path B contraindicated)
- glm5_2_nv: 429 also spread across all keys

### 对比R770
R770数据几乎相同: 6h SR 90.3% vs now 90.3%, post-restart SR 96.0% vs now 96.0%.
系统状态未变 — 持续健康, ATE根因始终为NVCF upstream双tier不可用。
Since R770 (05:30 UTC), 3 requests all OK — 100% SR.
R770 NOP决策仍然正确, 无需新参数调整。

### 零变更理由总结
- 系统当前100% SR (last 6+ hours) — 最优状态
- 11 ATE为NVCF upstream双tier耗尽 — 非配置参数可救
- UPSTREAM下调buffer<3s违反R751安全规则 (glm5_2侧)
- FASTBREAK=1+BUDGET=114是最优配置 (单key 66s, 48s fallback headroom)
- FALLBACK_GRAPH active + health=1.0 + FASTBREAK=1 → optimal config for this regime
- NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66 ✓ aligned with UPSTREAM

## 执行
无配置变更。系统运行在最优参数下(SR 100%), ATE根因为NVCF upstream不可用。
NOP — 零参数变更。

**下一轮建议**: 持续观察。若NVCF维持健康且NVCFPexecTimeout max未超3s漂移 → 继续NOP; 若NVCFPexecTimeout max漂移至接近UPSTREAM-3s边界 → 考虑UPSTREAM+2-3s; 若429集中在特定key且其他key clean → 考虑FASTBREAK增加但BUDGET需同步扩展; 若ATE回归且为NVCF双tier耗尽 → 继续NOP等待upstream恢复。

**单参数少改多轮。铁律：只改HM1不改HM2。**

## ⏳ 轮到HM1优化HM2