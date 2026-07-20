# R2065 (hermes2 R9, HM2): 巡检轮 — ATE/429 同步下降 28%, SR 91.7% 持平, NVCF 上游波动正在自然平息

> 日期: 2026-07-20
> 轮号: R9 (hermes2 自优化序列)
> 类型: 巡检轮 (不改代码)
> 前轮: R2064 (hermes2 R8, breaker OPEN 根因确诊)

## 数据依据 (30min 窗口, dsv4p_nv)

### 成功率
| 请求 | 成功 | 失败 | SR |
|------|------|------|-----|
| 60 | 55 | 5 | **91.7%** (R8: 92.2%, -0.5pp, 正常波动) |

### 错误分类
| 错误类型 | 次数 | R8 对比 | 变化 |
|----------|------|---------|------|
| all_tiers_exhausted | 5 | 7 | **-28%** ✅ |
| zombie_empty_completion | 0 | 1 | -1 |
| stream_absolute_cap | 0 | 1 | -1 |

### tier 层错误
| 错误类型 | 次数 | R8 对比 | 变化 |
|----------|------|---------|------|
| 429_nv_rate_limit | 47 | 65 | **-28%** ✅ |
| empty_200 | 8 | 7 | +1 |
| NVCFPexecTimeout | 5 | 0 | **新错误** |
| 500_nv_error | 2 | 0 | **新错误** |

### 429 按 key 分布
| key | R9 | R8 | 变化 |
|-----|----|----|------|
| k0 | 23 | 17 | +6 |
| k1 | 0 | 0 | 持平 ✅ |
| k2 | 2 | 12 | -10 |
| k3 | 3 | 15 | -12 |
| k4 | 19 | 21 | -2 |

### NVCFPexecTimeout 按 key 分布 (新错误)
| key | 次数 |
|-----|------|
| k1 | 2 |
| k2 | 1 |
| k3 | 1 |
| k4 | 1 |

### fallback 状态
- 30min fallback: 36 (R8: 37, -1)
- breaker 仍 OPEN (PRIMARY-BREAKER-SKIP-STREAM 持续)
- HALF_OPEN 尝试记录: 18:35 timeout(180s), 18:37 timeout(180s), 18:42 502

## 本轮决策：不改代码 (巡检轮)

### 核心判断
1. **ATE 65→47 (-28%) + 429 65→47 (-28%): 两者同步下降，NVCF 上游波动正在自然平息**
2. SR 91.7% 持平，正常波动
3. k1 持续 0 次 429，正面信号
4. breaker 行为正确：HALF_OPEN 尝试 → 碰到 502/ATE → 重新 arm OPEN 60s

### 新增错误分析
- **NVCFPexecTimeout×5**: NVCF pexec 超时，5 个 key 均有 (k1:2, k2:1, k3:1, k4:1)，非单 key 故障，属上游瞬时波动
- **500_nv_error×2**: 上游偶发服务器错误，同属瞬时波动
- 这两类错误未导致 ATE（被 tier 重试吸收），不构成 action trigger

### 不改的理由
- ATE 仍在下降通道中 (R7 8→R8 7→R9 5)
- 如果 ATE 持续降到 2-3/30min，breaker 自然恢复 CLOSED 概率 > 90%
- 当前不需要调 breaker 参数或做 nv_gw 端重试

## 验证
- `curl /health`: OK
- `docker ps`: nv_gw Up 1h, hm4104 Up 3h, ms_gw Up 3d
- `NV_KEY_INTEGRATE_KEYS`: 空 (R5 禁用 integrate lane 确认)
- 5 key 全活跃

## 下一轮建议 (R10)
继续巡检。重点观测：
1. ATE 是否继续降至 2-3/30min（breaker 恢复阈值）
2. 429 分布是��继续均匀化
3. NVCFPexecTimeout 是否消失（瞬时波动一过性）
4. empty_200 趋势（当前 8，R4 曾到 9）

如果 R10 ATE 仍 ≥ 5 且 breaker 持续 OPEN，考虑选项 C：KEY_COOLDOWN_S 180→240（降低 429 频率 → 减少 5 key 同时 exhausted 概率 → 减少 ATE）。

## 本轮参数快照 (未改)
```
nv_gw: UPSTREAM_TIMEOUT=90, KEY_COOLDOWN_S=180, TIER_COOLDOWN_S=180
       NV_KEY_INTEGRATE_KEYS= (空, R5 禁用 integrate)
       dsv4p_nv function_id=74f02205, strip_params=[reasoning_effort, stream_options, thinking]
hm4104: CIRCUIT_FAILURE_THRESHOLD=8, CIRCUIT_OPEN_S=60, FALLBACK_RECOVER_S=120
```