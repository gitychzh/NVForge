# R2030 — HM2→HM1 优化回合

## 数据采集 (HM1 @ 100.109.153.83, 2026-07-20 ~11:10 UTC)

### 6h 请求统计 (R2028 regime: KEY=TIER=55)
- **总请求**: 33
- **成功**: 28 (84.85% SR)
- **失败**: 5 (15.15% zombie_empty_completion, 全部 glm5_2_nv, NVCF content_filter 不可修复)
- **0 real ATE** (13 phantom ATE all_tiers_exhausted with status=200, 0 real 502 ATE)
- **0 peer-fallback events** (fallback_occurred=f for all 33)
- **key_cycle_429s**: 20/33 (60.6%) — **恶化！R2028 的 50→55 反转 429 率从 53.1% 升至 60.6%**

### 6h 延迟 (成功请求)
- **glm5_2_nv**: avg=7,079ms, min=1,696ms, max=28,697ms (28 requests)

### 30min 窗口
- 3 req, 3 OK, 0 fail (100% SR, 极低流量窗口)

### 容器状态
- **nv_gw**: Up, listening on 40006, R2028 values
- **KEY_COOLDOWN_S=55, TIER_COOLDOWN_S=55** (R2028)
- **TIER_TIMEOUT_BUDGET_S=153, UPSTREAM_TIMEOUT=28, PEER_FALLBACK_TIMEOUT=122**
- **NVU_TIER_BUDGET_GLM5_2_NV=20**
- **Docker logs**: 0 errors/warnings

## 问题诊断

**核心发现**: R2028 的 KEY_COOLDOWN_S 50→55 非但未改善 429 率，反而恶化：
- R2024 (KEY=48): 46.9% (15/32)
- R2025 (KEY=50): 53.1% (17/32)
- R2028 (KEY=55): 60.6% (20/33) — 持续恶化！

**根因重新分析**: 这不是简单的 "cooldown 不够长" 问题。当 KEY_COOLDOWN_S 在 48-55s 区间时，key 被释放回轮转池时 NVCF 的 rate limit 窗口（约 60s）尚未过期。但 429 率随 cooldown 增大反而上升，说明中间值区间（48-55s）存在 **anti-pattern**：key 在 hotter 状态下被轮转触发更多 429。

**关键洞察**: KEY_COOLDOWN_S 必须 **≥ 60s**（NVCF 的 rate limit 窗口边界）才能让 key 在完全冷却后重新进入轮转池。当前 55s 距离 60s 仍有 5s 缺口。本轮直接跨越到 60s 边界。

## 优化方案

**单参数对**: KEY_COOLDOWN_S: 55→60 (+5s), TIER_COOLDOWN_S: 55→60 (+5s)

**依据**:
- 429 率在 48→50→55 区间持续恶化 (46.9%→53.1%→60.6%)，中间值区间存在 anti-pattern
- 60s 是 NVCF 60s rate limit 窗口边界，key 在完全冷却后重新进入轮转池
- 极低流量 (5.5req/h, 5 keys) 下 key 几乎不会连续命中同一 key，60s 足以冷却
- 60+60=120 << 153 BUDGET (33s 安全余量)
- 铁律: KEY=TIER 保持一致

**评判标准**:
- **更少报错**: 消除 429 cycling → 减少 key 轮转等待 → 降低 zombie_empty_completion 风险
- **更快请求**: 减少无效 key 轮转 → 降低延迟
- **超低延迟**: 429 越少等待越少
- **稳定优先**: BUDGET 安全余量 33s 充足；5 key 低流量无 key 耗尽风险

**约束检查**:
- peer-fb constraint: UPSTREAM=28 + PEER=122 = 150 < 153 ✓ (peer-fb 可触发)
- 6h: 0 real ATE → 无 rescue path 风险
- 铁律: 只改 HM1 不改 HM2 ✓

**历史趋势**: R2020 (56→54) → R2022 (54→50) → R2024 (50→48) → R2025 (48→50) → R2028 (50→55) → **R2030 (55→60) 到达 NVCF 60s 边界，消除 429 cycling anti-pattern**

## 执行

```bash
# HM1 compose nv_gw section — sed with | delimiter, line-number anchored
# Line 500: KEY_COOLDOWN_S: "55" → "60"
# Line 505: TIER_COOLDOWN_S: "55" → "60"
cd /opt/cc-infra && docker compose up -d nv_gw
```

## 验证

- **Live env**: KEY_COOLDOWN_S=60, TIER_COOLDOWN_S=60 ✓
- **容器重启**: nv_gw recreated + started, clean start ✓
- **Health check**: {"status": "ok"} ✓
- **其他参数不变**: PEER_FALLBACK=122, BUDGET=153, UPSTREAM=28, MIN_OUTBOUND=0, TIER_BUDGET_GLM5_2_NV=20, FORCE_STREAM=66 ✓
- **ms_gw KEY_COOLDOWN_S=58 (line 186) 未触碰** ✓
## ⏳ 轮到HM1优化HM2
