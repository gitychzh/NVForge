# R1501: HM2→HM1 — NOP (zero new data, all params floor/optimal, zombie+ATE dominated)

## 数据收集

### SSH HM1
- SSH: `ssh -p 222 opc_uname@100.109.153.83` — 成功连接
- nv_gw health: `{"status": "ok"}`, 5 keys, 4 models active
- compose md5: `ba4f2871` (与 R1498/R1499/R1500 相同，未变更)

### DB (6h 窗口)
| 指标 | 值 |
|------|-----|
| 总请求 | 59 |
| 成功 | 36 (61.0%) |
| 失败 | 23 |
| 最新请求 | 2026-07-15 20:06:34 UTC (≈8.5h 零新流量) |

### 错误分类
| 模型 | 错误类型 | 数量 | 平均延迟 |
|------|---------|------|---------|
| glm5_2_nv | zombie_empty_completion | 12 | 12,274ms |
| dsv4p_nv | zombie_empty_completion | 6 | 11,644ms |
| dsv4p_nv | all_tiers_exhausted | 5 | 63,580ms |

**总计**: 18 zombie (78%), 5 ATE (22%)

### 按模型
| 模型 | 总数 | 成功 | SR | 平均成功延迟 |
|------|------|------|-----|-------------|
| dsv4p_nv | 35 | 24 | 68.6% | 22,554ms |
| glm5_2_nv | 24 | 12 | 50.0% | 14,816ms |

### 按小时
| 小时 (UTC) | 总数 | 成功 | SR |
|------------|------|------|-----|
| 14:00 | 3 | 1 | 33.3% |
| 15:00 | 6 | 2 | 33.3% |
| 16:00 | 9 | 6 | 66.7% |
| 17:00 | 8 | 4 | 50.0% |
| 18:00 | 18 | 14 | 77.8% |
| 19:00 | 9 | 5 | 55.6% |
| 20:00 | 6 | 4 | 66.7% |

### Tier 尝试
- 2× `429_integrate_rate_limit` (glm5_2_nv) — 瞬时速率限制，非配置可修复

### ms_gw
- 20/16 (80.0%) — 健康

### Fallback
- 58 无 fallback 触发
- 1 fallback_occurred=false 但 fallback_actually_attempted=true

### 24h 错误全景
- 50 zombie_empty_completion
- 19 all_tiers_exhausted
- 零 504, 零 tier-cycling, 零 peer-fb, 零 ms-fb

## Live 日志分析 (tail 100)

| 信号 | 数量 | 说�� |
|------|------|------|
| NV-ZOMBIE-EMPTY | 6 | NVCF content-filter，代码级不可修复 |
| NV-INTEGRATE-SUCCESS | 6 | 全部首次尝试成功 |
| NV-THINKING-TIMEOUT | 若干 | thinking 请求超时延长 66s |
| NV-TIER-FAIL | 0 | ✅ |
| NV-CYCLE | 0 | ✅ |
| NV-PEER-FB | 0 | ✅ |
| NV-MS-FB | 0 | ✅ |
| 504 | 0 | ✅ |
| NV-NONCYCLE | 0 | ✅ |

### Zombie 键循环模式 (代码级)
```
k2 → NV-THINKING-TIMEOUT (17.4s) → k3 → NV-THINKING-TIMEOUT (8.3s) → k4 → NV-ZOMBIE-EMPTY (2.3s)
```
网关在 pexec 路径中循环 3 个键后检测到 zombie。EMPTY_200_FASTBREAK=2 不适用（zombie 返回 200+12 字符内容，非 empty_200）。这是代码级 zombie 检测行为，不可配置修复。

## 环境变量 (全部参数)

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | 地板 |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | 地板 (=UPSTREAM) |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | 地板 |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | 地板 |
| TIER_TIMEOUT_BUDGET_S | 205 | 最优 |
| TIER_COOLDOWN_S | 15 | 地板 |
| KEY_COOLDOWN_S | 25 | 地板 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 地板 |
| NVU_EMPTY_200_FASTBREAK | 2 | 最优 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | 地板 |
| NVU_PEER_FALLBACK_ENABLED | 1 | 最优 |
| NVU_PEER_FB_SKIP_MODELS | (空) | 最优 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | 最优 |
| NVU_CONNECT_RESERVE_S | 0 | 地板 |
| MIN_OUTBOUND_INTERVAL_S | 0 | 地板 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | 地板 |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | 最优 |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | 最优 |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | 最优 |
| NVU_FORCE_STREAM_UPGRADE | 0 | 最优 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | 最优 |

**全部 16 个参数已触底/最优。**

## 决策: NOP

### 失败根因分析
1. **zombie_empty_completion (78%)**: NVCF 返回 finish_reason=stop 但 content_chars=12 < 50，网关正确检测+快速 abort。代码级 NVCF content-filter 问题，不可配置修复。
2. **all_tiers_exhausted (22%)**: dsv4p_nv 5× ATE，avg 63.6s ≈ BUDGET 66 地板。BUDGET=UPSTREAM_TIMEOUT 已是最紧安全边界。peer-fb 已启用 (NVU_PEER_FB_SKIP_MODELS=空)，ms_gw 80% SR 健康。

### 零可配置修复项
- 零 504 → 无需调整 UPSTREAM_TIMEOUT
- 零 tier cycling → 无需调整 COOLDOWN
- 零 peer-fb/ms-fb → 无需调整 fallback 参数
- 零 SSLEOFError → 无需调整 retry delay
- FASTBREAK 全部地板 → 无需调整
- BUDGET 全部地板 → 无需调整
- compose md5 未变 → 无需重启

### 与 R1499/R1500 对比
完全相同的 NOP 模式 — 同一数据集 (59 请求)，同样 zombie 主导，同样全部参数触底。连续 3 轮零新数据，零新流量，零可配置问题。

## 铁律
- ✅ 只改HM1不改HM2 — 本轮无配置修改
- ✅ compose md5 ba4f2871 未变
- ✅ 铁律:只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
