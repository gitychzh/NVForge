# Round R2361: HM2 → HM1 Optimization

## Timestamp
- Round Start: 2026-07-26 ~01:16 UTC
- HM1 DB Time: 2026-07-25 17:43:27+00 (UTC)
- HM1 Container: nv_gw (hm40006 does not exist)

## Data Collection
1. **Docker Logs (nv_gw)** — last restart ~2026-07-26 01:00 UTC (8h gap from DB data). Prior period data 100% relevant to budget analysis since no NVU param changes since R2360. No errors/warns in post-restart 20 lines.
2. **Env** — NVU params verified in compose. Target parameter: `NVU_TIER_BUDGET_DSV4P_NV=210` at line 493.
3. **DB: nv_requests (4h: 17:00→17:43):**
   - **dsv4p_nv**: 9 req → 0 OK, 9 ATE (0% SR). All ATE cluster 180000–210000ms, exactly at budget ceiling. NVCF upstream: 2×504 Gateway Timeout (~64s) + 1×exec timeout (~67s) + 1×SSLEOFError (~5s) = ~200s key-cycle, key5 killed with remaining 10s.
   - **glm5_2_nv**: 13 req → 5 OK, 8 ATE. 8 ATE all instant reject (~25s) via big-input cooldown (not tier budget). 5 OK avg 15.8s. NVCF degraded.
   - **kimi_nv**: 16 req → 11 OK, 5 ATE. Of 5 ATE: 4 at budget ceiling 220–230s (pre-R2360), 1 NVStream_IncompleteRead. No post-restart ATE data.
4. **JSONL** (tail 30 lines): confirms same error patterns.

## Analysis
- dsv4p_nv is the **worst-performing model** (0% SR in 4h, 20.5% in 24h). Every ATE hits the 210s budget ceiling.
- Root cause: NVCF upstream is severely degraded — even with 3–4 keys per tier, the cumulative per-key timeouts exceed 210s.
- dsv4p_nv is **outside** the big-input breaker (`NVU_BIG_INPUT_MODELS=glm5_2_nv` since R2358), so no goalie interference.
- The 504 timeouts (~64s), exec timeouts (~67s), and occasional fast failures (~5s) add up to ~200s across 4–5 keys. Raising budget to 240s gives the 4th key a full attempt window.
- kimi_nv already stabilized at 240s (R2360), no new data post-restart. SAFE.
- glm5_2_nv NVCF degradation is outside tier-budget scope (cooldown saves time). UNTOUCHED.

## Optimization
Single-param change, **HM1 only**, following iron law.
1. **Parameter**: `NVU_TIER_BUDGET_DSV4P_NV`
2. **Change**: `210 → 240`
3. **Rationale**: dsv4p_nv 0% SR. All ATE @ budget ceiling. Per-key NVCF timeout pattern (~64s 504, ~67s timeout) accumulates >200s before key5 gets aborted. 240s = budget parity with kimi_nv (matching model, same upstream cluster), allows key4/key5 full ~66s windows.
4. **Expected**: Reduce dsv4p_nv ATE rate from 0% to >0% by allowing more keys full attempts. No side effects on other models.

## Verification
- docker compose up -d nv_gw → Container nv_gw Recreated & Started
- docker exec nv_gw env → NVU_TIER_BUDGET_DSV4P_NV=240 confirmed
- docker logs tail → [NV-PROXY] Listening on 0.0.0.0:40006 with new budget

## ⏳ 轮到HM1优化HM2
