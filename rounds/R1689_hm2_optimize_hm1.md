# R1689: HM2→HM1 — NOP (zombie-dominated, R1688 FASTBREAK just deployed, all params floor/optimal)

**决策**: NOP — 零可配置修复项。R1688 FASTBREAK 1→2 刚部署需观察。全部参数触底/最优。

## 数据摘要

### 6h 窗口 (38req/27OK/11fail = 71.1% SR)
| 指标 | 值 |
|------|-----|
| 总请求 | 38 |
| 成功 | 27 (71.1%) |
| 失败 | 11 |
| zombie_empty_completion | 11 (100% of failures, NVCF content-filter, 不可配置) |
| ATE | 0 |
| fallback | 0 |
| peer-fb | 0 |
| 429 key cycling | 0 |

### 按模型
| 模型 | 请求 | OK | 失败 | SR | 失败原因 |
|------|------|-----|------|-----|---------|
| glm5_2_nv | 38 | 27 | 11 | 71.1% | 全部 zombie_empty_completion |
| dsv4p_nv | 0 | 0 | 0 | — | 无流量 |
| kimi_nv | 0 | 0 | 0 | — | 无流量 |

### zombie_empty_completion (代码级，不可配置修复)
- 全部 11 个失败均为 `zombie_empty_completion`，`tiers_tried=1`
- NVCF 返回 `finish_reason=stop`，但 `content_chars` 不足 50 字符
- 日志: `[NV-ZOMBIE-EMPTY] finish_reason=stop but content_chars=14 reasoning_chars=0 < 50 (content-only, R852b), input_chars=274590 >= 5000, no real tool_calls — aborting stream to trigger fallback`
- Gateway 正确检测+快速 abort，触发 cc4101 zombie→api_error→CC retry
- 这是 NVCF 服务端内容过滤行为，非本地配置可修复

### tier_attempts
- glm5_2_nv: 38× pexec_success, 1× pexec_SSLEOFError (瞬态, 0.5s retry delay 足以处理)

### 容器状态
- nv_gw: Running, env 与 compose 一致 (无漂移)
- 最后请求: 2026-07-17 07:33 UTC (glm5_2_nv)
- 日志显示 k1+k2 均被尝试 (FASTBREAK=2 生效中)

### 日志 (最近 nv_gw)
```
[15:33:20.4] [NV-GLM52-ATTEMPT] tier=glm5_2_nv mode=pexec_us_rr k1 timeout=66s
[15:33:48.2] [NV-GLM52-ATTEMPT] tier=glm5_2_nv mode=pexec_us_rr k2 timeout=66s
[15:34:14.5] [NV-ZOMBIE-EMPTY] aborting stream to trigger fallback
```
→ FASTBREAK=2 生效，k1+k2 均被尝试后才触发 fallback

## 参数状态 (全部触底/最优 — 与 R1688 相同)

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | 最优 (R1490) |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 2 | R1688 刚改 → 需观察 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | 触底 |
| NVU_EMPTY_200_FASTBREAK | 3 | 最优 (R1681→2, R1688→2 pexec) |
| TIER_TIMEOUT_BUDGET_S | 195 | 最优 (R1647) |
| NVU_TIER_BUDGET_DSV4P_NV | 70 | 触底 (R1663, 对齐 HM2) |
| NVU_TIER_BUDGET_GLM5_2_NV | 120 | 最优 |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | 最优 |
| TIER_COOLDOWN_S | 65 | 最优 (R1687, KEY=TIER=65 对齐) |
| KEY_COOLDOWN_S | 65 | 最优 (R1687, NVCF 60s+5s buffer) |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | 触底 (R919) |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | 最优 (R1459) |
| NVU_PEER_FALLBACK_TIMEOUT | 72 | 最优 |
| NVU_PEER_FB_SKIP_MODELS | (空) | 最优 (R1646) |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms | 最优 (R1609) |
| NVU_CONNECT_RESERVE_S | 0 | 触底 |
| NVU_SSLEOF_RETRY_DELAY_S | 0.5 | 触底 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | 对齐 UPSTREAM |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | 最优 |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | 最优 |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | 最优 |
| MIN_OUTBOUND_INTERVAL_S | 0 | 触底 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | 触底 |

### 预算验证
- glm5_2_nv: FASTBREAK=2×10+66=86<120 ✓
- dsv4p_nv: 70+72=142<195 ✓
- KEY=TIER=65 对齐，65+65=130<<195 ✓
- PEER_FALLBACK_TIMEOUT=72 ≥ HM2 BUDGET=70+2 ✓

## 铁律验证
- ✅ 只改HM1: 本轮无修改
- ✅ 改前必有数据: 6h DB + tier_attempts + 容器日志
- ✅ 改后必有验证: N/A
- ✅ 聚焦 nv_gw: 仅分析 nv_gw 链路
- ✅ 所有修改写入仓库: 本轮 NOP 仍记录
## ⏳ 轮到HM1优化HM2
