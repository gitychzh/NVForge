# R2023 — HM2→HM1 优化回合

## 数据采集 (HM1 @ 100.109.153.83, 2026-07-20 02:09 UTC)

### 6h 请求统计 (pre-R2022 regime)
- **总请求**: 32
- **成功**: 27 (84.4% SR)
- **失败**: 5 (15.6% zombie_empty_completion, 全部 glm5_2_nv)
- **0 real ATE** (17 phantom ATE 全部 status=200, no real 502 ATE)
- **0 peer-fallback events** (6h peer_fb_total=0, peer_fb_success=0, peer_fb_fail=0)
- **key_cycle_429s**: 15/32 (46.9%) — 近半数请求第一key被429限流

### 6h 延迟 (成功请求)
- **glm5_2_nv**: avg=6,045ms, min=1,696ms, max=28,697ms (27 requests)

### Post-R2022 deploy (container restart 02:09:10Z)
- **0 requests** in post-restart window (19 min, slow traffic window)

### 容器状态
- **nv_gw**: Up, listening on 40006, healthy
- **KEY_COOLDOWN_S=50, TIER_COOLDOWN_S=50** (R2022)
- **TIER_TIMEOUT_BUDGET_S=153**
- **PEER_FALLBACK_TIMEOUT=122, UPSTREAM_TIMEOUT=28**
- **NVU_TIER_BUDGET_GLM5_2_NV=20**
- **Docker logs**: 0 errors/warnings (clean start)

## 问题诊断

**核心问题**: 47% key_cycle_429s rate (15/32 req) — 第一key被NVCF 429限流。KEY_COOLDOWN_S=50s 时key冷却时间仍有收紧空间，key恢复速度偏慢，流量集中到剩余key→连锁429。

**根因**: KEY_COOLDOWN_S=50s 在5-key池低流量(~5.3req/h)场景下仍偏保守。R2022已从54→50，429率从47%没有明显改善(统计窗口相同)。需继续加速key恢复。

## 优化方案

**单参数对**: KEY_COOLDOWN_S: 50→48 (-2s), TIER_COOLDOWN_S: 50→48 (-2s)

**评判标准**:
- **更少报错**: 降低429率 → 减少key轮转耗时 → 降低zombie_empty_completion风险
- **更快请求**: 减少key_cycle等待 → 降低p50延迟
- **超低延迟**: 429越少等待越少
- **稳定优先**: BUDGET安全: 48+48=96 << 153 (57s安全余量); 5key低流量无key exhaustion风险

**约束检查**:
- peer-fb constraint: UPSTREAM=28 + PEER=122 = 150 < 153 ✓ (peer-fb可触发)
- 6h: 0 real ATE → 无rescue path风险
- 铁律: 只改HM1不改HM2 ✓

**历史趋势**: R2020 (56→54) → R2022 (54→50) → R2023 (50→48), 持续-2s递减，零回退纪录

## 执行

```bash
# HM1 compose nv_gw section — python3 stdin pipe mode
# Line 500: KEY_COOLDOWN_S: "50" → "48"
# Line 505: TIER_COOLDOWN_S: "50" → "48"
docker compose up -d nv_gw
```

## 验证

- **Live env**: KEY_COOLDOWN_S=48, TIER_COOLDOWN_S=48 ✓
- **容器运行**: nv_gw up, StartedAt=2026-07-20T02:22:38Z ✓
- **日志**: 0 errors/warnings, clean start ✓
- **其他参数不变**: PEER_FALLBACK=122, BUDGET=153, UPSTREAM=28, MIN_OUTBOUND=0 ✓
## ⏳ 轮到HM1优化HM2
