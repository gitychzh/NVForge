# RN1072: NOP — NVCF 过载持续振荡第 6 窗, 错误全孤立(<3)不可调, SR 85.4%, hm4104 fallback 传导续(设计兜底)

日期: 2026-08-08 21:04 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF pexec 链路)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

RN1071 (20:14 UTC) 报告 NVCF 过载流级阻断相位。本轮窗口 (21:04 UTC) 延续过载振荡，SR 85.4%。
30min 错误全孤立 (<3)：`NVStream_IncompleteRead×2 + all_tiers_exhausted×2 + client_gone_during_flush×1
+ stream_absolute_cap×1`，散布 k1×2/k3×1/k0×1/k4×1/空×1，无单 key 聚集，0 净 429。失败均因 NVCF
上游过载（流级截断 + tier 级 exhaust），非本地参数杠杆。hm4104 fallback 传导延续（fallback→ms_gw
timeout 后 primary retry 成功），为设计 failover 兜底，非本容器可调。

## 数据证据

### 30min 主指标
- 总量 41，成功 35，错误 6，其他 0 → **SR = 85.4%** (RN1071: 87.8%)
- Avg/P50/P95: 59178ms / 35604ms / 177278ms (p95 ≈ 180s = TIER_TIMEOUT_BUDGET_S 烧满)

### 30min 错误分类（tier_attempts 级）
| error_type | n | avg_ms |
|---|---|---|
| NVStream_IncompleteRead | 2 | 80001 |
| all_tiers_exhausted | 2 | 205593 |
| client_gone_during_flush | 1 | 175233 |
| stream_absolute_cap | 1 | 177278 |

### per-key 错误分散（无单 key 聚集）
| key | error | n | avg_ms |
|---|---|---|---|
| 1 | NVStream_IncompleteRead | 2 | 80001 |
| 0 | all_tiers_exhausted | 1 | 180067 |
| 3 | stream_absolute_cap | 1 | 177278 |
| 4 | client_gone_during_flush | 1 | 175233 |
| (空) | all_tiers_exhausted | 1 | 231118 |

错误散布 k1/k0/k3/k4/空，无单 key 物理劣化，非 SOCKS5/出口 IP 问题。

### per-key 200 延迟
| key | n | avg_ms | p95_ms |
|---|---|---|---|
| 0 | 6 | 31221 | 65129 |
| 1 | 8 | 34976 | 88869 |
| 2 | 9 | 62629 | 133389 |
| 3 | 5 | 32436 | 68808 |
| 4 | 7 | 44231 | 96755 |

key 间负载 (5-9 req) 均衡，无异常慢 key。

### upstream_type / finish_reason
- nvcf_pexec: 40/41 (98%), 其他 1 (ATE)
- finish_reason: tool_calls 28, stop 7 —— 长 tool_calls 链占 80%, 高延迟主要来自长链

### 429 / key_cycle / fallback
- 30min 请求级 429 = **0**; key_cycle_429s: 0|14, 1|21, 2|5, 4|1 —— 中间态 429 全部被 key 轮转吸收
- **hm4104 fallback (近 5min)**: `FALLBACK-FAIL-STREAM` ms_gw 流式 timeout after 70077ms →
  `PRIMARY-RETRY-OK-STREAM` primary 流式 retry 成功。链路兜底被触发且工作正常（fallback 超时后
  primary 重试成功）。

### 趋势
| 窗口 | SR | 备注 |
|---|---|---|
| 6h | **89.0%** (533/599) | 66 err, 0 timeout |
| 3h 逐小时 | 13:00 4(3/1), 12:00 91(81/10), 11:00 92(82/10), 10:00 103(87/16) | 逐小时 75.0%* / 89.0% / 89.1% / 84.5% |
| 24h | all_tiers_exhausted = **51** | 持续 NVCF 过载天数 (RN1071: 47) |

*13:00 样本量仅 4，不可靠。

### 容器状态
- 容器 Up 19 hours, /health ok (status ok, passthrough, 5 keys, port 40666)
- 当前参数与基线一致：UPSTREAM_TIMEOUT=50, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=90,
  KEY_COOLDOWN_S=30, NVU_TIER_BUDGET_DSV4F0731_NV=180, NVU_KEYMGR_429_*=120,
  NVU_KEYMGR_CONN_*=30/60/120, NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_EMPTY_200_FASTBREAK=3,
  NV_KEY_INTEGRATE_KEYS 空, NVU_PEER/MS_FALLBACK_ENABLED=0

## 为什么不改参数（逐项排除本地杠杆）

- `UPSTREAM_TIMEOUT=50`: NVStream_IncompleteRead avg 80001ms 含流中截断，绝对 cap 177278ms 为
  budget 层截断 —— NVCF 主动截断/过载，非我方超时截断。
- `all_tiers_exhausted` @205s ≈ 180s 预算烧满 —— 5 key 全被 NVCF 过载拖垮后才 exhaust，非 budget 设错。
  缩短 budget 减少重试，加长增加死链烧时，180s 为合理平衡。
- `stream_absolute_cap @177s`: 接近 180s budget 上限，属 budget 烧满时流级保护，非独立劣化信号。
- `fast-break` (PEXEC_TIMEOUT=3, EMPTY_200=3): 无单 key 连续触发模式，fast-break 不适用。
- `KEY_COOLDOWN/CONN_COOLDOWN/429_COOLDOWN`: 429=0、无单 key 持续劣化，冷却调参无收益。
- `integrate 路由` (NV_KEY_INTEGRATE_KEYS 空): R1017 已因 integrate SR 50% 劣于 pexec 70.5% 而全走
  pexec DIRECT。本轮为 pexec 流级截断，切 integrate 无数据支持且历史证明更差。
- **hm4104 fallback 传导是设计兜底**：fallback→ms_gw 流式 timeout 后 primary retry 成功 —— 端到端
  可用性由 adapter 的 retry/fallback 逻辑保障，非本容器可调。

## 上次修改效果 (RN1071 → RN1072)

RN1071 为 NOP，参数未变。对比两轮：
- **SR**: 87.8% (43/49) → **85.4%** (35/41)。NVCF 过载持续振荡，略回落。
- **错误构成**: ATE×4+IncompleteRead×1+client_gone×1 → 本轮 IncompleteRead×2+ATE×2+absolute_cap×1+
  client_gone×1。全部孤立 (<3)。
- **fallback 传导续**: hm4104 本轮 fallback→ms_gw timeout 后 primary retry 成功。链路兜底持续被触发，
  端到端可用性由 ms_gw/retry 保障。
- 参数零改动，纯上游波动。

## 结论

RN1068→RN1072 确认 NVCF 对 dsv4f0731_nv 的过载**持续振荡**（流级截断 + tier exhaust 混合相位），本轮 SR 85.4%。
错误全孤立 (<3)、无单 key 聚集、无净 429。hm4104 fallback 传导为设计 failover 兜底（fallback 超时→primary
retry 成功），验证安全网持续正常，非本容器可调问题。为保持健康稳态基线，本轮 **NOP**。

## 下一步建议

- 持续监测 SR：NVCF 过载持续振荡（RN1069 80.6% → RN1070 87.0% → RN1071 87.8% → 本轮 85.4%）。
  关注是否出现连续 2+ 窗口 SR>95% + 错误归零确认进入恢复期。
- **重点观察 hm4104 fallback 频率**：本轮 fallback→ms_gw timeout 后 primary retry 成功，若继续频繁化
  （多请求/短间隔），说明 nv_gw 502 已实质性影响上层可用性 —— 但那属架构决策（Peer/ms fallback
  兜底配置），不在容器自优化范围 (NVU_MS_FALLBACK_ENABLED=0, NVU_PEER_FALLBACK_ENABLED=0)。
- 若 all_tiers_exhausted / IncompleteRead 聚集至 ≥3/30min 且伴随 hm4104 fallback 频繁化，才重新
  评估 TIER_TIMEOUT_BUDGET_S=180 是否过长（长 tool_calls 链常烧满预算）。当前 count=2 但 ATE 为
  tier 级（5 key 全过载），非单 key 可调，继续观察。
- 保持当前参数；仅在 NVCF 完全恢复后仍有模式化错误聚集时，才重新评估超时/预算/fast-break。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] 数据完整: 30min SR/延迟/错误分类/per-key/upstream/finish_reason/429/key_cycle/6h/3h/24h/fallback 均已采集
- [x] 错误分类: IncompleteRead×2 + ATE×2 + absolute_cap×1 + client_gone×1, 全孤立各<3
- [x] per-key: 无既慢又错单key, 错误散布 k1/k0/k3/k4/空, 非 SOCKS5/出口 IP 问题
- [x] 请求级: 200×35 + 错误×6, p95≈180s budget 烧满, 与 hm4104 fallback 传导吻合
- [x] hm4104 fallback: fallback→ms_gw timeout 70077ms → primary retry 成功, 属设计 failover 兜底
- [x] 决策数据驱动: SR 85.4% + 错误全孤立 + 0 净429 + fallback 为设计兜底 → NOP, 本地无可调杠杆, 不扰动链路