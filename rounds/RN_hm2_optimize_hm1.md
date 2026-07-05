# R753: HM2→HM1 — UPSTREAM_TIMEOUT 62→64 (+2s)

## 变更
**参数**: `UPSTREAM_TIMEOUT` 62 → 64 (+2s)

**类型**: Safety buffer restoration (preventative, per R751 pitfall rule)

## 数据依据
- **6h**: 341req/240OK (70.4%) / 101 ATE (29.6%)
- **dsv4p_nv**: 227req/135OK (59.5%), NVCFPexecTimeout max=60,823ms (k0) at UPSTREAM=62 binding
- **glm5_2_nv**: 112req/104OK (92.9%), NVCFPexecTimeout max=62,251ms (k4) — healthy fallback
- **kimi_nv**: 2req/1OK (50.0%), negligible
- **glm5_2 func 3b9748d8**: health=0.0 (dead), but in tier_chain via MIN_SAMPLES protection
- **FALLBACK_GRAPH**: bidirectional working — logs show tier_chain=['dsv4p_nv', 'glm5_2_nv'] and ['glm5_2_nv', 'dsv4p_nv'] with dynamic fallback
- 22 single-tier ATE (dsv4p_nv exhausted, all pre-restart), 70 double-tier (dsv4p_nv→glm5_2), 8 double-tier (glm5_2→dsv4p_nv)
- **ALL 101 ATEs are pre-restart** (container restarted at 21:20 UTC, 6 min ago)
- Success 60-62s bucket: 1 request (via fallback); 62-64s: 1 request (via fallback) — minimal edge rescue
- NVCFPexecTimeout dsv4p_nv: 36 failures, 5-key uniform distribution (6/7/12/6/5), max=60,823ms

## 安全分析
- **R751 pitfall rule**: post-reduction buffer (UPSTREAM - NVCFPexecTimeout_max) must be ≥3s
- Current buffer: 62,000 - 60,823 = 1,177ms (1.2s) — **violates 3s minimum**
- Between R750→R751, NVCFPexecTimeout max drifted +1.2s (59,596→60,823ms)
- +2s to 64 creates buffer: 64,000 - 60,823 = 3,177ms (3.2s) — **meets 3s minimum**
- BUDGET=114 >> 64s per-tier safe
- FASTBREAK=1 unchanged — 1 key × 64s = 64s << 114s budget
- Fallback rescue: glm5_2_nv 92.9% SR (healthy), 64s key1 + 64s fallback = 128s > 114s BUDGET per-tier (but per-tier budget resets for fallback per R707)
- No risk of false-abort: max success duration via fallback = 203s (extreme outlier), typical fallback success avg = 68s

## 容器状态
- Container: `nv_gw` (R680 rename), started 2026-07-05 21:20 UTC (pre-R753 restart)
- **R753 restart**: `Recreated` + `Started`, health check passing

## 验证
- YAML: OK ✓
- Container recreated + started ✓
- Health: OK ✓
- `UPSTREAM_TIMEOUT=64` ✓
- `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=62` (unchanged) ✓
- `FALLBACK_HEALTH_THRESHOLD=0.10` ✓
- `NVU_PEXEC_TIMEOUT_FASTBREAK=1` ✓
- `TIER_TIMEOUT_BUDGET_S=114` ✓

## 下一轮提示
- glm5_2 func 3b9748d8 health=0.0 dead — MIN_SAMPLES will expire, removing glm5_2 from tier_chain → single-tier ATE may increase
- dsv4p_nv NVCFPexecTimeout max=60,823ms at UPSTREAM=64 — 3.2s buffer now, monitor drift
- NVU_FORCE_STREAM_UPGRADE_TIMEOUT=62 drifted from UPSTREAM=64 — next round candidate (drift correction)
- Peer fallback to HM2 won't rescue local ATEs (R744 code-level defect) — zero-change correct response

## ⏳ 轮到HM1优化HM2