# R1682: HM2→HM1 — NOP (R1681 post-change warmup, zombie-dominated steady state, all params floor/optimal, NVCF content-filter not config-fixable)

## 网络状态
- HM2→HM1 SSH: ✅ OK
- Tailscale: HM2 Online, relay=tok

## 6h 数据 (pre-R1681)
| 指标 | 值 |
|---|---|
| 总请求 | 30 |
| OK (200) | 19 (63.3%) |
| Fail (502 zombie) | 11 (36.7%) |
| zombie_empty_completion | 11 (100% of failures) |
| Non-zombie errors | 0 |
| ATE | 0 |
| Fallback | 0 |
| 429s | 0 (KEY_COOLDOWN=55 effective) |
| ms_gw traffic | 0 |
| dsv4p_nv traffic | 0 |
| kimi_nv traffic | 0 |
| Tier attempts | 30 (all pexec_success on glm5_2_nv) |

## OK 延迟
| 指标 | 值 |
|---|---|
| P50 | 6,856ms |
| P95 | 22,850ms |
| Max | 32,092ms |
| Avg | 9,785ms |

## Zombie 详情
- 全部 glm5_2_nv integrate, finish_reason=stop, input ~245K-254K chars
- Zombie 检测: 2-36s (代码级检测正确, 非config可修复)
- NVCF content-filter 行为: 返回 stop + 12 chars, 无 model-call 输出

## Config 状态
- NVU_PEXEC_TIMEOUT_FASTBREAK=2 ✅ (R1681 applied, container restarted 05:19 UTC)
- NVU_EMPTY_200_FASTBREAK=3 (unchanged — irrelevant for pexec zombie path)
- NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
- NVU_TIER_BUDGET_GLM5_2_NV=120
- NVU_PEER_FALLBACK_TIMEOUT=72
- UPSTREAM_TIMEOUT=66
- KEY_COOLDOWN_S=55
- TIER_TIMEOUT_BUDGET_S=195
- FALLBACK_HEALTH_THRESHOLD=0.05
- All params at floor/optimal

## 决策: NOP
1. **R1681 post-change warmup**: FASTBREAK 3→2 applied at 05:19 UTC, ALL 6h data is pre-R1681 (latest request 05:03:34 UTC). Need 6h+ post-change data for evaluation.
2. **zombie_empty_completion**: NVCF content-filter model-level behavior, not config-fixable. Gateway detection correct.
3. **Zero ATE, zero fallback**: No tier exhaustion or rescue path issues.
4. **Zero 429s**: KEY_COOLDOWN=55 stable.
5. **All params at floor/optimal**: No headroom to trim without breaking success path.
6. **Single model traffic**: Only glm5_2_nv (dsv4p/kimi idle for 6h+), no cross-tier interference.

## 铁律遵守
- ✅ 只改HM1不改HM2 (本轮无变更)
- ✅ 改前有数据 (DB查询 6h window)
- ✅ 无参数变更 (NOP)
## ⏳ 轮到HM1优化HM2
