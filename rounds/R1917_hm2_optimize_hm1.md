# R1917 (HM2→HM1): TIER_TIMEOUT_BUDGET_S 155→153 (-2s)

## 6h DB数据 (pre-R1917, R1916 baseline)
- **42 req, 31 OK (73.8% SR), 11 fail**
- 9 zombie (zombie_empty_completion, all glm5_2_nv except 1 dsv4p_nv)
- 2 real ATE (dsv4p_nv, status=502)
- 17 phantom ATE (status=200, counted in OK)
- OK duration: min=1779ms, max=27809ms, avg=7983ms
- Per-model: glm5_2_nv 32/24OK(75%)/8 zombie, dsv4p_nv 10/7OK(70%)/1 zombie/2 real ATE

## Analysis
- Zombie rate unchanged (9/42=21.4%) — all NVCF empty_200 on glm5_2_nv function, not config-fixable
- OK max=27.8s << UPSTREAM=30s safe, zero risk of budget cut hitting success path
- Budget floor: UPSTREAM(30) + PEER_FALLBACK_TIMEOUT(122) = 152s
- 155→153 leaves 1s margin above floor, saves 2s on zombie/ATE paths

## Change
- **TIER_TIMEOUT_BUDGET_S: 155→153** (-2s)
- Single param; iron rule: only change HM1 never HM2

## Verification
- `docker compose up -d nv_gw` → Container started OK
- `/health` → `{"status": "ok"}`
- `docker exec nv_gw env | grep TIER_TIMEOUT_BUDGET_S` → `153` ✓
## ⏳ 轮到HM1优化HM2
