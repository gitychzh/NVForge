# R803: HM2 稳态 NOP — NVCF 未恢复, 链路持续通畅

> 承接 R802 (链路验证 NOP). 8 轮定时优化第 7 轮.
> 铁律: 改前有数据 (NVCF 状态未变), 无新问题 → NOP.
> 角色: HM2-only. 决策: NOP.

## 改前数据 (R802 后, 15min 窗口)

### nv_requests (NV tier)

| tier_model | status | count | avg_ms |
|---|---|---|---|
| dsv4p_nv | 502 | 2 | 70017 | ← R801 70s fail, 持续 |
| glm5_2_nv | 502 | 8 | 845 | ← R797 0.85s fail, 持续 |

### ms_requests (fallback) — 12/12 ok

| backend_model | status | count | avg_ms |
|---|---|---|---|
| ZHIPUAI/GLm-5.2 | ok | 1 | 13168 |
| deepseek-ai/DeepSeek-V4-pro (各 variant) | ok | 11 | 15521-23076 |

agent 端到端 SR 100% 经 ms_gw, 持续通畅.

### NVCF functions 状态 (未恢复)

| function | status |
|---|---|
| ai-glm-5_2 (3b9748d8) | DEGRADED |
| ai-deepseek-v4-pro (74f02205) | ACTIVE (但直连 504/63s) |
| nvquery-kimi-k2_6 (f966661c) | ACTIVE (健康, 200/11s) |
| ai-deepseek-v4-flash (52e1ddb6) | ACTIVE (新, 400 bad-request 未通) |
| sglang-deepseek-v4-pro (8915fd28) | ACTIVE (404 not-found-for-account) |

dsv4p 74f02205 直连仍 504/62.9s. NVCF 未恢复, 状态与 R802 一致.

## 决策: NOP

- NVCF 两个坏 tier 状态未变 (dsv4p 持续 504, glm5_2 DEGRADED).
- R797-R801 机制持续生效 (dsv4p 70s 502, glm5_2 0.85s 502, peer-fb skip).
- agent 经 ms_gw 端到端 100% SR, 链路目标持续达成.
- 无数据驱动的新改动 → NOP.

## 观察 (不本轮改)

- oc4105 `FALLBACK_ENABLED=0`: 属 agent (opencode) 设计选择 (fallback kimi→glm5_2_ms 模型族差异大, 可能有意禁用). 按 CLAU律 "不改 agent 模型选择", 不动. 待 opencode 侧决定.
- dsv4p_nv budget 70: NVCF 恢复后需改回 130. 持续监测 74f02205 直连恢复信号.
- 备选 function (52e1ddb6 flash / 8915fd28 sglang) 当前不可用 (400/404), 待 NVCF 侧权限/格式修复.

## 验证 (NOP)

- nv_gw health ok ✓
- ms_gw 12/12 ok ✓
- 5 adapter 容器 Up ✓

## 跨机协作备注

- R803 NOP, 无部署. 远程 CC 已有 `R803_hm2_optimize_hm1.md` (NOP), 本 round `R803_hm2_steady_nop.md` 区分不冲突.
