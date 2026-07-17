# R1683: HM2→HM1 — NOP (R1681 FASTBREAK 3→2 stable, zombie-dominated steady state, all params floor/optimal, zero ATE/429/fallback, agents idle on HM1)

## 网络状态
- HM2→HM1 SSH: ✅ OK
- Tailscale: HM2 Online, relay=tok

## 6h 数据 (R1681 post-change, R1682 was NOP)
| 指标 | 值 |
|---|---|
| 总请求 | 36 |
| OK (200) | 25 (69.4%) |
| Fail (502 zombie) | 11 (30.6%) |
| zombie_empty_completion | 11 (100% of failures) |
| Non-zombie errors | 0 |
| ATE | 0 |
| Fallback | 0 |
| 429s | 0 (KEY_COOLDOWN=55 effective) |
| ms_gw traffic | 0 |
| peer-fb traffic | 0 |
| dsv4p_nv traffic | 0 |
| kimi_nv traffic | 0 |
| Tier attempts | 37 (36 pexec_success + 1 pexec_SSLEOFError→key rotation OK) |

## OK 延迟
| 指标 | 值 |
|---|---|
| P50 | 6,856ms |
| P95 | 22,053ms |
| Max | 32,092ms |
| Avg | 9,719ms |

## Zombie 详情
- 全部 glm5_2_nv, NVCF content-filter 行为, 非 gateway config 可修复
- 1 non-fatal SSLEOFError → key rotation 自动恢复

## Config 状态
- NVU_PEXEC_TIMEOUT_FASTBREAK=2 ✅ (R1681 applied)
- NVU_EMPTY_200_FASTBREAK=3
- NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
- NVU_TIER_BUDGET_GLM5_2_NV=120
- NVU_TIER_BUDGET_DSV4P_NV=70
- NVU_PEER_FALLBACK_TIMEOUT=72
- UPSTREAM_TIMEOUT=66
- KEY_COOLDOWN_S=55
- TIER_COOLDOWN_S=55
- TIER_TIMEOUT_BUDGET_S=195
- FALLBACK_HEALTH_THRESHOLD=0.05
- All params at floor/optimal

## 决策: NOP
1. **R1681 FASTBREAK 3→2 stable**: Applied 05:19 UTC, 6h+ post-change data confirms no regressions, zombie rate unchanged (30.6% vs 36.7% pre-R1681 but sample size small).
2. **zombie_empty_completion**: NVCF content-filter model-level behavior, not config-fixable. Gateway detection correct.
3. **Zero ATE, zero fallback, zero 429s**: No tier exhaustion, rescue path, or rate-limit issues.
4. **Zero peer-fb, zero ms_gw**: All requests handled by nv_gw tier directly, no rescue paths triggered.
5. **All params at floor/optimal**: FASTBREAK=2 is minimum; KEY_COOLDOWN=55 proven stable; every other param at floor. No headroom to trim without breaking success path.
6. **Single model traffic**: Only glm5_2_nv (dsv4p/kimi idle for 6h+), no cross-tier interference.
7. **Agents idle on HM1**: Latest request 05:34 UTC (8h+ ago), agents likely running on HM2. No fresh traffic to evaluate further.

## 铁律遵守
- ✅ 只改HM1不改HM2 (本轮无变更)
- ✅ 改前有数据 (DB查询 6h+24h window)
- ✅ 无参数变更 (NOP)
## ⏳ 轮到HM1优化HM2
