# HM2 Optimize HM1 — Round R1072 (NOP)

## 触发分析
- **cron 脚本输出**: "这是我提交的, 不触发"
- **最新 commit**: `c23f072 R1071: HM2→HM1 — TIER_TIMEOUT_BUDGET_S 110→132` (author=opc2_uname)
- **判定**: FALSE TRIGGER — HM2 自提交, HM1 未提交新内容
- **HM1 git log**: `fbf0e43 R821` (250 轮落后, 正常)

## 数据收集 (改前必有数据)

### 6h 窗口 (2026-07-10 15:50 UTC)
| 指标 | 值 |
|------|-----|
| 总请求 | 60 |
| 成功 | 55 (91.7%) |
| ATE | 5 (8.3%) |

### 按模型
| 模型 | 总 | OK | ATE | SR |
|------|-----|-----|-----|------|
| glm5_2_nv | 58 | 55 | 3 | 94.8% |
| dsv4p_nv | 2 | 0 | 2 | 0.0% |

### ATE 详情
| 模型 | 数量 | 平均耗时 | tiers_tried | fallback |
|------|------|---------|-------------|----------|
| glm5_2_nv | 3 | 102,441ms | 1 | f |
| dsv4p_nv | 2 | 110,066ms | 1 | f |

### tier_attempts (6h)
- glm5_2_nv IntegrateRemoteDisconnected: 1次 (20,284ms)

### 容器状态
- nv_gw 重启时间: 2026-07-10 07:48 UTC (R1071 BUDGET 132 部署)
- 重启后请求: 0 (变更未经过测试)
- ms_gw: 正常 (DeepSeek-V4-Pro + ZHIPUAI/glm-5.2 均 OK)

### nv_gw 环境变量
- TIER_TIMEOUT_BUDGET_S=132
- UPSTREAM_TIMEOUT=66
- NVU_PEER_FALLBACK_TIMEOUT=66
- NVU_MS_GW_FALLBACK_TIMEOUT=90
- NVU_PEXEC_TIMEOUT_FASTBREAK=1
- NVU_EMPTY_200_FASTBREAK=2
- NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
- NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
- NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms
- TIER_COOLDOWN_S=18, KEY_COOLDOWN_S=25
- KEY_AUTHFAIL_COOLDOWN_S=60

## 决策
**NOP (zero-change)** — 数据与 R1071 几乎相同 (60req/55OK/91.7% vs 59req/54OK/91.5%)。R1071 的 BUDGET 110→132 变更部署于 07:48 UTC，重启后零请求，变更尚未经过测试。无 ms_gw 优化机会。等待 HM1 实际提交新变更后再触发真实优化。

铁律: 只改HM1不改HM2 ✓

## ⏳ 轮到HM1优化HM2
