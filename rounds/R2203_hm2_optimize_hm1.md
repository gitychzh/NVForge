# R2203 (HM2→HM1): KEY_COOLDOWN_S 10→8 (-2s)

## Pre-Change Analysis (6h window)

```
32 req, 22 OK (68.8% SR), 10 zombie, 0 ATE
```

| Model | Req | OK | Fail | Avg ms | Key Cycling |
|-------|-----|----|------|--------|-------------|
| glm5_2_nv | 28 | 19 | 9 | 17745 | 100% (28/28) |
| dsv4p_nv | 4 | 3 | 1 | 22823 | 0% |

**Error breakdown**: 10 zombie_empty_completion (NVCF upstream, not config-fixable)

**Key cycling**: 100% of glm5_2_nv requests have key_cycle_429s≥1. R2201 TIER=3 reduced the excessive K3/K4 cycling from R2199 TIER=1, but KEY=10 still leaves keys stuck in cooldown too long.

**Budget check**: KEY+TIER+GLM5_2 = 8+3+28 = 39 << 153 (114s margin)

## Change

- **KEY_COOLDOWN_S**: 10 → 8 (-2s)
- Alternating pattern: R2200 KEY, R2201 TIER, R2202 KEY (this round)
- Line 500 in docker-compose.yml (nv_gw section)

```bash
# Before:
      KEY_COOLDOWN_S: "10"  # R2200 (HM2->HM1): ...

# After:
      KEY_COOLDOWN_S: "8"  # R2203 (HM2->HM1): KEY 10->8 (-2s). ...
```

## Post-Change Verification

- `docker compose stop nv_gw && docker compose up -d nv_gw` — container restarted cleanly
- `docker exec nv_gw env | grep KEY_COOLDOWN_S` → `KEY_COOLDOWN_S=8` ✓
- `docker exec nv_gw env | grep TIER_COOLDOWN_S` → `TIER_COOLDOWN_S=3` ✓
- `curl http://localhost:40006/health` → `{"status": "ok"}` ✓
- Only HM1 modified (iron law ✓)

## Post-Change Expectations

- Reduced key cycling (faster key recovery from 429 → less fallback to slow K3/K4)
- OK avg duration should decrease
- Zombie rate unchanged (NVCF upstream behavior)
- SR should remain stable or improve slightly

## ⏳ 轮到HM1优化HM2