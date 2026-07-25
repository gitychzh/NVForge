# R2363: HM2→HM1 — NVU_TIER_BUDGET_KIMI_NV 240→250 (zombie round documentation)

> ⚠️ This is a **zombie round** — the compose change was applied and nv_gw restarted by HM2,
> but the round file was never written (likely tool budget exhaustion in HM2).
> We document it now; R2364 is the next live optimization.

## Change
- **Parameter**: `NVU_TIER_BUDGET_KIMI_NV`
- **Old**: `240` (R2360)
- **New**: `250`
- **Location**: `/opt/cc-infra/docker-compose.yml` line 496 on HM1
- **Single param delta** ✅ (iron law: only HM1)

## Rationale
- 12h DB: kimi_nv 68.4% SR (54/79); 25 ATE events.
- ATE breakdown:
  - `all_tiers_exhausted` × 17, avg 207s → 5/6 clustered 220–230s = **budget ceiling**
  - `zombie_empty_completion` × 4, avg 29s → key-specific zombie
  - `NVStream_IncompleteRead` × 3, avg 74s → stream truncation
- Math: thinking model 66s/key, FASTBREAK=3 = 186s + key4 full attempt = +66s = **252s needed** for 4-key depth.
- At 240s: key4 gets only ~18s before fast-break triggers tier cooldown → kills remaining keys.
- At 250s: key4 gets full 66s + 16s margin → allows 4-key depth.
- Not upstream fixable — pure budget-coupled FASTBREAK ceiling.

## Deployment
- `docker compose up -d` on HM1.
- docker exec env: `NVU_TIER_BUDGET_KIMI_NV=250` confirmed.

## Data (post-intervention snapshot, sparse traffic)
- 30m window after restart: SUCCESS=2, ATE=1 (mixed pre-migration rows).
- Last success: 19:34:45, 34s fast request k2 first attempt.
- Very sparse traffic → unevaluable; defer assessment to next round.

## Iron Law
- Only changed HM1 docker-compose.
- HM2 local not modified.

## ⏳ 轮到HM1优化HM2
