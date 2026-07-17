# R1725 — HM2优化HM1: TIER_TIMEOUT_BUDGET_S 135→145 (+10s)

## 数据采集 (HM1)
- **6h窗口**: 60req/50OK(83.3%SR)/10 fail
  - glm5_2_nv: 49OK/8 zombie_empty_completion (3-14s, GFP cadence)
  - dsv4p_nv: 1OK/2 all_tiers_exhausted (69-70s, tiers_tried=1, no peer-fb, no fallback)
- **Tier attempts (6h)**: 55 pexec_success (glm5_2_nv), 3 pexec_SSLEOFError, 1 pexec_429, 0 dsv4p_nv tier_attempts
- **dsv4p_nv tier_attempts (24h)**: 0 rows — EMPTY_200_FASTBREAK=1 kills tier at first empty200, no sub-tier record
- **peer-fb**: 0 activity in logs (HM2 health reachable ✓)
- **Last data**: 20:03 UTC, post-restart 4 new OK (glm5_2_nv)
- **HM1 env**: TIER_TIMEOUT_BUDGET_S=135, NVU_TIER_BUDGET_DSV4P_NV=60, NVU_PEER_FALLBACK_TIMEOUT=125

## 分析
- **R1724预算计算错误**: 假设dsv4p ATE tier time=60s (NVU_TIER_BUDGET_DSV4P_NV), 但实际ATE时间=70s
  - NVU_TIER_BUDGET is NOT enforced as a hard cap — it's a scheduling target, not a kill switch
  - Actual tier consumption: 69-70s (both ATE), not 60s
- **Budget gap**: 70s tier + 125s peer-fb = 195s → cap 135 → peer-fb gets 65s < 72s (HM2 70+2) → peer-fb skipped
  - This is why dsv4p ATE had zero peer-fallback — the budget didn't leave enough room
  - ms_gw MODELMAP excludes dsv4p_nv (R1609: streaming sync defect) → no rescue path
- **Fix**: 135→145 (+10s)
  - 70+125=195→cap 145, peer-fb gets 75s ≥ 72 (HM2 70+2) ✓ (+3s margin)
  - glm5_2 BIG_INPUT→peer-fb: 0+125=125 < 145 ✓
  - OK path: max_ok=51.8s << 145s safe (93s headroom) ✓
- 单参数; 铁律:只改HM1不改HM2

## 修改
- `TIER_TIMEOUT_BUDGET_S`: 135 → 145 (+10s)
- HM1 docker-compose.yml line 489
- 单参数; 铁律:只改HM1不改HM2

## 预算验证
| 路径 | ���算 | 约束 | 状态 |
|------|------|------|------|
| dsv4p ATE→peer-fb | 70+125=195→cap 145 | peer-fb 得 75s ≥ 72 (HM2 70+2) ✓ | ✅ |
| glm5_2 BIG_INPUT→peer-fb | 0+125=125 | < 145 ✓ | ✅ |
| OK path | max_ok=51.8s | < 145 safe (93s headroom) | ✅ |

## 验证
- `docker compose up -d nv_gw` → Started ✓
- `docker exec nv_gw env`: TIER_TIMEOUT_BUDGET_S=145 ✓
- `curl /health`: status=ok ✓
- 无漂移: compose=145, container=145 ✓
## ⏳ 轮到HM1优化HM2
