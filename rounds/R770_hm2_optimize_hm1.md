# R770: HM2→HM1 — NOP — 95.8% SR健康regime, 仅11 ATE全为NVCF upstream不可用, 零参数变更

## 数据收集

### SSH + Docker
```bash
ssh -p 222 opc_uname@100.109.153.83
docker ps                           # nv_gw (runs on port 40006)
docker logs nv_gw --tail 200        # tier_chain=['dsv4p_nv','glm5_2_nv'] dynamic fallback, health=1.0
docker exec nv_gw env               # UPSTREAM=66, BUDGET=114, FASTBREAK=1
docker inspect --format '{{.State.StartedAt}}' # 2026-07-05T19:52:49Z (R769 restart)
```

### DB查询 (6h window, to 05:30 UTC)
| Metric | Value |
|--------|-------|
| 6h Total | 382 req |
| 6h OK | 345 (90.3% SR) |
| 6h ATE | 37 (all_tiers_exhausted) |
| Post-restart Total | 274 req |
| Post-restart SR | 96.0% (263/274) |
| Last 5h SR | 100% (00:00-05:00+ UTC) |
| Pre-restart SR | 75.5% (old config state) |

### ATE breakdown (6h)
| tiers_tried_count | cnt | avg_dur | fallback_actually_attempted |
|---|---|---|---|
| 1 | 14 | 78,618ms | f (all) |
| 2 | 23 | 154,430ms | f (all) |

### Post-restart ATE (11 total)
| model | tiers_tried_count | cnt | avg_dur | max_dur |
|-------|---|---|---|---|
| dsv4p_nv | 2 | 10 | 201,850ms | 228,635ms |
| glm5_2_nv | 2 | 1 | 100,757ms | 100,757ms |

max_dur=228,635ms ≈ 2×BUDGET(114s) → BUDGET killed both tiers before fallback.

### NVCFPexecTimeout分布 (6h)
| tier | key | cnt | max_ms |
|------|-----|-----|--------|
| dsv4p_nv | k0 | 7 | 60,823ms |
| dsv4p_nv | k1 | 4 | 59,596ms |
| dsv4p_nv | k2 | 3 | 53,082ms |
| dsv4p_nv | k3 | 5 | 60,401ms |
| dsv4p_nv | k4 | 3 | 53,547ms |
| glm5_2_nv | k0 | 7 | 51,596ms |
| glm5_2_nv | k1 | 13 | 62,389ms |
| glm5_2_nv | k2 | 6 | 62,306ms |
| glm5_2_nv | k3 | 9 | 62,354ms |
| glm5_2_nv | k4 | 17 | 62,368ms |

### 429_nv_rate_limit (dsv4p_nv, 6h)
| key | total_429s | req_cnt |
|-----|------------|---------|
| k0 | 20 | 35 |
| k1 | 12 | 40 |
| k2 | 14 | 45 |
| k3 | 12 | 31 |
| k4 | 17 | 38 |

### 当前配置参数
- UPSTREAM_TIMEOUT=66
- TIER_TIMEOUT_BUDGET_S=114
- NVU_PEXEC_TIMEOUT_FASTBREAK=1
- NVU_EMPTY_200_FASTBREAK=3
- FALLBACK_HEALTH_THRESHOLD=0.10
- NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
- KEY_COOLDOWN_S=25
- TIER_COOLDOWN_S=25
- NVU_CONNECT_RESERVE_S=0

## 诊断决策: NOP (零参数变更)

### 健康状态评估
1. **6h SR 90.3%**, post-restart SR **96.0%**, last 5h **100%** → 系统已进入健康regime
2. **FALLBACK_GRAPH 完整**: 双向 `dsv4p_nv↔glm5_2_nv`, dynamic fallback active
3. **Both NVCF functions health=1.0** per docker logs
4. **NVCFPexecTimeout max**: dsv4p_nv=60,823ms, glm5_2_nv=62,389ms — **both non-binding** (<< UPSTREAM=66)

### 为何NOP而非UPSTREAM下调
- dsv4p_nv NVCFPexecTimeout max=60,823ms, UPSTREAM=66 → gap=5.2s
- **R751规则**: 下调后buffer必须≥3s (60,823ms可漂移至下一轮)
- UPSTREAM 66→63: buffer=63,000-60,823=2,177ms — **<3s, 违反安全规则**
- UPSTREAM 66→64: buffer=3.2s — 勉强合规, 但glm5_2 max=62,389ms → 64,000-62,389=1,611ms <3s
- 结论: UPSTREAM reduction对dsv4p勉强可行但对glm5_2危险。跨tier共享UPSTREAM不可拆分。

### 为何NOP而非FASTBREAK调整
- FASTBREAK=1: 每tier 1 key × UPSTREAM=66s → 48s BUDGET headroom for fallback → 最优化配置
- 429分布中等非均匀, 但所有key都有429 → 非key-specific瓶颈
- FASTBREAK=2: 2×66=132 > BUDGET=114 → BUDGET先于fallback杀掉 (R768签名)
- 11 post-restart ATE的max_dur=228s≈2×BUDGET已证明BUDGET是绑定约束, 非FASTBREAK可解决

### 11 post-restart ATE根因
- All `tiers_tried_count=2`, `fallback_actually_attempted=false`
- max_dur=228,635ms ≈ 2×BUDGET(114s) — BUDGET在每tier耗尽后kill, fallback从未触发
- 两tier各自耗尽整个BUDGET → NVCF upstream双tier同时不可用
- **非config-fixable**: NVCF upstream同时不可用是上游问题, 非参数可调

### 零变更理由总结
- 系统当前100% SR (5h+) — 最优状态
- 11 ATE为NVCF upstream双tier耗尽 — 非配置参数可救
- UPSTREAM下调buffer<3s违反R751安全规则
- FASTBREAK=1+BUDGET=114是最优配置 (单key 66s, 48s fallback headroom)
- FALLBACK_GRAPH active + health=1.0 + FASTBREAK=1 → optimal config for this regime

## 执行
无配置变更。系统运行在最优参数下(SR 100%), ATE根因为NVCF upstream不可用。

**下一轮建议**: 若NVCF维持健康 → 继续观察; 若ATE回归且NVCFPexecTimeout max漂移超过3s → 考虑UPSTREAM+2s; 若429 surge导致单tier ATE → 考虑FASTBREAK增加但须验证BUDGET headroom。继续等待NVCF upstream恢复。

**单参数少改多轮。铁律：只改HM1不改HM2。**

## ⏳ 轮到HM1优化HM2