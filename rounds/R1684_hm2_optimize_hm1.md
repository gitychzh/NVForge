# R1684: HM2→HM1 — NOP (R1683 NOP continued, zombie-dominated steady state, all params floor/optimal, zero ATE/429/fallback, agents idle 8h+)

## 网络状态
- HM2→HM1 SSH: ✅ OK
- Tailscale: HM2 Online

## 6h 数据
|| 指标 | 值 |
||---|---|
|| 总请求 | 36 |
|| OK (200) | 25 (69.4%) |
|| Fail (502 zombie) | 11 (30.6%) |
|| zombie_empty_completion | 11 (100% of failures) |
|| Non-zombie errors | 0 |
|| ATE | 0 |
|| Fallback | 0 |
|| 429s | 0 |
|| ms_gw traffic | 0 |
|| peer-fb traffic | 0 |
|| dsv4p_nv traffic | 0 |
|| kimi_nv traffic | 0 |
|| Tier attempts | 37 (36 pexec_success + 1 pexec_SSLEOFError→key rotation OK) |

## OK 延迟
|| 指标 | 值 |
||---|---|
|| P50 | 6,856ms |
|| P95 | 22,053ms |
|| Max | 32,092ms |
|| Avg | 9,719ms |

## Zombie 详情
- 全部 glm5_2_nv, NVCF content-filter 行为, 非 gateway config 可修复
- 1 non-fatal SSLEOFError → key rotation 自动恢复
- 最新请求 05:34 UTC (8h+ 前), agents 空闲

## Config 状态
- NVU_PEXEC_TIMEOUT_FASTBREAK=2 ✅ (R1681)
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
- NVU_PEER_FB_SKIP_MODELS="" (empty, all enabled)
- All params at floor/optimal

## 决策: NOP
1. **R1681 FASTBREAK 3→2 持续稳定**: 12h+ post-change, 零回归, zombie rate 稳定 30.6%.
2. **zombie_empty_completion**: NVCF content-filter model-level behavior, 非 config-fixable. Gateway 检测正确.
3. **Zero ATE, zero fallback, zero 429s**: 无 tier exhaustion, rescue path, 或 rate-limit 问题.
4. **Zero peer-fb, zero ms_gw**: 所有请求由 nv_gw tier 直接处理, 无 rescue path 触发.
5. **All params at floor/optimal**: FASTBREAK=2 最小; KEY_COOLDOWN=55 稳定; 无余量可削.
6. **Single model traffic**: 仅 glm5_2_nv (dsv4p/kimi 空闲 6h+), 无跨 tier 干扰.
7. **Agents idle on HM1**: 最新请求 05:34 UTC (8h+ 前), 无新流量评估.
8. **peer-fb constraint noted**: HM1 PEER_FALLBACK_TIMEOUT=72 < HM2 BUDGET_GLM5_2_NV=120+2, glm5_2_nv peer-fb 保证超时 (R1641 known). 但无 peer-fb 流量, 不紧急.

## 铁律遵守
- ✅ 只改HM1不改HM2 (本轮无变更)
- ✅ 改前有数据 (DB查询 6h window)
- ✅ 无参数变更 (NOP)
## ⏳ 轮到HM1优化HM2
