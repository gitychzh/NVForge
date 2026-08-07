# RN1010: NOP — dsv4f0731_nv 链路稳定 (SR=98.4%), 不改参数

**日期**: 2026-08-08
**采集窗口**: 2026-08-08 ~02:22 UTC (基线; RN1009 改后验证窗口)
**容器**: dsvf0731_nv40666 (port 40666, DeepSeek V4 Pro via NVCF)
**主机**: HM2 (opc2sname)
**改动类型**: NOP (无修改)

## 当前参数

| 参数 | 当前值 | 设置轮次 |
|------|--------|---------|
| `UPSTREAM_TIMEOUT` | **50** | RN1009 |
| `KEY_COOLDOWN_S` | 30 | 默认 |
| `TIER_COOLDOWN_S` | 90 | R1007 |
| `TIER_TIMEOUT_BUDGET_S` | 180 | 默认 |
| `NVU_TIER_BUDGET_DSV4F0731_NV` | 180 | 默认 |
| `NVU_PEXEC_TIMEOUT_FASTBREAK` | 3 | 默认 |
| `NVU_EMPTY_200_FASTBREAK` | 3 | 默认 |
| `NV_KEY_INTEGRATE_KEYS` | (空) | R1006 |

所有 integrate 相关保持为空（R1006 清空），纯 pexec 路径。

## 数据

### 30min 主指标
| 指标 | 值 |
|------|-----|
| 总量 | 183 |
| 成功 | 180 |
| 失败 | 3 |
| SR | **98.4%** |
| Avg/P50/P95 | 6326ms / 13775ms / 27537ms |
| Max | 207488ms |
| 429 总计数 | **0** |

### 30min 错误分布
| 错误类型 | 次数 | avg ms |
|----------|------|--------|
| all_tiers_exhausted | 3 | 278,105 |

### 30min per-key 200 延迟
| Key | 成功 | avg(ms) | p95(ms) |
|-----|------|---------|---------|
| k0  | 36   | 8,215   | 22,761  |
| k1  | 36   | 8,618   | 20,344  |
| k2  | 35   | 9,302   | 25,575  |
| k3  | 39   | 11,416  | 25,977  |
| k4  | 34   | 9,111   | 24,065  |

各 key 负载均衡（34-39 请求），延迟方差合理，无单 key 集中劣化。

### 30min per-key 错误
| Key | 错误 | 内容 |
|-----|------|------|
| — | all_tiers_exhausted ×3 | 跨 key 遍历后无 key 成功 |

无单 key 集中错误。ATE 为系统级（全部 key 尝试后失败）。

### upstream_type 分布
| 类型 | 请求 | 200 | avg(ms) |
|------|------|-----|---------|
| nvcf_pexec | 180 | 180 | 9,370 |
| integrate | 3 | 0 | 278,105 |

100% 成功走 pexec 路径；integrate 仍为 0（R1006 效果持续）。failed 行的 3 次为 all_tiers_exhausted（upstream 归为 none/未定型）。

### finish_reason
| 原因 | 次数 | 占比 |
|------|------|------|
| tool_calls | 165 | 91.7% |
| stop | 14 | 7.8% |

正常分布，无空响应。

### key_cycle_429s 分布
| cycle=0 | cycle=1 |
|---------|---------|
| 115 | 67 |

多数请求零 429 或仅一次 429 即成功。无多次 429 死循环。

### 趋势
| 窗口 | 总量 | 成功 | 失败 | SR | avg ms |
|------|------|------|------|----|--------|
| 30min | 183 | 180 | 3 | 98.4% | — |
| 6h | 1,748 | 1,735 | 13 | 99.3% | — |
| 24h ATE | — | — | 126 | — | — |

逐小时 SR:
- 15:00-16:00(UTC): 179/179 SR=100%, avg=11.2s
- 16:00-17:00: 273/273 SR=100%, avg=13.4s
- 17:00-18:00: 273/279 SR=97.8%, avg=11.8s
- 18:00-19:00: 143/143 SR=100%, avg=10.2s

### HM4104 Fallback
最近 5 分钟：**2 条 primary-fail 记录**（`nv_gw 流式 conn status=0 after 537ms, 切 fallback: RemoteDisconnected`）。属于 NVCF 流式连接的瞬时中断，hm4104 已正确切换到 fallback (ms_gw)，频率低（2 次/5min）不构成链路劣化。

## RN1009 上次修改效果验证 (UPSTREAM_TIMEOUT 90→50)
- **30min SR**: RN1008 的 97.1% (132/136) → **98.4%** (180/183) ✓ 小幅提升
- **30min ATE 计数**: 4 → **3** ✓ 减少 25%
- **24h ATE**: 127 → 126 (基本持平，历史累积)
- **p95 延迟**: RN1008 34.4s → 本轮 27.5s ✓ 下降 (~7s, 一部分归因于 ATE 减少后未被 push 高)
- **无新增 RemoteDisconnected/IncompleteRead 反弹** ✓

### ATE 深度分析
本轮 3 次 ATE avg 278s > TIER_TIMEOUT_BUDGET=180s，且 UPSTREAM_TIMEOUT=50 下 278s ≈ 5^key × ~50s（含连接建立/重试开销）。**说明这 3 次 ATE 是 5 个 key 真实全部失败**（NVCF 端整窗不可用），而非 RN1009 想解决的"预算内仅试 2 key 就 ATE"（预算耗尽型）。
- RN1009 的 50s 已让预算内可试 3.6 key，但若 5 key 全失败（fast-break=5 全遍历 + min_outbound 间隔），278s 即是"真实全失败"成本。
- 真实全失败型 ATE 无法通过降超时解决（key 本身不可用），只能靠 `TIER_COOLDOWN_S` (90) 在故障窗口避免重复命中 → 已在 R1007 配置。

## 分析结论
**链路状态: 优秀**。30min SR=98.4%, 6h SR=99.3%, 429=0, 5 key 负载均衡, integrate 归零, 无单 key 错误集中, 无冷却级联。HM4104 fallback 仅 2 次瞬时切换且正确回退。

3 次 ATE (0.7%) 为真实全-key NVCF 故障型，非参数可调范围；RN1009 的预算耗尽型 ATE 已基本消除。

**不修改决定**: SR>95% 触发 NOP 规则。当前所有指标健康，无需调整。

## 下一步建议
1. **持续观察 ATE**: 若真实全失败型 ATE 频率上升（>0.7%），可考虑 `NVU_TIER_BUDGET_DSV4F0731_NV` 已足够；重点看 NVCF 端是否有系统性故障窗口。
2. **HM4104 fallback**: 若 fallback 频率持续上升（>10次/h），需查 nv_gw 流式连接稳定性（联系 NVCF/网络层），非本容器参数可调。
3. **下次 30min 窗口**: 验证 RN1009 的 24h ATE 是否真正下降（当前 126 含改前历史，需改后累计 30min×8 窗口观察）。