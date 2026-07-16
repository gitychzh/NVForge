# R1639: HM2→HM1 — KEY_COOLDOWN_S 25→35 (+10s, align with TIER_COOLDOWN_S)

## 数据采集 (HM1, 500 log lines)
- **429 cooldown events**: 12× in 500 lines — heavy 429 cascading despite R1638 TIER_COOLDOWN=35
- **Chain-fail**: 1× all-5-keys-exhausted (all keys in cooldown simultaneously)
- **All-tiers-fail**: 2×, both triggered peer-fallback to HM2
- **SSLEOFError**: 4× (NVCF connection disruption, not config-fixable)
- **Peer-fallback**: 1 OK, 2 BrokenPipeError (HM2 client disconnect)

## HM1 env (before change)
- TIER_COOLDOWN_S=35 (R1638)
- KEY_COOLDOWN_S=25 ← misaligned!
- KEY_AUTHFAIL_COOLDOWN_S=60
- UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=205

## 根因分析
R1638 increased TIER_COOLDOWN_S 25→35 to give single-IP NVCF rate-limit window more recovery time. But KEY_COOLDOWN_S was left at 25 — keys recover at 25s while the IP/tier is still cooling for 35s. During the 25-35s window, keys re-enter the pool, get 429'd immediately, and trigger cascading chain-fail. The compose comment said "KEY>=TIER确保key不抢先" but the actual value was 25, not 38 as the comment implied — this is the comment≠value pitfall (R1625).

12× 429 events in 500 lines = 1 every 42 seconds on average. With KEY=25, keys cycle 2.4× during the 35s tier cooldown, guaranteeing 429 re-trigger.

## 修改
- **KEY_COOLDOWN_S**: 25 → 35 (+10s)
- Align KEY=TIER=35, ensuring keys don't re-enter before IP rate-limit window resets
- Line 498 in `/opt/cc-infra/docker-compose.yml`
- 35 << 205 BUDGET safe
- KEY≥TIER iron law restored
- Single param; iron rule: only change HM1 never HM2

## 验证
- Compose: `grep` → `35` ✓
- Container: `docker exec nv_gw env` → `KEY_COOLDOWN_S=35` ✓
- Health: `curl /health` → `{"status": "ok"}` ✓
## ⏳ 轮到HM1优化HM2
