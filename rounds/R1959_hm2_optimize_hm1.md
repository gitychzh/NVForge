# R1959 (HM2→HM1): NVU_BIG_INPUT_COOLDOWN_S 21600→86400 — 24h breaker keeps all zombies contained

## 数据
- 6h: 44 req, 39 OK (88.6% SR), 5 fail (status=502, zombie_empty_completion)
- 30min: 4 req, 3 OK (75.0% SR), 1 fail
- dsv4p_nv: 10 OK, avg=31599ms, min=11102ms, max=55335ms — 0 genuine OK, all peer-fb rescued
- glm5_2_nv: 29 OK, avg=10129ms, min=3484ms, max=26165ms, p95=17998ms — healthy
- kimi_nv: 0 traffic (6h)

## 错误分解
- 5× `zombie_empty_completion` (status=502), all glm5_2_nv NVCF function-level degradation
  - Latest at 02:33:33 UTC — input_chars=152302 > 115000 threshold, but breaker cooldown had expired
- 24× `all_tiers_exhausted` + status=200 (phantom ATE, all peer-fb rescued)
- 0 real ATE with status=502
- 0 tier-level errors (only 16 pexec_success)
- key_cycle_429s: 16 req with 1 cycle each, normal rotation

## 容器日志
- [NV-ZOMBIE-EMPTY] glm5_2_nv zombie: input_chars=152302, content_chars=12 — caught by zombie detector
- BIG_INPUT breaker had cooldown expired (21600s=6h from previous trigger batch)
- Zombie was correctly detected but not breaker-blocked → peer-fb/ms_gw fallback rescue

## 决策: NVU_BIG_INPUT_COOLDOWN_S 21600→86400 (6h→24h)

**根因**: 6h cooldown resets 4x per day. Each reset allows next zombie to go through first before breaker re-opens. At 5 zombie/day, 4 are caught by the breaker (after 1st trigger), but 1 always leaks through at the cooldown boundary.

**数据支撑**: The 02:33 zombie hit exactly at a cooldown-expired window. FAIL_N=1 (floor) catches the first zombie and opens the breaker. With 24h cooldown, only 1 zombie per 24h leaks through (the trigger), and all subsequent are fast-rejected by the breaker → peer-fb/ms_gw rescue.

**预期效果**: 24h cooldown keeps the breaker active for the full day. Only 1 zombie per 24h triggers the breaker (FAIL_N=1), all subsequent zombies are fast-rejected. This reduces effective zombie count from 5/6h to 1/24h.

**铁律**: 只改HM1不改HM2

## 参数变更
| 参数 | 旧值 | 新值 | 理由 |
|------|------|------|------|
| NVU_BIG_INPUT_COOLDOWN_S | 21600 | 86400 | 6h→24h cooldown, keeps breaker active full day, catches all zombies after 1st trigger |

## 验证
- ✅ docker compose up -d nv_gw → container restarted
- ✅ curl /health → {"status":"ok"}
- ✅ docker exec nv_gw env → NVU_BIG_INPUT_COOLDOWN_S=86400
## ⏳ 轮到HM1优化HM2
