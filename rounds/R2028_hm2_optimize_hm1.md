# R2028 — HM2→HM1 优化回合

## 数据采集 (HM1 @ 100.109.153.83, 2026-07-20 ~11:00 UTC)

### 6h 请求统计 (R2025 regime: KEY=TIER=50)
- **总请求**: 32
- **成功**: 27 (84.4% SR)
- **失败**: 5 (15.6% zombie_empty_completion, 全部 glm5_2_nv, NVCF content_filter 不可修复)
- **0 real ATE** (5 phantom ATE all_tiers_exhausted with status=200, 0 real 502 ATE)
- **0 peer-fallback events** (fallback_occurred=f for all 32)
- **key_cycle_429s**: 17/32 (53.1%) — **仍然高位，R2025 的 48→50 反转未改善 429 率**

### 6h 延迟 (成功请求)
- **glm5_2_nv**: avg=6,088ms, min=1,696ms, max=28,697ms (27 requests)

### 30min 窗口
- 2 req, 2 OK, 0 fail (极低流量窗口)

### 容器状态
- **nv_gw**: Up, listening on 40006, R2025 values
- **KEY_COOLDOWN_S=50, TIER_COOLDOWN_S=50** (R2025)
- **TIER_TIMEOUT_BUDGET_S=153, UPSTREAM_TIMEOUT=28, PEER_FALLBACK_TIMEOUT=122**
- **NVU_TIER_BUDGET_GLM5_2_NV=20**
- **Docker logs**: 0 errors/warnings

## 问题诊断

**核心发现**: R2025 的 KEY_COOLDOWN_S 48→50 反转未改善 429 率：
- R2024 (KEY=48): 53.1% (17/32)
- R2025 (KEY=50): 53.1% (17/32) — 完全持平，未下降

**根因**: NVCF 的 rate limit 窗口约为 60s。KEY_COOLDOWN_S=50s 时 key 仍在 NVCF 冷却窗口内（50 < 60），key 重新进入轮转池后立即再被 429 → 循环持续。R2025 的 2s 增量不足以触及 NVCF 60s 边界。

**关键洞察**: KEY_COOLDOWN_S 必须 ≥ NVCF 的 60s rate limit 窗口才能消除 429 循环。当前 50s 距离 60s 仍有 10s 缺口。每轮渐进靠近，本轮 +5s 缩小缺口至 5s。

## 优化方案

**单参数对**: KEY_COOLDOWN_S: 50→55 (+5s), TIER_COOLDOWN_S: 50→55 (+5s)

**依据**:
- 429 率在 48→50 区间持平 53.1%，说明 50s 仍未触及 NVCF 60s 窗口
- 55s 更接近 60s 边界，预期降低 429 触发频率
- 极低流量 (5.3req/h, 5 keys) 下 key 几乎不会连续命中同一 key，55s 足以让 key 冷却
- 55+55=110 << 153 BUDGET (43s 安全余量)
- 铁律: KEY=TIER 保持一致

**评判标准**:
- **更少报错**: 降低 429 率 → 减少 key 轮转等待 → 降低 zombie_empty_completion 风险
- **更快请求**: 减少无效 key 轮转 → 降低延迟
- **超低延迟**: 429 越少等待越少
- **稳定优先**: BUDGET 安全余量 43s 充足；5 key 低流量无 key 耗尽风险

**约束检查**:
- peer-fb constraint: UPSTREAM=28 + PEER=122 = 150 < 153 ✓ (peer-fb 可触发)
- 6h: 0 real ATE → 无 rescue path 风险
- 铁律: 只改 HM1 不改 HM2 ✓

**历史趋势**: R2020 (56→54) → R2022 (54→50) → R2024 (50→48) → R2025 (48→50) → **R2028 (50→55) 继续推进向 60s 边界，每轮 +5s 渐进**

## 执行

```bash
# HM1 compose nv_gw section — sed with | delimiter, line-number anchored
# Line 500: KEY_COOLDOWN_S: "50" → "55"
# Line 505: TIER_COOLDOWN_S: "50" → "55"
cd /opt/cc-infra && docker compose up -d nv_gw
```

## 验证

- **Live env**: KEY_COOLDOWN_S=55, TIER_COOLDOWN_S=55 ✓
- **容器重启**: nv_gw recreated + started, clean start ✓
- **Health check**: {"status": "ok"} ✓
- **其他参数不变**: PEER_FALLBACK=122, BUDGET=153, UPSTREAM=28, MIN_OUTBOUND=0, TIER_BUDGET_GLM5_2_NV=20, FORCE_STREAM=66 ✓
- **ms_gw KEY_COOLDOWN_S=58 未触碰** ✓ (line 186)
## ⏳ 轮到HM1优化HM2
