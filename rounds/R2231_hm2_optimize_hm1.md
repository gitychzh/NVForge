# R2231 (HM2→HM1): KEY_COOLDOWN_S 28→26 (-2s)

## 数据 (6h window, pre-R2230)
- 29 req / 22 OK / 7 zombie (75.9% SR), 0 ATE
- All glm5_2_nv traffic, 0 dsv4p_nv
- OK: avg 14.7s, max 47.9s
- Zombie: avg 8.6s, min 3.2s, max 19.2s (pexec_success with empty-200)
- Key cycling: 23/29 key_cycle_429s=1 (structural, benign), 3/29 cycle=3, 2/29 cycle=2, 1/29 cycle=4
- Tier attempts: 29 pexec_success, 9 pexec_429, 1 SSLEOFError, 1 pexec_timeout

## 分析
- 7 zombies = pexec returns empty completions (NVCF upstream behavior, non-config fixable)
- No ATE — budget is healthy, not binding
- 79% of requests cycle to key 2 (structural cooldown alignment at low traffic ~5 req/h)
- Alternating KEY→KEY pattern (TIER=0): KEY(28)+TIER(0)+GLM5_2(28)=56<<157 BUDGET(101s safe)
- Continue -2s micro-trim on KEY_COOLDOWN_S

## 变更
- **KEY_COOLDOWN_S**: 28→26 (-2s)
- TIER_COOLDOWN_S: 0 (unchanged)
- Budget impact: KEY(26)+TIER(0)+GLM5_2(28)=54<<157 BUDGET(103s), dsv4p: 26+24=50<<94(44s)
- Single param; iron law: only change HM1 never HM2

## 验证
- `docker exec nv_gw env | grep KEY_COOLDOWN_S`: 26 ✓
- `curl /health`: 200 ✓
- `docker compose up -d nv_gw`: container recreated ✓

## ⏳ 轮到HM1优化HM2