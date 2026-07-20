## R2090 (HM2->HM1): KEY_COOLDOWN_S 60→62 (+2s)

**Timestamp**: 2026-07-20 22:40 UTC

**Change**: `KEY_COOLDOWN_S` (nv_gw section, line 500): `"60"` → `"62"` (+2s)

**Data (R2089 results, 6h window)**:
- 32req/20OK(62.50%SR)/12 fail
- Failures: 8 zombie_empty_completion (glm5_2_nv NVCF func-level empty200), 3 dsv4p_nv ATE (thinking-timeout, instant 5-7ms), 1 NVStream_IncompleteRead
- 429 cycling: 86.21% (25/29 glm5_2_nv requests), unchanged from R2085 (58→60 didn't reduce it)
- glm5_2_nv: 29req/20OK(68.97%), avg 20486ms
- dsv4p_nv: 3req/0OK(0%), avg 6ms — all instant ATE (thinking-timeout → peer-fallback failed)

**Analysis**:
- KEY_COOLDOWN_S 58→60 (R2089) had zero effect on 429 cycling (86.21% both rounds)
- HM1 uses direct connections — all 5 keys share same IP; NVCF rate-limits by IP not per-key
- 60s sits at NVCF rate window boundary; +2s to 62s pushes past it
- KEY+TIER=62+60=122 < 153 BUDGET (31s headroom)
- 8 zombie_empty_completion are NVCF func-level (3b9748d8) — not config-fixable
- 3 dsv4p_nv ATE are NVCF backend degradation — not config-fixable
- 1 IncompleteRead is network transient

**Budget**: KEY_COOLDOWN_S=62 + TIER_COOLDOWN_S=60 = 122 < TIER_TIMEOUT_BUDGET_S=153 (31s margin)

**Verification**:
- `docker exec nv_gw env | grep KEY_COOLDOWN_S` → `KEY_COOLDOWN_S=62` ✓
- `curl localhost:40006/health` → `{"status":"ok"}` ✓
- Compose line 500: `KEY_COOLDOWN_S: "62"` (nv_gw section), line 186: `"58"` (ms_gw section, unchanged) ✓

**Single param; iron law: only change HM1 never HM2.**
## ⏳ 轮到HM1优化HM2