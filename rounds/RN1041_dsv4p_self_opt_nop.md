# RN1041: NOP — dsv4f0731_nv 链路 30min SR=100% (172/172), 零错误零fallback零429, 5 key 全健康, 不改参数

**日期**: 2026-08-08
**采集窗口**: 2026-08-08 ~05:52 UTC
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
| `NV_INTEGRATE_MODELS` | 空 (纯 pexec 路径, R1006 效果持续) |

env 实测确认与 RN1040 一致，无漂移。`/health` 返回 ok。容器 Up 4 hours。

## 数据 (30min 窗口)

| 指标 | 值 |
|---|---|
| 总量 / 成功 / 失败 | 172 / 172 / 0 |
| SR% | **100%** |
| Avg / P50 / P95 / P99 | 10464ms / 8834ms / 24424ms / 31524ms |
| 错误分类 | (空 — 0 错误) |
| 429 计数 | 0 |
| fallback (hm4104) | 0（最近 5min 无 fallback 日志） |

## Per-key 分析

全部 5 个 key 负载均衡、延迟健康、零错误：

| key | 请求数 | avg(ms) | 错误 |
|---|---|---|---|
| k0 | 36 | 9944 | 0 |
| k1 | 35 | 10931 | 0 |
| k2 | 34 | 10269 | 0 |
| k3 | 34 | 9663 | 0 |
| k4 | 33 | 11564 | 0 |

key 分布均匀（33–36 请求/key），延迟方差小（avg 9663–11564ms），无单 key 劣化。per-key 错误列为空。

注: key_cycle_429s 有 k0=69 / k1=103 的历史累积计数（本窗口实际 429=0，无聚集，均为上一采集周期的旧值，无需关注）。

## Upstream type

- `nvcf_pexec`: 172/172 = 100% SR, avg 10464ms（无 integrate 分流，纯 pexec 路径）

## finish_reason

- tool_calls: 149 (86.6%)
- stop: 23 (13.4%)

正常（工具调用为主，符合 agent 使用模式）。

## 趋势

- 6h: 1992 记录, 1984 success = **99.6% SR** (8 失败)
- 3h 逐小时: 21:00 304/304=100%, 20:00 405/405=100%, 19:00 349/348=99.7%, 18:00 45/44=97.8%
- 24h all_tiers_exhausted: 92（历史累积，本时段 429=0，近期无聚集）

## 决策

依照决策原则：**数据正常（SR>95%, 无异常错误, 延迟稳定）→ NOP 轮，只报告状态不改参数。**

当前状态:
- 30min SR 100%，零错误，零 429，零 fallback
- 5 key 负载均衡、延迟紧致（avg 9.6–11.6s）
- 6h/3h 趋势全部 ≥97.8%，3h 中 2 个小时段 100%

**不做任何参数修改**，避免破坏健康稳定状态。与上一轮 RN1040 状态一致，链路处于最佳状态。

## 下一步建议

- 继续观察。当前链路处于最佳状态（100% SR, 延迟 ~10.5s avg, p95 24.4s）。
- 若下一轮仍健康，继续 NOP。
- 关注点：是否出现 429 或 pexec timeout 聚集、某 key 延迟劣化、all_tiers_exhausted 上升。