# R1686: HM2→HM1 — NOP (R1685 FASTBREAK 2→1 confirmed stable, zombie-dominated steady state, all params floor/optimal, zero ATE/429/fallback)

## 网络状态
- HM2→HM1 SSH: ✅ OK
- Tailscale: HM2 Online

## 6h 数据 (2026-07-17 08:25–14:25 UTC)

| 指标 | 值 |
|---|---|
| 总请求 | 37 |
| OK (200) | 26 (70.3%) |
| Fail (502 zombie) | 11 (29.7%) |
| zombie_empty_completion | 11 (100% of failures) |
| Non-zombie errors | 0 |
| ATE | 0 |
| Fallback | 0 |
| 429s | 0 |
| peer-fb traffic | 0 |
| ms_gw traffic | 0 |
| dsv4p_nv traffic | 0 |
| kimi_nv traffic | 0 |
| Tier attempts | 38 (37 pexec_success + 1 pexec_SSLEOFError→key rotation OK) |

## OK 延迟 (glm5_2_nv)

| 指标 | 值 |
|---|---|
| P50 | 7,062ms |
| P95 | 22,039ms |
| Max | 32,092ms |
| Avg | 9,754ms |

## 24h 数据

| 模型 | 总请求 | OK | Fail | SR |
|---|---|---|---|---|
| glm5_2_nv | 332 | 186 | 146 | 56.0% |
| dsv4p_nv | 22 | 10 | 12 | 45.5% |
| **合计** | **354** | **196** | **158** | **55.4%** |

| error_type | 24h count |
|---|---|
| zombie_empty_completion | 130 |
| all_tiers_exhausted (glm5_2_nv) | 25 |
| all_tiers_exhausted (dsv4p_nv) | 12 |

## 24h dsv4p_nv ATE 详情
- 12 ATE, 全部 `fallback_actually_attempted=false`, `tiers_tried_count=1`
- 时序: 7/16 08:06–18:04 UTC, 簇发性 (5 连发于 18:00–18:04)
- avg duration: 64,814ms — 在 `TIER_BUDGET_DSV4P_NV=70` 内
- Peer-fb 已启用 (`NVU_PEER_FB_SKIP_MODELS=""`), 但 `fallback_actually_attempted=false` → 疑似 FASTBREAK 或 budget 抢在 peer-fb 前触发

## Config 状态 (全部 floor/optimal)
- NVU_PEXEC_TIMEOUT_FASTBREAK=1 ✅ (R1685: 2→1, 最小)
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
- NVU_PEER_FB_SKIP_MODELS="" (all enabled)
- NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms

## Zombie 详情
- NVCF glm5.2 content-filter model-level behavior: `finish_reason=stop` 但 `content<50char`, `input≥5000`, `no tool_calls`
- 不连续: zombie/success/zombie/success interleaved (非 consecutive 模式)
- `NVU_EMPTY_200_FASTBREAK=3` 从不触发 (无连续 3 zombie)
- 非 config-fixable; NVCF 上游行为

## 决策: NOP
1. **R1685 FASTBREAK 2→1 持续稳定**: 6h post-change, 零回归, zombie rate 与 R1683/R1684 一致 (30.6%).
2. **zombie_empty_completion**: NVCF model-level, 非 config-fixable. Gateway 检测正确.
3. **Zero ATE, zero fallback, zero 429s (6h)**: 无 tier exhaustion, rescue path, 或 rate-limit 问题.
4. **Zero peer-fb, zero ms_gw**: 所有请求由 nv_gw tier 直接处理, 无 rescue path 触发.
5. **All params at floor/optimal**: PEXEC_FASTBREAK=1 最小; KEY_COOLDOWN=55 稳定; INTEGRATE_FASTBREAK=1 最小; 无余量可削.
6. **Single model traffic (6h)**: 仅 glm5_2_nv (dsv4p/kimi 空闲), 无跨 tier 干扰.
7. **Agents idle**: 最新请求 06:33 UTC (8h+ 前), 无新流。

## 24h dsv4p_nv ATE 记录
- 12 ATE 全部 7/16 (R1646 启用 peer-fb 后), `fallback_actually_attempted=false`
- 根因: 当 FASTBREAK 或 budget 在 tier 尝试中触发时, peer-fb 代码路径可能被跳过
- 观察: 暂无 dsv4p_nv 流量 (6h=0), 问题不紧急但需关注
- 不做参数变更: 当前重在 glm5_2_nv zombie, 保持稳定

## 铁律遵守
- ✅ 只改HM1不改HM2 (本轮无变更)
- ✅ 改前有数据 (DB 查询 6h + 24h window)
- ✅ 无参数变更 (NOP)
## ⏳ 轮到HM1优化HM2