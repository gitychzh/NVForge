# R2025 — HM2→HM1 优化回合

## 数据采集 (HM1 @ 100.109.153.83, 2026-07-20 10:40 UTC)

### 6h 请求统计 (R2024 regime: KEY=TIER=48)
- **总请求**: 32
- **成功**: 27 (84.4% SR)
- **失败**: 5 (15.6% zombie_empty_completion, 全部 glm5_2_nv, NVCF content_filter 不可修复)
- **0 real ATE** (15 phantom ATE 全部 status=200, no real 502 ATE)
- **0 peer-fallback events** (fallback_occurred=f for all 32)
- **key_cycle_429s**: 17/32 (53.1%) — **↑ 从 R2022 的 46.9% (KEY=50) 升至 53.1% (KEY=48)**

### 6h 延迟 (成功请求)
- **glm5_2_nv**: avg=6,315ms, min=1,696ms, max=28,697ms (27 requests)

### 30min 窗口
- 2 req, 2 OK, 0 fail / avg 9,626ms (low traffic window)

### 容器状态
- **nv_gw**: Up, listening on 40006, R2024 values
- **KEY_COOLDOWN_S=48, TIER_COOLDOWN_S=48** (R2024)
- **TIER_TIMEOUT_BUDGET_S=153, UPSTREAM_TIMEOUT=28, PEER_FALLBACK_TIMEOUT=122**
- **NVU_TIER_BUDGET_GLM5_2_NV=20**
- **Docker logs**: 0 errors/warnings

## 问题诊断

**核心发现**: KEY_COOLDOWN_S 缩减路径 (56→54→50→48) 导致 429 率反而上升：
- R2020 (KEY=56): 未记录 429 率
- R2022 (KEY=50): 46.9% (15/32)
- R2024 (KEY=48): 53.1% (17/32)

**根因**: NVCF 的 rate limit 窗口约为 60s。KEY_COOLDOWN_S=48s 时 key 在 NVCF 冷却窗口结束前就重新进入轮转池，发出请求后立即再被 429 → 触发新一轮 48s 冷却 → 循环扩大。KEY=50s 更接近 60s 边界，但仍有 gap。缩减方向错误，需反向调整。

**关键洞察**: 不是 "key 冷却越快越好" — 而是 "key 冷却必须 ≥ NVCF 的 rate limit 窗口"。在 48s 时 key 冷却不足，频繁触发 429 循环，反而增加了总 key 轮转延迟。

## 优化方案

**单参数对**: KEY_COOLDOWN_S: 48→50 (+2s), TIER_COOLDOWN_S: 48→50 (+2s)

**依据**:
- R2022 时 KEY=50 的 429 率为 46.9%，低于 R2024 的 53.1%
- 50s 虽仍略低于 NVCF ~60s 窗口，但差距更小，429 触发频率更低
- 在当前极低流量 (5.3req/h, 5 keys) 下，key 几乎不会连续命中同一 key，50s 足以让 key 基本冷却
- 50+50=100 << 153 BUDGET (53s 安全余量)
- 铁律: KEY=TIER 保持一致

**评判标准**:
- **更少报错**: 降低 429 率 → 减少 key 轮转等待 → 降低 zombie_empty_completion 风险
- **更快请求**: 减少无效 key 轮转 → 降低 p50 延迟
- **超低延迟**: 429 越少等待越少
- **稳定优先**: BUDGET 安全余量 53s 充足；5 key 低流量无 key 耗尽风险

**约束检查**:
- peer-fb constraint: UPSTREAM=28 + PEER=122 = 150 < 153 ✓ (peer-fb 可触发)
- 6h: 0 real ATE → 无 rescue path 风险
- 铁律: 只改 HM1 不改 HM2 ✓

**历史趋势**: R2020 (56→54) → R2022 (54→50) → R2024 (50→48) → **R2025 (48→50) 首次反向调整，基于数据证实 429 率恶化**

## 执行

```bash
# HM1 compose nv_gw section — sed with | delimiter
# Line 500: KEY_COOLDOWN_S: "48" → "50"
# Line 505: TIER_COOLDOWN_S: "48" → "50"
cd /opt/cc-infra && docker compose up -d nv_gw
```

## 验证

- **Live env**: KEY_COOLDOWN_S=50, TIER_COOLDOWN_S=50 ✓
- **容器重启**: nv_gw recreated + started, clean start ✓
- **日志**: 0 errors/warnings, [NV-PROXY] Listening on 0.0.0.0:40006 ✓
- **其他参数不变**: PEER_FALLBACK=122, BUDGET=153, UPSTREAM=28, MIN_OUTBOUND=0, TIER_BUDGET_GLM5_2_NV=20, FORCE_STREAM=66 ✓
- **ms_gw KEY_COOLDOWN_S=58 未触碰** ✓ (line 186)
## ⏳ 轮到HM1优化HM2
