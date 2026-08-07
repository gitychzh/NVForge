# RN1044: NOP — dsv4f0731_nv 链路 30min SR=100% (174/174), 零错误零fallback零429, 5 key 全健康, 不改参数

**日期**: 2026-08-08
**采集窗口**: 2026-08-08 ~07:52 UTC
**容器**: dsvf0731_nv40666 (port 40666, DeepSeek V4 Pro via NVCF)
**主机**: HM2 (opc2sname)
**改动类型**: NOP (无修改)

## 当前参数 (脚本 env 实测确认，无漂移)

| 参数 | 当前值 |
|------|--------|
| `UPSTREAM_TIMEOUT` | 50 |
| `KEY_COOLDOWN_S` | 30 |
| `TIER_COOLDOWN_S` | 90 |
| `TIER_TIMEOUT_BUDGET_S` | 180 |
| `NVU_TIER_BUDGET_DSV4F_NV` | 180 |
| `NVU_PEXEC_TIMEOUT_FASTBREAK` | 3 |
| `NVU_EMPTY_200_FASTBREAK` | 3 |
| `NVU_KEYMGR_429_BASE/MAX_COOLDOWN` | 120/120 |
| `NVU_KEYMGR_CONN_BASE/MAX/LONG` | 30/60/120, THRESHOLD=3 |
| `NVU_PROBE_TIMEOUT` | 10 |
| `NVU_BUFFER_TIMEOUT_STAIRS` | 90×5 |
| `NV_INTEGRATE_MODELS` | 空 (纯 pexec 路径) |

env 实测确认与 RN1043 一致，无���移。容器 Up 6 hours。

## 数据 (30min 窗口)

| 指标 | 值 |
|---|---|
| 总量 / 成功 / 失败 | 174 / 174 / 0 |
| SR% | **100%** |
| Avg / P50 / P95 | 11220ms / 8432ms / 28015ms (总均值) |
| 错误分类 | (空 — 0 错误) |
| 429 计数 | 0 |
| fallback (hm4104) | 0（最近 5min 无 fallback 日志） |

## Per-key 分析

全部 5 个 key 负载均衡、延迟健康、零错误：

| key | 请求数 | avg(ms) | p95(ms) | 错误 |
|---|---|---|---|---|
| k0 | 34 | 11090 | 21951 | 0 |
| k1 | 35 | 11517 | 24988 | 0 |
| k2 | 35 | 9949 | 27908 | 0 |
| k3 | 35 | 13377 | 31210 | 0 |
| k4 | 35 | 10163 | 32023 | 0 |

key 分布均匀（34–35 请求/key），延迟方差小（avg 9949–13377ms），无单 key 劣化。per-key 错误列为空。

注: key_cycle_429s 有 k0=63 / k1=111 的历史累积计数（本窗口实际 429=0，无聚集，均为上一采集周期的旧值，无需关注）。

## Upstream type

- `nvcf_pexec`: 174/174 = 100% SR, avg 11220ms（无 integrate 分流，纯 pexec 路径）

## finish_reason

- tool_calls: 152 (87.4%)
- stop: 22 (12.6%)

正常（工具调用为主，符合 agent 使用模式）。

## 趋势

- 6h: 2031 记录, 2023 success = **99.6% SR** (8 失败)
- 3h 逐小时: 23:00 273/273=100%, 22:00 265/262=99.2%, 21:00 355/355=100%, 20:00 48/48=100%
- 24h all_tiers_exhausted: 53（历史累积，本时段 429=0，近期无聚集）

## 决策

这是一轮 NOP。系统在 30min 窗口内表现完美：SR=100%、零错误、零 429、零 fallback、5 key 均匀健康、6h SR 99.6%。当前参数组合（纯 pexec 路径 + UPSTREAM_TIMEOUT=50 + TIER_COOLDOWN=90 + 429 冷却 120s）持续产出最优链路质量。

**遵循"如需修改必须有数据支撑 + 一次只改一个参数"铁律，无劣化数据则不改任何参数。** 避免为了"看起来在优化"而做无意义的改动，保持稳定优先。

## 验证

- `/health` → status ok
- 容器 Up 6 hours
- 无参数修改，无需重启

## 下一步建议

继续监控。当前链路质量稳定（连续多轮 100% SR，自 RN1034 起持续 NOP）。若后续出现 `all_tiers_exhausted` 24h 计数显著上升、某 key 延迟持续劣化、或某 key 错误集中，再针对性调参。本轮 pexec 延迟 avg 11220ms / p95 28015ms，k3/k4 p95 略高于 30s，若持续抬升到 >30s 考虑 UPSTREAM_TIMEOUT 微调。