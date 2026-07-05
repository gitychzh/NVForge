# R754: HM2→HM1 — UPSTREAM_TIMEOUT 64→66 (+2s)

## 变更
**参数**: `UPSTREAM_TIMEOUT` 64 → 66 (+2s)

**类型**: Safety buffer restoration (preventative, per R751 pitfall rule)

## 数据依据
- **6h**: 346req/248OK (71.7%) / 98 ATE (28.3%)
- **dsv4p_nv**: 263req/174OK (66.2%), NVCFPexecTimeout max=60,823ms (k0) at UPSTREAM=64 — buffer=3.2s (adequate)
- **glm5_2_nv**: 81req/73OK (90.1%), NVCFPexecTimeout max=62,389ms (k1) at UPSTREAM=64 — buffer=1.6s **<3s minimum**
- **kimi_nv**: 2req/1OK (50.0%), negligible
- **glm5_2 func 3b9748d8**: health fluctuating 0.0-0.5 (recovering post-restart)
- **dsv4p_nv func 74f02205**: health=1.0 (healthy)
- **FALLBACK_GRAPH**: bidirectional working — logs show tier_chain=['dsv4p_nv', 'glm5_2_nv'] and ['glm5_2_nv', 'dsv4p_nv'] with dynamic fallback
- 23 single-tier ATE (all fallback_actually_attempted=f, glm5_2 health=0.0 during some periods), 75 double-tier (NVCF dual-function exhaustion)
- glm5_2_nv: 10 empty_200 fallback events, 68 NVCFPexecTimeout failures — key1 max=62,389ms worst
- dsv4p_nv success latency percentiles: P25=23.7s, P50=44.9s, P75=61.3s, P90=91.6s, P95=104.4s, P99=120.0s
- Container restarted at 13:41 UTC (~8h ago), MIN_SAMPLES protection expired
- Hourly SR trend: improving from 46.2% (10:00) → 93.8% (21:00) — system recovering

## 安全分析
- **R751 pitfall rule**: post-reduction buffer (UPSTREAM - NVCFPexecTimeout_max) must be ≥3s
- **glm5_2_nv** buffer: 64,000 - 62,389 = 1,611ms (1.6s) — **violates 3s minimum** (this is the trigger)
- **dsv4p_nv** buffer: 64,000 - 60,823 = 3,177ms (3.2s) — meets 3s minimum
- +2s to 66 creates: 66,000 - 62,389 = 3,611ms (3.6s) buffer for glm5_2_nv — **meets 3s minimum**
- +2s to 66 creates: 66,000 - 60,823 = 5,177ms (5.2s) buffer for dsv4p_nv — safer
- BUDGET=114 >> 66s per-tier safe
- FASTBREAK=1 unchanged — 1 key × 66s = 66s << 114s budget
- Fallback rescue: glm5_2_nv 90.1% SR (healthy fallback), bidirectional working
- No risk of false-abort: max success duration via fallback = 203s (extreme outlier), 96 fallback successes avg=69s
- 6 successes in 60-70s bucket (via fallback) — +2s captures 64-66s range directly, reduces fallback load

## 容器状态
- Container: `nv_gw` (R680 rename), started 2026-07-05 13:41 UTC (pre-R754 restart)
- **R754 restart**: `Recreated` + `Started`, health check passing

## 验证
- YAML: OK ✓
- Container recreated + started ✓
- Health: OK ✓
- `UPSTREAM_TIMEOUT=66` ✓
- `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=62` (unchanged) ✓
- `FALLBACK_HEALTH_THRESHOLD=0.10` ✓
- `NVU_PEXEC_TIMEOUT_FASTBREAK=1` ✓
- `TIER_TIMEOUT_BUDGET_S=114` ✓

## 下一轮提示
- glm5_2 func 3b9748d8 health recovering (0.0→0.333→0.5) — positive trend, wait for stability
- dsv4p_nv NVCFPexecTimeout max=60,823ms at UPSTREAM=66 — 5.2s buffer now, safe
- glm5_2_nv NVCFPexecTimeout max=62,389ms at UPSTREAM=66 — 3.6s buffer now, meets 3s minimum
- NVU_FORCE_STREAM_UPGRADE_TIMEOUT=62 still drifted from UPSTREAM=66 — next round candidate
- 75 double-tier ATEs = NVCF dual-function exhaustion, not config-fixable
- Peer fallback to HM2 won't rescue local ATEs (R744 code-level defect) — zero-change correct response

## ⏳ 轮到HM1优化HM2