# RN1070: NOP — NVCF 过载第 4 窗持续振荡, 错误全孤立(<3)不可调, 首次 hm4104 fallback 传导经设计 failover 兜底, SR 87.0%

日期: 2026-08-08 20:00 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF pexec 链路)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

RN1069 (11:52 UTC) 报告 NVCF 过载进入流级阻断相位 (IncompleteRead+absolute_cap 取代连接级错误)。
本轮窗口 (20:00 UTC) 延续过载振荡，SR 小幅回升至 87.0%。30min 错误全孤立 (<3)：
`all_tiers_exhausted×2 + stream_absolute_cap×2 + NVStream_IncompleteRead×1 + client_gone_during_flush×1`，
散布 k0/k2/k4/空，无单 key 聚集，0 净 429。失败均因 NVCF 上游过载，非本地参数杠杆。
**新信号**：hm4104 首次出现 PRIMARY-FAIL-STREAM 502 → ms_gw fallback 传导 —— 这是 nv_gw 502 经
设计 failover 兜底（adapter 层切 ms_gw），验证链路兜底正常，非本容器可调问题。

## 数据证据

### 30min 主指标
- 总量 46，成功 40，错误 6，其他 0 → **SR = 87.0%** (RN1069: 80.6%)
- Avg/P50/P95: 57863ms / 36074ms / 179369ms
- 40min 窗口 status: 200×53 (avg 45655), **502×5 (avg 148649 ≈ TIER_BUDGET 180s 烧满 → ATE)**, 499×2 (client_gone, avg 220887)

### 30min 错误分类（tier_attempts 级）
| error_type | n | avg_ms |
|---|---|---|
| all_tiers_exhausted | 2 | 182231 |
| stream_absolute_cap | 2 | 172447 |
| NVStream_IncompleteRead | 1 | 33890 |
| client_gone_during_flush | 1 | 214621 |

### per-key 错误分散（无单 key 聚集）
| key | error | n | avg_ms |
|---|---|---|---|
| 0 | all_tiers_exhausted | 1 | 180023 |
| 2 | NVStream_IncompleteRead | 1 | 33890 |
| 2 | stream_absolute_cap | 1 | 167486 |
| 4 | client_gone_during_flush | 1 | 214621 |
| 4 | stream_absolute_cap | 1 | 177407 |
| (空) | all_tiers_exhausted | 1 | 184438 |

错误散布 k0×1, k2×2, k4×2, 空×1 —— 无单 key 物理劣化，非 SOCKS5/出口 IP 问题。

### per-key 200 延迟
| key | n | avg_ms | p95_ms |
|---|---|---|---|
| 0 | 4 | 29993 | 47789 |
| 1 | 10 | 46644 | 100111 |
| 2 | 7 | 49717 | 109382 |
| 3 | 8 | 33057 | 50294 |
| 4 | 11 | 45902 | 148807 |

key 间负载 (4-11 req) 均衡，无异常慢 key。

### upstream_type / finish_reason
- nvcf_pexec: 45/46 (98%), 其他 1 (ATE)
- finish_reason: tool_calls 35, stop 5 —— 长 tool_calls 链占 87.5%，高延迟主要来自长链

### 429 / key_cycle / fallback
- 30min 请求级 429 = **0**; key_cycle_429s: 0|15, 1|29, 3|2 —— 中间态 429 全部被 key 轮转吸收
- **hm4104 fallback (近 10min)**: `PRIMARY-FAIL-STREAM` nv_gw 502 after 180030ms → 切 ms_gw;
  `PRIMARY-BREAKER-SKIP-STREAM` circuit OPEN 直走 fallback。**首次传导至 adapter 层**。
- DB nv_requests `fallback_occurred=0`：ms_gw fallback 记在 ms_requests，属 adapter 层 failover，非 nv_requests 字段。

### 趋势
| 窗口 | SR | 备注 |
|---|---|---|
| 6h | **89.6%** (554/618) | 64 err, 0 timeout |
| 3h 逐小时 | 11:00 91, 10:00 116, 09:00 100 | 逐小时 89.1% / 86.2% / 86.0% |
| 24h | all_tiers_exhausted = **45** | 持续 NVCF 过载天数 |

### 容器状态
- 容器 Up 18 hours, /health ok (status ok, passthrough, 5 keys, port 40666)
- 当前参数与基线一致：UPSTREAM_TIMEOUT=50, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=90,
  KEY_COOLDOWN_S=30, NVU_TIER_BUDGET_DSV4F0731_NV=180, NVU_KEYMGR_429_*=120, NVU_KEYMGR_CONN_*=30/60/120

## 为什么不改参数（逐项排除本地杠杆）

- `UPSTREAM_TIMEOUT=50`: NVStream_IncompleteRead avg 33890ms < 50s —— NVCF 主动截断流，**非我方超时截断**。
- `stream_absolute_cap` @172s: 接近 180s 预算 —— 长 tool_calls 链在预算内未完成被绝对 cap 截断。count=2 孤立，未达 ≥3 聚集阈值；调高预算只让已死长链烧更久。
- `TIER_BUDGET/DSV4F0731=180`: ATE×2 + 502×5 (avg 149s ≈ 烧满 budget) —— 5 key 全被 NVCF 拖垮时才 exhaust，非 budget 设错。缩短 budget 减少重试，加长增加死链烧时。
- `fast-break` (PEXEC_TIMEOUT=3, EMPTY_200=3): 无单 key 连续触发模式，fast-break 不适用。
- `KEY_COOLDOWN/CONN_COOLDOWN/429_COOLDOWN`: 429=0、无单 key 持续劣化，冷却调参无收益。
- `integrate 路由` (NV_KEY_INTEGRATE_KEYS 空): R1017 已因 integrate SR 50% 劣于 pexec 70.5% 而全走 pexec DIRECT。本轮为 pexec 流级截断，切 integrate 无数据支持且历史证明更差。
- **hm4104 fallback 传导是设计兜底**：nv_gw 502 after 180030ms (budget 烧满) → adapter 正确切 ms_gw。
  这是 NVCF 过载下的预期 failover，非故障；切回逻辑由 adapter 管理，不在容器自优化范围。

## 上次修改效果 (RN1069 → RN1070)

RN1069 为 NOP，参数未变。对比两轮：
- **SR 回升**: 80.6% (29/36) → **87.0%** (40/46)。NVCF 过载仍在振荡但较上一峰值略缓解。
- **错误构成**: 上轮 IncompleteRead×2+absolute_cap×2+client_gone×2+ATE×1 → 本轮
  ATE×2+absolute_cap×2+IncompleteRead×1+client_gone×1。构成相似，全部孤立 (<3)。
- **新信号**: 本轮首次出现 hm4104 PRIMARY-FAIL-STREAM 502 → ms_gw fallback 传导
  (上轮"0 DB fallback + hm4104 0 fallback 事件")。链路兜底被实际触发，工作正常。
- 参数零改动，纯上游波动。

## 结论

RN1068→RN1070 确认 NVCF 对 dsv4f0731_nv 的过载**持续振荡**（连接级→流级→当前混合相位），
本轮 SR 87.0%。错误全孤立 (<3)、无单 key 聚集、无净 429。首次 hm4104 fallback 传导为
设计 failover 兜底（502→ms_gw），验证安全网正常，非本容器可调问题。为保持健康稳态基线，本轮 **NOP**。

## 下一步建议

- 持续监测 SR：NVCF 过载持续振荡（RN1067 92.9% → RN1068 85.7% → RN1069 80.6% → 本轮 87.0%）。
  关注是否出现连续 2+ 窗口 SR>95% + 错误归零确认进入恢复期。
- **重点观察 hm4104 fallback 频率**：若 502→ms_gw 传导频繁化（多请求/短间隔），说明 nv_gw 502 已
  实质性影响上层可用性 —— 但那属架构决策（Peer/ms fallback 兜底配置），不在容器自优化范围
  (NVU_MS_FALLBACK_ENABLED=0, NVU_PEER_FALLBACK_ENABLED=0)。
- 若 stream_absolute_cap / IncompleteRead 聚集至 ≥3/30min 且伴随 hm4104 fallback 频繁化，才重新
  评估 TIER_TIMEOUT_BUDGET_S=180 是否过长（长 tool_calls 链常烧满预算）。当前 count=2 孤立，继续观察。
- 保持当前参数；仅在 NVCF 完全恢复后仍有模式化错误聚集时，才重新评估超时/预算/fast-break。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] 数据完整: 30min SR/延迟/错误分类/per-key/upstream/finish_reason/429/key_cycle/6h/3h/24h/fallback 均已采集
- [x] 错误分类: ATE×2 + absolute_cap×2 + IncompleteRead×1 + client_gone×1, 全孤立各<3
- [x] per-key: 无既慢又错单key, 错误散布 k0/k2/k4/空, 非 SOCKS5/出口 IP 问题
- [x] 请求级: 200×53 + 502×5 (avg 149s) + 499×2, 502 与 hm4104 fallback 传导吻合
- [x] hm4104 fallback: PRIMARY-FAIL-STREAM 502→ms_gw 首次传导, 属设计 failover 兜底
- [x] 决策数据驱动: SR 87.0% + 错误全孤立 + 0 净429 + fallback 为设计兜底 → NOP, 本地无可调杠杆, 不扰动链路