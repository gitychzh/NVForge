# R1638: HM2→HM1 — TIER_COOLDOWN_S 25→35 (+10s, HM1 single-IP anti-429)

## 数据采集 (HM1, 2h window)
- **glm5_2_nv**: 117 OK (avg 24.5s), 103 fail (avg 11.5s) → **53.2% SR**
- **dsv4p_nv**: 0 OK, 8 fail (avg 63.8s) → 0% (function-level dead, NVCF 504)
- **Error breakdown**: 95 zombie_empty_completion (NVCF content-filter, not config-fixable), 10 all_tiers_exhausted (429 cascading)
- **Logs**: Heavy 429 cascading on glm5_2_nv — all 5 keys 429'd in rapid succession, chain-fail at 132s and 254s

## HM2对比 (2h window)
- **glm5_2_nv**: 91 OK, 40 fail → **69.5% SR** (much better)
- HM2 uses per-key SOCKS5 (different IPs) → NVCF sees different IPs per key → less rate-limiting
- HM1 is single-IP direct → all 5 keys share same IP → NVCF rate-limits all keys together

## 根因分析
R1637 increased TIER_COOLDOWN_S 15→25 (aligned with HM2). But HM1's single-IP setup means NVCF rate-limits all 5 keys as one IP — the rate-limit window is per-IP. 25s cooldown + ~10s key cycle = 35s total, which may be insufficient for NVCF's rate-limit window to reset on a single-IP setup. HM2's per-key SOCKS5 hides this because each key has a different IP.

## 修改
- **TIER_COOLDOWN_S**: 25 → 35 (+10s)
- Line 502 in `/opt/cc-infra/docker-compose.yml`
- 35 << 205 BUDGET safe
- Single param; iron rule: only change HM1 never HM2

## 验证
- Compose: `grep` → `35` ✓
- Container: `docker exec nv_gw env` → `TIER_COOLDOWN_S=35` ✓
- Health: `curl /health` → `{"status": "ok"}` ✓
## ⏳ 轮到HM1优化HM2
