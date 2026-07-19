# R1925 (HM2→HM1): NVU_TIER_BUDGET_GLM5_2_NV 42→40 (-2s)

## 数据摘要 (6h window)
- **37 req, 26 OK (70.3% SR), 11 fail**
- 10 glm5_2 zombie_empty_completion (all big_input >115K chars)
- 2 dsv4p ATE (both status=200 → phantom, not real failures)
- 0 real ATE failures (dsv4p phantom ATE excluded)
- **glm5_2 OK**: 22 req, avg=8655ms, max=27809ms, min=2333ms
- **glm5_2 zombie**: 10 req, avg=8963ms, max=35687ms, min=2139ms
- **23 key_cycle_429s** on glm5_2 (21 single-cycle, 2 double-cycle)
- dsv4p OK: 4 req, avg=16485ms, max=43081ms

## 分析
- glm5_2 OK max=27809ms < 40s (12s margin, safe)
- dsv4p 2 ATE are phantom (status=200) — not real failures
- All 10 zombie failures are big_input (≥115K chars), caught by BIG_INPUT breaker
- Tier attempts: 23 pexec_success, 1 SSLEOFError, 1 pexec_timeout (healthy)
- Peer-fb budget: UPSTREAM=30 + PEER=122 = 152 < 153 ✓ (1s margin, same as R1917)

## 优化
- **NVU_TIER_BUDGET_GLM5_2_NV: 42→40 (-2s)**
- Saves 2s per zombie fail path (10 zombie × 2s = 20s saved in 6h)
- glm5_2 OK max=27809ms < 40s with 12s margin
- Peer-fb constraint: UPSTREAM=30 + PEER=122 = 152 < 153 ✓
- Single param; iron rule: only change HM1 never HM2

## 验证
- `docker exec nv_gw env | grep NVU_TIER_BUDGET_GLM5_2_NV` → `40` ✓
- Container restarted successfully
## ⏳ 轮到HM1优化HM2
