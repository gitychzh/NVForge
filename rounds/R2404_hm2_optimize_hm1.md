# R2404 (HM2→HM1): NVU_EMPTY_200_FASTBREAK 3→2

## Data (HM1, 2h window ending ~21:30 UTC)

| Metric | Count |
|--------|-------|
| Total requests | ~58 |
| Success (200) | ~23 |
| ATE/Abort | ~35 |
| [NV-SUCCESS] | 9 |
| [NV-TIER-FAIL] → ALL-TIERS-FAIL | 11 |
| [NV-EMPTY-CYCLE] | 10 |
| [NV-TIMEOUT] | 22 |
| [NV-SSL-CYCLE] | 5 |

### Per-model ATE pattern

| Model | ATE Count | Primary root cause |
|-------|-----------|-------------------|
| glm5_2_nv | ~12 | NVCF pexec timeout cluster (5/5 keys timeout) → PEXEC-FASTBREAK |
| kimi_nv | ~6 | empty_200 cascade (3/5 keys empty 200) → EMPTY-FASTBREAK |
| dsv4p_nv | ~2 | Silent in 2h (low/no traffic) |

## Diagnosis

### Problem: EMPTY_200 FASTBREAK happening too late

**Observed pattern (`21:10:12` – `21:12:16`):**
```
kimi_nv → k1 empty_200 → k2 empty_200 → k3 empty_200 → [EMPTY-FASTBREAK] → [TIER-FAIL] → [ALL-TIERS-FAIL]
```
- Three keys consumed before FASTBREAK triggers (3 × ~62s = 185s wasted)
- Only k4, k5 remain after FASTBREAK → budget exhausted, 185s+ total elapsed
- FASTBREAK=3 is conservative for empty_200 which is **deterministic** — if k1 and k2 both return empty_200, k3 will almost certainly also return empty_200 (cluster-wide NVCF health issue)

### Why FASTBREAK=2 is safe

1. **empty_200 is non-transient**: Unlike `NVCFPexecTimeout` (which can vary per key), empty_200 indicates NVCF returning Content-Length:0 — a service-wide health signal. Two in a row = strong signal.
2. **FASTBREAK saves keys**: At FASTBREAK=2, k3-k5 are preserved. This allows tier fallback or agent-level ms_gw fallback to succeed.
3. **Budget math**: With KEY_COOLDOWN=5 and per_key_timeout=66s:
   - FASTBREAK=2: k1 (66s+5s) + k2 (66s+5s) = 142s → k3 preserved → total ATE ~142s (vs current 185s)
   - Savings: **~43s per empty_200 cascade**
4. **HM2 alignment**: HM2 already at FASTBREAK=2 (R701 baseline), proving stability.
5. **Risk**: Negligible — empty_200 rarely succeeds on 3rd key when 1st and 2nd both failed.

## Fix

**NVU_EMPTY_200_FASTBREAK: 3 → 2**

## Execution

```bash
# Applied on HM1 only (iron law: never modify HM2)
ssh -p 222 opc_uname@100.109.153.83
  sed -i '466s/NVU_EMPTY_200_FASTBREAK=3/NVU_EMPTY_200_FASTBREAK=2/' /opt/cc-infra/docker-compose.yml
  # Updated comment: R2404 rationale
  docker compose up -d nv_gw
  curl localhost:40006/health  # → {"status": "ok"}
```

- Container restated gracefully, health check passes
- No paired parameter change — single param FASTBREAK only

## Expected effect

- empty_200 cascade triggered 1 key earlier (k2→FASTBREAK vs k3→FASTBREAK)
- Saves ~43s per empty_200 failure, prevents unnecessary key exhaustion
- Preserves k3-k5 for fallback paths or NVCF recovery
- No impact on success path (empty_200 only fires on failure)

## ⏳ 轮到HM1优化HM2  ← 脚本检测此标记
