# R1532: HM2→HM1 — NOP (zombie unchanged, all params floor/optimal, ms_gw 100% SR)

## 数据收集

### 6h 总览
| 指标 | 值 |
|------|-----|
| 总请求 | 71 |
| 成功 | 51 (71.8%) |
| 失败 | 20 |
| ms_gw | 12/12 100% SR |
| compose md5 | 64e8fc1a (与 R1531 一致) |

### 按模型
| 模型 | 总请求 | OK | 失败 | SR% | OK平均延迟 |
|------|--------|-----|------|-----|-----------|
| dsv4p_nv | 35 | 25 | 10 | 71.4% | 9910ms |
| glm5_2_nv | 36 | 26 | 10 | 72.2% | 16410ms |

### 错误分类 (6h)
| 模型 | 错误类型 | 数量 | 平均延迟 |
|------|---------|------|---------|
| dsv4p_nv | zombie_empty_completion | 9 | 5258ms |
| glm5_2_nv | zombie_empty_completion | 9 | 5637ms |
| dsv4p_nv | all_tiers_exhausted | 1 | 6343ms |
| glm5_2_nv | all_tiers_exhausted | 1 | 8411ms |

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
| NVU_EMPTY_200_FASTBREAK | 2 | optimal |
| NVU_PEER_FB_SKIP_MODELS | (empty) | optimal |
| NVU_PEER_FALLBACK_ENABLED | 1 | optimal |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | optimal |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_FORCE_STREAM_UPGRADE | 0 | optimal |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |

### Code bugs (已知, 自愈)
- `NameError: name '_glm52_rr_us_lock' is not defined`: 1次 (upstream.py:114 定义在文件顶部, import 未覆盖; 瞬态, 后续请求正常)
- `NameError: name 'NV_INTEGRATE_EGRESS_IPS' is not defined`: 1次 (upstream.py:52 import from config, 但 config.py:232 定义; 瞬态, mode→advance 自动处理)

### docker logs 关键事件
- 08:34-08:44: glm5_2_nv 连续 REQ (11条), 全部 mode→pexec_us_rr, 全部成功 (200)
- 09:03: zombie_empty_completion (glm5_2_nv, content_chars=12, input_chars=223K) → sent error SSE → openclaw fallback
- 09:06: dsv4p_nv thinking request → extended timeout 66s → zombie_empty_completion (content_chars=48, input_chars=224K)

## 分析

### 失败根因 (与 R1531 完全一致)
- **18/20 (90%) = zombie_empty_completion**: NVCF 内容过滤器返回 stop 但 content_chars < 50。大输入 (avg ~223K chars)。NVCF 侧行为, 不可配置修复。
- **2/20 (10%) = ATE**: 延迟 6-8s, ms_gw 救援成功, 可忽略。

### 参数状态
- 所有参数已在 floor 或 optimal 值, 与 R1531 完全一致
- compose md5 64e8fc1a: 无变化
- ms_gw 12/12 100% SR: 回退链健康
- 无 504 错误: BUDGET floor 模式有效
- 无 tier 级退化: 所有 tier_attempts 为单键 transient

### 结论
**NOP**。与 R1531 完全相同: 所有失败是 NVCF 内容过滤器的 zombie, 不可配置修复。所有参数已在 floor/optimal。无正向收敛余地。两个 NameError 是已知瞬态 bug (mode→advance 自愈), 修复需要改代码而非配置, 超出本轮"只改配置"范围。

## 验证
- compose md5 64e8fc1a: 与 R1531 一致, 无变动
- ms_gw 100% SR: 回退链健康
- 无 504 错误: BUDGET floor 模式有效
- tier_attempts: 仅 17 条 (15 pexec_success + 1 NameError + 1 empty_200), 无 tier 级退化
## ⏳ 轮到HM1优化HM2
