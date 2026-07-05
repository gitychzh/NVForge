# R740: HM2→HM1 — UPSTREAM_TIMEOUT 58→60 (+2s)

## 6h Data
- 319 req / 217 OK (68.0%) / 102 ATE (32.0%)
- **dsv4p_nv**: 231 req, 134 OK (58.0% SR), 97 ATE. NVCFPexecTimeout max=54,284ms (function-level, 3.7s below UPSTREAM=58)
- **glm5_2_nv**: 88 req, 83 OK (94.3% SR), 5 ATE. NVCFPexecTimeout max=57,797ms (AT UPSTREAM=58 binding edge)
- 82 double-tier ATEs (80%), 19 single-tier ATEs (all pre-restart, fallback_actually_attempted=f)
- glm5_2 func 3b9748d8 health=0.0 (dead); FALLBACK_GRAPH bidirectional working
- dsv4p_nv success buckets: 53 ≤30s, 6 in 30-35s, 9 in 35-40s, 16 in 40-45s, 13 in 45-50s, 4 in 50-55s, 6 in 55-58s, 1 in 58-60s, 26 >60s

## Decision
UPSTREAM_TIMEOUT 58→60 (+2s). glm5_2_nv NVCFPexecTimeout max=57,797ms at UPSTREAM=58 binding edge. dsv4p_nv is function-level (~54s) and unaffected. 1 success in 58-60s bucket — direct capture. BUDGET=114 >> 60s per-tier safe. FASTBREAK=1 unchanged.

## Config
- UPSTREAM_TIMEOUT: 58 → 60
- BUDGET: 114 (unchanged)
- FASTBREAK: 1 (unchanged)
- FALLBACK_HEALTH_THRESHOLD: 0.10 (unchanged)

## NVCF Health
- dsv4p_nv 74f02205: 0.5-0.75 (declining)
- glm5_2_nv 3b9748d8: 0.0 (dead function, auto-switch working)

## ⏳ 轮到HM1优化HM2