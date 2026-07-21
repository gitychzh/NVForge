# R2204 (HM2→HM1): TIER_COOLDOWN_S 3→1 (-2s)

## Pre-Change Analysis (6h window)

```
32 req, 22 OK (68.8% SR), 10 zombie, 0 ATE
```

| Model | Req | OK | Fail | Avg ms | Key Cycling |
|-------|-----|----|------|--------|-------------|
| glm5_2_nv | 28 | 19 | 9 | 17745 | 100% (28/28) |
| dsv4p_nv | 4 | 3 | 1 | 22823 | 0% |

**Error breakdown**: 10 zombie_empty_completion (NVCF upstream, not config-fixable)

**Key cycling**: 87.5% of all requests (28/32) have key_cycle_429s≥1. R2203 reduced KEY 10→8, continuing the alternating KEY→TIER reduction pattern.

**Budget check**: KEY(8) + TIER(1) + GLM5_2(28) = 37 << 153 (116s margin)

**Docker logs**: Clean, no errors/warnings. Container started normally.

## Change

- **TIER_COOLDOWN_S**: 3 → 1 (-2s)
- Alternating pattern: R2203 KEY, R2204 TIER (this round)
- Line 507 in docker-compose.yml (nv_gw section)

```bash
# Before:
      TIER_COOLDOWN_S: "3"  # R2201 (HM2->HM1)...

# After:
      TIER_COOLDOWN_S: "1"  # R2204 (HM2->HM1): TIER 3->1 (-2s). Alternating TIER->KEY. 6h: 32req/22OK(68.8%SR)/10zombie/0ATE. OK avg 18380ms. KEY+TIER+GLM5_2=8+1+28=37<<153 BUDGET(116s). Single param; iron law: only HM1.
```

## Post-Change Verification

- `docker compose stop nv_gw && docker compose up -d nv_gw` — container restarted cleanly
- `docker exec nv_gw env | grep KEY_COOLDOWN_S` → `KEY_COOLDOWN_S=8` ✓
- `docker exec nv_gw env | grep TIER_COOLDOWN_S` → `TIER_COOLDOWN_S=1` ✓
- `curl http://localhost:40006/health` → `{"status": "ok"}` ✓
- docker logs clean (no errors) ✓
- Only HM1 modified (iron law ✓)

## Post-Change Expectations

- Slightly faster tier restart (shorter cooldown between key rotation cycles)
- 0 ATE regime continues (already 0 ATE pre-change)
- Zombie rate unchanged (NVCF upstream behavior, not config-fixable)
- Budget: 37/153 — extremely safe, 116s margin
- SR should remain stable

## ⏳ 轮到HM1优化HM2