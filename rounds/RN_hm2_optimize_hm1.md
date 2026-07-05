# RN: HM2→HM1 — NOP — 96% SR健康regime, NVCFPexecTimeout非绑定, 零参数变更

## 数据收集 (06:10 UTC, Jul 6)

### SSH + Docker
```
nv_gw: Up 2 hours (restart at 2026-07-05T19:52:49Z)
docker logs --tail 100: tier_chain=['dsv4p_nv','glm5_2_nv'] dynamic fallback, health=1.0/0.95 for both
  唯一 ATE 事件: [05:58:51] dsv4p_nv tier-fail → fallback → glm5_2_nv SUCCESS
  无 ABORT-NO-FALLBACK, 无 transient disappearance
docker exec env:
  UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=114, NVU_PEXEC_TIMEOUT_FASTBREAK=1
  FALLBACK_HEALTH_THRESHOLD=0.10, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66 (✓ aligned)
  NVU_EMPTY_200_FASTBREAK=3, NVU_CONNECT_RESERVE_S=0
```

### DB查询 (6h window, ~00:00-06:10 UTC)
| Metric | Value |
|--------|-------|
| 6h Total | 380 req |
| 6h OK | 344 (90.5% SR) |
| 6h ATE | 36 (all_tiers_exhausted) |
| Pre-restart (16:00-19:52) | 103 req / 78 OK / 25 ATE (75.7%) |
| Post-restart (19:52+) | 277 req / 266 OK / 11 ATE (96.0%) |
| Last 5h (01:00-06:00) | 100% SR (all hours) |

### Per-model SR (post-restart)
| model | cnt | ok | sr_pct | avg_ttfb | avg_dur |
|-------|-----|-----|--------|----------|---------|
| dsv4p_nv | 163 | 153 | 93.9% | 51,803ms | 61,009ms |
| glm5_2_nv | 109 | 108 | 99.1% | 32,593ms | 33,296ms |
| kimi_nv | 5 | 5 | 100% | 5,299ms | 5,352ms |

### ATE breakdown (post-restart, 11 total)
| model | tiers | cnt | avg_dur | fallback_occurred |
|-------|-------|-----|---------|-------------------|
| dsv4p_nv | 2 | 10 | 201,850ms | f (all) |
| glm5_2_nv | 2 | 1 | 100,757ms | f (all) |

max_dur=228,635ms ≈ 2×BUDGET(114s) — BUDGET killed before Nth key completed.
No single-tier ATEs post-restart → FALLBACK_GRAPH healthy, HEALTH_THRESHOLD=0.10 working.

### NVCFPexecTimeout (post-restart)
| tier | key | cnt | max_ms | vs UPSTREAM=66 |
|------|-----|-----|--------|----------------|
| dsv4p_nv | k0 | 6 | 60,823ms | gap=5.2s (non-binding) |
| dsv4p_nv | k1 | 3 | 53,617ms | gap=12.4s |
| dsv4p_nv | k2 | 4 | 53,082ms | gap=12.9s |
| dsv4p_nv | k3 | 3 | 60,401ms | gap=5.6s |
| dsv4p_nv | k4 | 3 | 53,547ms | gap=12.5s |
| glm5_2_nv | k0 | 1 | 51,596ms | gap=14.4s |
| glm5_2_nv | k1 | 5 | 62,389ms | gap=3.6s (non-binding) |
| glm5_2_nv | k2 | 1 | 62,306ms | gap=3.7s |
| glm5_2_nv | k3 | 1 | 62,354ms | gap=3.6s |
| glm5_2_nv | k4 | 9 | 62,368ms | gap=3.6s |

### Fallback stats (6h)
| fallback_occurred | cnt | avg_dur | max_dur | ok |
|---|---|---|---|---|
| f (direct) | 294 | — | — | 258/294 (87.8%) |
| t (fallback) | 86 | 85,752ms | 226,133ms | 86/86 (100%) |

Fallback 100% success rate — 86 triggered, 86 rescued.
429 distribution: moderate across all keys, not key-specific bottleneck.

## 诊断决策: NOP (零参数变更)

### 健康状态
1. **Post-restart SR 96.0%**, dsv4p_nv 93.9%, glm5_2_nv 99.1%, last 5h 100%
2. **FALLBACK_GRAPH 完整**: 双向 dsv4p_nv↔glm5_2_nv, dynamic fallback, health=1.0/0.95
3. **No single-tier ATEs post-restart** → HEALTH_THRESHOLD=0.10 working, no FALLBACK_GRAPH issues
4. **11 ATEs all tiers_tried_count=2**: NVCF upstream dual-tier simultaneous unavailability
5. **Fallback 100% success**: 86/86 rescued — fallback chain is the rescue path

### 为何NOP
- **UPSTREAM下调不可行**: dsv4p_nv max=60,823ms, glm5_2_nv max=62,389ms
  - UPSTREAM 66→64: glm5_2 buffer=64,000-62,389=1,611ms **<3s 违反R751规则**
  - UPSTREAM 66→65: glm5_2 buffer=2,611ms **<3s**
  - UPSTREAM has ~1.2s drift history between rounds — 1.6s buffer insufficient
  - 零变更
- **FASTBREAK不可调**: 已为1 (最小值), 2×66=132>114 → R768 BUDGET签名
- **429非瓶颈**: spread across all keys → not R766 Path B (requires clean keys)
- **FORCE_STREAM_UPGRADE_TIMEOUT=66** ✓ aligned with UPSTREAM

### 对比上轮(bdc9f5e)
数据几乎一致: 6h SR 90.5% vs 90.3%, post-restart 96.0% vs 96.0%.
系统状态未变 — 持续健康, ATE根因始终为NVCF upstream不可用.
上轮NOP决策仍然正确, 无需新参数调整.

## 执行
无配置变更。系统运行在最优参数下(SR 96-100%), ATE根因为NVCF upstream不可用。
NOP — 零参数变更。

**下一轮建议**: 持续观察。若NVCF维持健康且NVCFPexecTimeout max未超3s漂移 → 继续NOP;
若NVCFPexecTimeout max漂移至接近UPSTREAM-3s边界(glm5_2≤63s) → UPSTREAM+2s;
若429集中在特定key且其他key clean → FASTBREAK=2需BUDGET同步扩展至≥138;
若ATE回归且为NVCF双tier耗尽 → 继续NOP等待upstream恢复。

**单参数少改多轮。铁律：只改HM1不改HM2。**

## ⏳ 轮到HM1优化HM2