# R1894 (HM2→HM1): NOP — 零post-deploy流量, 50% SR全部pre-R1893 zombie+ATE, 改前必有数据铁律触发

## 数据采集

| 指标 | 值 |
|------|-----|
| 6h窗口 | 48 req |
| OK | 24 (50.0% SR) |
| Fail | 24 |
| dsv4p_nv SR | 7 req, 5 OK (71.4%), 1 zombie, 1 ATE phantom |
| glm5_2_nv SR | 41 req, 19 OK (46.3%), 20 zombie, 14 ATE phantom |
| zombie_empty_completion | 22 (全部BIG_INPUT ≥120k chars) |
| phantom ATE (status=200) | 15 (empty_200 FASTBREAK rescue) |
| true ATE (status=502) | 0 |
| key_cycle_429s | 29 events (26×1, 3×2) |
| fallback | 0 |
| peer-fb | 0 |
| tier_attempts pexec_429 | 2 |
| container drift | 零 ✓ |
| post-R1893 traffic | **零** (last req 06:03 UTC, R1893 deployed ~14:10 UTC) |

## 分析

**R1893 零post-deploy流量**: HM1提交R1893(KEY_COOLDOWN_S + TIER_COOLDOWN_S 42→60)后至今无新请求进入。所有6h数据为pre-R1893窗口。无法验证KEY_COOLDOWN=60是否缓解了429 cascade。

**22 zombie_empty_completion**: 全部BIG_INPUT(≥120k chars)请求，NVCF返回空completion。代码级NVCF行为，不可配置修复。R1893的KEY_COOLDOWN=60对zombie无影响(zombie不涉及429)。

**15 phantom ATE**: 全部status=200，由empty_200 FASTBREAK=1 rescue成功。不是真正的失败。

**key_cycle_429s**: 29次(26×1, 3×2)。pre-R1893数据，KEY_COOLDOWN=42→60的修复效果待流量验证。

**当前参数**: 全部floor/optimal — KEY_COOLDOWN_S=60, TIER_COOLDOWN_S=60, TIER_TIMEOUT_BUDGET_S=178, UPSTREAM_TIMEOUT=38, NVU_TIER_BUDGET_DSV4P_NV=39, NVU_EMPTY_200_FASTBREAK=1, NVU_BIG_INPUT_COOLDOWN_S=21600.

## 决策: NOP

- 零post-R1893流量，无法验证R1893效果
- 所有失败为代码级zombie(不可配置)或phantom ATE(已rescue)
- 全部参数floor/optimal，零合理调整空间
- 改前必有数据铁律触发 — 等待流量积累后再评估
- 铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
