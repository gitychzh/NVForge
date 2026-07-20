# R2101 (HM2→HM1): TIER_COOLDOWN_S 62→64 (+2s)

## 数据快照 (HM1 6h)
- **Total**: 31 req, 19 OK (61.3% SR), 12 fail
- **Fail**: 8 zombie_empty_completion + 3 ATE + 1 NVStream_IncompleteRead
- **429 cascade**: 22/31 (71.0%) with key_cycle_429s > 0
  - 17 req with key_cycle_429s=1, 1 with 3, 2 with 5, 1 with 7
- **Tier attempts**: 20 pexec_success, 12 pexec_timeout, 6 pexec_SSLEOFError
- **Model**: glm5_2_nv 19/19 OK (100% SR for success), dsv4p_nv 3 ATE
- **ATE detail**: 9 total ATE, 3 real (status=502), 6 phantom (status=200)
- **30min window**: 2 req, 1 OK (50% SR) — low traffic

## 当前配置
- KEY_COOLDOWN_S=69 (R2100), TIER_COOLDOWN_S=62 (R2099)
- KEY+TIER=131 < 153 BUDGET (22s margin)
- MIN_OUTBOUND_INTERVAL_S=0, UPSTREAM_TIMEOUT=24

## 分析
- 71% 429 cycling rate is the dominant problem — far above acceptable
- Despite KEY=69 > 60s NVCF boundary, the NVCF function-level rate limit still overwhelms
- 12 pexec_timeout in tier attempts suggest key 429s → exhausted → timeout
- R2098/R2099/R2100 alternating KEY↑/TIER↑ pattern: this round is TIER's turn
- TIER_COOLDOWN_S=64 gives NVCF more cooldown between tier retries
- Budget: KEY+TIER=69+64=133 < 153 (20s margin) ✓

## 变更
- **TIER_COOLDOWN_S**: 62 → 64 (+2s)
- 单参数; 铁律: 只改HM1不改HM2

## 验证
- `docker exec nv_gw env | grep TIER_COOLDOWN_S` → TIER_COOLDOWN_S=64 ✓
- `docker compose up -d nv_gw` → Container restarted, no errors
- Health: `{"status": "ok"}` ✓
- ms_gw TIER_COOLDOWN_S=62 unchanged (line 185) ✓
## ⏳ 轮到HM1优化HM2
