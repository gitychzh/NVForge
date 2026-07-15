# HM2 Optimize HM1 — Round R1410 (NOP, false trigger, double-dispatch, 569th chain of R1133)

## 触发分析
cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2)，R1409 已提交
- 脚本正确检测到自提交并标记 "不触发"，但仍被 cron 派遣 → 误触发/双派遣
- HM1 本地 git log 停留在 R1206（203 轮落后），未提交任何新内容
- Symlink 已指向 R1409（正确），git status clean

## 数据收集 (改前必有数据)

### nv_gw 6h 窗口
| 指标 | 值 |
|---|---|
| Total | 16 |
| OK (200) | 13 |
| Fail (502) | 3 |
| SR | 81.3% |
| Tier attempts | 0 |

### 502 错误明细
| 模型 | 错误类型 | 数量 | 平均延迟 |
|---|---|---|---|
| glm5_2_nv | zombie_empty_completion | 2 | 7,624ms |
| dsv4p_nv | all_tiers_exhausted | 1 | 106,052ms |

### Hourly SR
| 小时 (UTC) | Total | OK | Fail | SR |
|---|---|---|---|---|
| 00:00 | 4 | 4 | 0 | 100.0% |
| 01:00 | 6 | 5 | 1 | 83.3% |
| 02:00 | 6 | 4 | 2 | 66.7% |

### nv_gw 日志分析
- **glm5_2_nv zombie**: `finish_reason=stop content_chars=12 < 50`，R1405 fix 生效（`finish_reason=timeout`），`[NV-ZOMBIE-ERROR-CHUNK]` 正确发送 error SSE chunk → openclaw fallback。code-level，不可配置。
- **dsv4p_nv ATE**: k4→504 gateway+timeout，k5→NVCFPexecTimeout 40,296ms，FASTBREAK=1 → `[NV-TIER-FAIL]` → `[NV-MS-FB]` ms_gw relay TimeoutError 198,814ms。R1103 BUDGET enforcement gap — ms_gw relay 超时远超 BUDGET=205s 和 NVU_MS_GW_FALLBACK_TIMEOUT=195s。code-level streaming sync defect，不可配置。
- **Tier chain**: `['glm5_2_nv']` / `['dsv4p_nv']` (no fallback, 3model) — FALLBACK_GRAPH={}，R832 设计预期，ms_gw same-model fallback 为救援路径。

### ms_gw 6h
| Total | OK | Fail | SR |
|---|---|---|---|
| 5 | 4 | 1 | 80.0% |

- glm5_2_ms: stream_no_data_lines 循环 v8→v9→v0→v1 后 v2 成功（ZHIPUAI/GlM-5.2）
- dsv4p_ms: deepseek-ai/DEEPSEEK-V4-PRO 成功（1 次）

### 当前参数 (floor/optimal)
| 参数 | 值 | 状态 |
|---|---|---|
| UPSTREAM_TIMEOUT | 66 | floor |
| TIER_TIMEOUT_BUDGET_S | 205 | optimal |
| NVU_TIER_BUDGET_DSV4P_NV | 106 | optimal |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | floor |
| KEY_COOLDOWN_S | 25 | floor |
| TIER_COOLDOWN_S | 15 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_MS_GW_FALLBACK_TIMEOUT | 195 | optimal |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | optimal |
| PROXY_TIMEOUT | 300 | optimal |

### ms_gw 参数
| 参数 | 值 | 状态 |
|---|---|---|
| EMPTY_200_FASTBREAK_THRESHOLD | 3 | floor |
| KEY_COOLDOWN_S | 60 | stable |
| VARIANT_COOLDOWN_S | 30 | stable |

### Compose md5
`f493494e2b41b17fbf5d9cff9093648e` — 自 container restart 2026-07-14T23:43:06Z 以来未变。

## 决策: NOP

**0 config-fixable issues。** All 3 failures are code-level:
1. 2× zombie_empty_completion (glm5_2_nv): NVCF content-filter，R1405 fix 已生效，gateway 正确检测并 fast-abort
2. 1× ATE (dsv4p_nv): ms_gw relay TimeoutError 198,814ms，R1103 BUDGET enforcement gap — streaming sync defect，不可配置

所有参数均为 floor/optimal，无优化空间。铁律: 只改HM1不改HM2（本轮无改动）。

## ⏳ 轮到HM1优化HM2
