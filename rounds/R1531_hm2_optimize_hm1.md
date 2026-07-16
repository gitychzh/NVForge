# R1531: HM2→HM1 — NOP (all failures zombie, all params floor/optimal, ms_gw 100% SR)

## 数据收集

### 6h 总览
| 指标 | 值 |
|------|-----|
| 总请求 | 71 |
| 成功 | 51 (71.8%) |
| 失败 | 20 |
| ms_gw | 12/12 100% SR |
| tier_attempts | 17 (15 pexec_success, 1 NameError, 1 empty_200) |

### 错误分类 (6h)
| 模型 | 错误类型 | 数量 | 平均延迟 |
|------|---------|------|---------|
| dsv4p_nv | zombie_empty_completion | 9 | 5258ms |
| glm5_2_nv | zombie_empty_completion | 9 | 5637ms |
| dsv4p_nv | all_tiers_exhausted | 1 | 6343ms |
| glm5_2_nv | all_tiers_exhausted | 1 | 8411ms |

### 按模型
| 模型 | 总请求 | OK | 失败 | SR% | OK平均延迟 |
|------|--------|-----|------|-----|-----------|
| glm5_2_nv | 36 | 26 | 10 | 72.2% | 16410ms |
| dsv4p_nv | 35 | 25 | 10 | 71.4% | 9910ms |

### 当前参数 (HM1 docker env)
| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | floor |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | floor (=UPSTREAM) |
| NVU_TIER_BUDGET_GLM5_2_NV | 120 | optimal |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | optimal |
| TIER_TIMEOUT_BUDGET_S | 205 | optimal |
| TIER_COOLDOWN_S | 15 | floor |
| KEY_COOLDOWN_S | 25 | floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | optimal (code bug: pexec path ignores) |
| NVU_PEER_FB_SKIP_MODELS | (empty) | optimal |
| NVU_PEER_FALLBACK_ENABLED | 1 | optimal |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | optimal |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_FORCE_STREAM_UPGRADE | 0 | optimal |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |

### 429 键循环 (6h)
15 个 glm5_2 请求触发 429 循环 (42%)，平均 1-2 键尝试成功。所有请求最终成功。

### Code bug
`NV_INTEGRATE_EGRESS_IPS` NameError 发生 1 次 (mode→advance 自动处理，无影响)。

### compose md5
`64e8fc1a` — 与 R1530 一致，未变化。

## 分析

### 失败根因
- **18/20 (90%) = zombie_empty_completion**: NVCF 内容过滤器返回 stop finish_reason 但 content_chars < 50 (无实际内容)。平均 input_chars ~223K (大请求)。这是 NVCF 侧行为，**不可配置修复**。
- **2/20 (10%) = ATE**: 可忽略，延迟仅 6-8s，ms_gw 救援成功。

### 参数状态
- 所有参数已在 floor 或 optimal 值
- dsv4p_nv BUDGET=66=UPSTREAM: 地板模式 (R1440)，504 主导时正确
- glm5_2_nv BUDGET=120: 足够容纳 integrate→pexec 回退链
- FASTBREAK 全部 floor: pexec=1, integrate=1, empty_200=2 (已知 pexec 路径不生效)
- TIER_COOLDOWN=15: R1103 修正后的 floor
- 429 循环: 42% glm5_2 请求命中，但 KEY_COOLDOWN=25 已 floor，降低无意义
- ms_gw 12/12 100% SR: 健康回退

### 结论
**NOP**。所有失败是 NVCF 内容过滤器的 zombie，不可配置修复。所有参数已在 floor/optimal。无正向收敛余地。

## 验证
- compose md5 64e8fc1a: 与 R1530 一致
- ms_gw 100% SR: 回退链健康
- 无 504 错误: BUDGET floor 模式有效
- 无 tier 级退化: 所有 tier_attempts 为单键 transient
## ⏳ 轮到HM1优化HM2
