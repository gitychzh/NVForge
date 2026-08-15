# RN1069: NOP — NVCF 过载进入流级阻断相位 (IncompleteRead+absolute_cap 取代上一窗连接级错误), SR 80.6%, 错误全孤立(<3)不可调

日期: 2026-08-08 11:52 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF pexec 链路)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

RN1068 (19:16 UTC) 报告 NVCF 连接级过载回归 (RemoteDisconnected+Timeout 均匀全 5 key, SR 85.7%)。
本轮窗口错误**相位从连接级转向流级**：30min 内 **0 RemoteDisconnected / 0 pexec Timeout / 0 显式 529**，
全部错误为流截断/客户端断开/单次 ATE，各错误类型 count<3 未触 ≥3 动作阈值，无一可归因本地杠杆。

## 数据证据

### 30min 主指标
- 总量 36，成功 29，错误 7，其他 0 → **SR = 80.6%** (RN1068: 85.7%)
- Avg/P50/P95: 66039ms / 38703ms / 179165ms
- 请求级 status: 200×29, 错误 7

### 30min 错误分类（tier_attempts 级）
| error_type | n | avg_ms |
|---|---|---|
| NVStream_IncompleteRead | 2 | 34977 |
| client_gone_during_flush | 2 | 197666 |
| stream_absolute_cap | 2 | 172447 |
| all_tiers_exhausted | 1 | 184438 |

请求级 (nv_requests): 与上表一致，无独立 ATE 超出。

### per-key 错误分散（无单 key 聚集）
| key | error | n | avg_ms |
|---|---|---|---|
| 1 | client_gone_during_flush | 1 | 227152 |
| 2 | NVStream_IncompleteRead | 2 | 34977 |
| 2 | stream_absolute_cap | 1 | 167486 |
| 4 | client_gone_during_flush | 1 | 168179 |
| 4 | stream_absolute_cap | 1 | 177407 |
| (空) | all_tiers_exhausted | 1 | 184438 |

错误散布 k1×1, k2×3, k4×2 —— 无单 key 物理劣化，非 SOCKS5/出口 IP 问题。

### per-key 200 延迟
| key | n | avg_ms | p95_ms |
|---|---|---|---|
| 0 | 3 | 37195 | 48298 |
| 1 | 11 | 53855 | 141830 |
| 2 | 3 | 55940 | 115943 |
| 3 | 5 | 37233 | 50167 |
| 4 | 7 | 46404 | 118692 |

key 间负载 (3-11 req) 尚均衡，无异常慢 key。

### upstream_type / finish_reason
- nvcf_pexec: 35/36 (97%), 其他 1 (ATE)
- finish_reason: tool_calls 27, stop 2 —— 长 tool_calls 链占 93%，高延迟主要来自长链

### 429 / fallback
- 30min 请求级 429 = **0**; key_cycle_429s: 0|11, 1|23, 3|2 —— 中间态 429 全部被 key 轮转吸收
- hm4104 fallback 日志 (近 5min): **无** —— adapter 未触发切换
- 0 DB fallback

### 趋势
| 窗口 | SR | 备注 |
|---|---|---|
| 6h | **89.4%** (551/616) | 65 err, 0 timeout |
| 3h 逐小时 | 11:00 66/74=89.2%, 10:00 100/116=86.2%, 09:00 86/100=86.0%, 08:00 12/14=85.7% | 持续受 NVCF 过载压制 |
| 24h | all_tiers_exhausted = **44** | 偏高，反映持续 NVCF 过载天数 |

### 容器状态
- 容器 Up 18 hours, /health ok (status ok, passthrough, 5 keys, port 40666)
- 当前参数与基线一致：UPSTREAM_TIMEOUT=50, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=90,
  KEY_COOLDOWN_S=30, NVU_TIER_BUDGET_DSV4F0731_NV=180, NVU_KEYMGR_429_*=120, NVU_KEYMGR_CONN_*=30/60/120

## 为什么不改参数（逐项排除本地杠杆）

- `UPSTREAM_TIMEOUT=50`: NVStream_IncompleteRead avg 34977ms < 50s —— NVCF 主动截断流，**非我方超时截断**。调高/调低均无益。
- `stream_absolute_cap` @172s: 接近 180s 预算 —— 长 tool_calls 链在预算内未完成被绝对 cap 截断。count=2 孤立，未达 ≥3 聚集阈值；且这是 NVCF 上游长响应劣化，非预算设错（调高预算只让已死长链烧更久）。
- `TIER_BUDGET/DSV4F0731=180`: ATE×1 孤立，未达聚集。5 key 全被 NVCF 拖垮时才 exhaust，非 budget 设错。
- `fast-break` (PEXEC_TIMEOUT=3, CONN_ERR=3): 无连接级错误、无单 key 连续触发模式，fast-break 不适用。
- `KEY_COOLDOWN/CONN_COOLDOWN/429_COOLDOWN`: 429=0、无单 key 持续劣化、无连接错误，冷却调参无收益。
- `integrate 路由` (NV_KEY_INTEGRATE_KEYS 空): R1017 已因 integrate SR 50% 劣于 pexec 70.5% 而全走 pexec DIRECT。本轮为 pexec 流级截断，切 integrate 无数据支持且历史证明更差。
- 数据证明 **NVCF 上游对 dsv4f0731 持续过载，本轮进入流级阻断相位**（IncompleteRead+absolute_cap 取代连接级错误），改本地参数属"对着幻影调参"。

## 上次修改效果 (RN1068 → RN1069)

RN1068 为 NOP，参数未变。对比两轮：
- **SR 回落**: 85.7% (36/42) → **80.6%** (29/36)。NVCF 过载持续，本轮进入峰值。
- **错误构成相位转变**: 连接级 (RemoteDisconnected×12 + pexec Timeout×12 + 显式529×1) →
  **流级** (NVStream_IncompleteRead×2 + stream_absolute_cap×2 + client_gone×2 + ATE×1)。
  连接级错误归零，但流级截断/长链阻断接棒 —— NVCF 过载从"连接被拒"演进为"流中途截断"。
- **成功延迟维持高位**: 本轮 avg 66039ms（含烧满 budget 失败加权），长 tool_calls 链占 93%。
- **fallback 未传导**: 0 DB fallback + hm4104 0 fallback 事件 —— 主链路抖动尚未引发上层切换。
- 参数零改动，纯上游波动。

## 结论

RN1068 的连接级过载在本轮转为**流级阻断**（IncompleteRead/absolute_cap），错误全孤立（各<3）、
无单 key 聚集、0 净 429、0 fallback、无连接级错误。SR 80.6% 为 NVCF 上游持续过载的下游反映，
非本容器可归因。为保持健康稳态基线，本轮 **NOP**。

## 下一步建议

- 持续监测 SR：NVCF 过载呈**振荡+相位演变**（RN1067 消退 → RN1068 连接级回归 → 本轮流级）。
  若后续窗口 SR 回升至 >95% 且错误归零，确认进入恢复期。
- **重点观察 stream_absolute_cap / IncompleteRead 是否聚集至 ≥3/30min**：若聚集，且伴随
  hm4104 fallback 频繁化，才重新评估 TIER_TIMEOUT_BUDGET_S=180 是否过长（长 tool_calls 链
  常烧满预算）。当前 count=2 孤立，继续观察。
- 若 NVCF 过载持续且 SR<85% 波及 hm4104 fallback 频繁，属架构决策（Peer/ms fallback 兜底），
  不在容器自优化范围（NVU_MS_FALLBACK_ENABLED=0, NVU_PEER_FALLBACK_ENABLED=0）。
- 保持当前参数；仅在 NVCF 完全恢复后仍有模式化错误聚集时，才重新评估超时/预算/fast-break。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] 数据完整: 30min SR/延迟/错误分类/per-key/upstream/finish_reason/429/key_cycle/6h/3h/24h/fallback 均已采集
- [x] 错误分类: IncompleteRead×2 + absolute_cap×2 + client_gone×2 + ATE×1, 全孤立各<3
- [x] per-key: 无既慢又错单key, 错误散布 k1/k2/k4, 非 SOCKS5/出口 IP 问题
- [x] 连接级错误归零 (0 RemoteDisconnected/Timeout/529), 进入流级阻断相位
- [x] 决策数据驱动: SR 80.6% + 流级截断全孤立 → NOP, 本地无可调杠杆, 不扰动链路