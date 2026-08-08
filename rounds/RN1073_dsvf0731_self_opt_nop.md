# RN1073: NOP — NVCF 过载振荡第 7 窗, SR 回升 92.3%, 错误全孤立(<3), 无本地杠杆

日期: 2026-08-08 21:48 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF pexec 链路)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

RN1072 (21:04 UTC) 报告 NVCF 过载流级阻断相位。本轮 (21:48 UTC) 延续过载振荡但 SR 回升至 92.3%
(RN1072: 85.4%)。30min 错误全孤立 (<3)：`all_tiers_exhausted×1 + client_gone_during_flush×1 +
stream_absolute_cap×1`，散布 k0×2/k2×1，无单 key 聚集，0 净 429。失败均因 NVCF 上游过载（tier 级
exhaust + 流级截断），非本地参数杠杆。hm4104 fallback 传导延续（PRIMARY-BREAKER-SKIP-STREAM →
FALLBACK-STREAM），为设计 failover 兜底，非本容器可调。

## 数据证据

### 30min 主指标
- 总量 39，成功 36，错误 3，其他 0 → **SR = 92.3%** (RN1072: 85.4%)
- Avg/P50/P95: 52769ms / 30210ms / 176846ms (p95 ≈ 176s 接近 TIER_TIMEOUT_BUDGET_S=180 烧满)

### 30min 错误分类（tier_attempts 级）
| error_type | n | avg_ms |
|---|---|---|
| all_tiers_exhausted | 1 | 180087 |
| client_gone_during_flush | 1 | 186854 |
| stream_absolute_cap | 1 | 176486 |

### per-key 错误分散（无单 key 聚集）
| key | error | n | avg_ms |
|---|---|---|---|
| 0 | all_tiers_exhausted | 1 | 180087 |
| 0 | stream_absolute_cap | 1 | 176486 |
| 2 | client_gone_during_flush | 1 | 186854 |

错误散布 k0×2/k2×1，各 <3，无单 key 物理劣化，非 SOCKS5/出口 IP 问题。

### per-key 200 延迟
| key | n | avg_ms | p95_ms |
|---|---|---|---|
| 0 | 6 | 44802 | 116739 |
| 1 | 6 | 32485 | 58971 |
| 2 | 5 | 51089 | 77948 |
| 3 | 8 | 34698 | 80414 |
| 4 | 11 | 47075 | 139691 |

key 间负载 (5-11 req) 均衡，无异常慢 key。

### upstream_type / finish_reason
- nvcf_pexec: 39/39 (100%), 成功 36 → pexec SR = 92.3%
- finish_reason: tool_calls 17, stop 19 —— 长短链混合 (RN1072 tool_calls 主导)，延迟中位回落至 30s

### 429 / key_cycle / fallback
- 30min 请求级 429 = **0**; key_cycle_429s: 0|11, 1|25, 2|2, 3|1 —— 中间态 429 全部被 key 轮转吸收
- **hm4104 fallback (近 5min)**: `PRIMARY-BREAKER-SKIP-STREAM` → `FALLBACK-STREAM` 连续出现
  (21:43-21:44, 4 次)。primary 流式跳过 (circuit OPEN 或 fallback 冷却) → 直走 ms_gw。链路 failover
  兜底持续被触发，工作正常。

### 趋势
| 窗口 | SR | 备注 |
|---|---|---|
| 6h | **88.1%** (503/571) | 68 err, 0 timeout |
| 3h 逐小时 | 13:00 57(49/8), 12:00 91(81/10), 11:00 92(82/10), 10:00 13(8/5) | 85.9% / 89.0% / 89.1% / 61.5%* |
| 24h | all_tiers_exhausted = **53** | 持续 NVCF 过载计数 (RN1072: 51) |

*10:00 样本量仅 13，不可靠。

### 容器状态
- 容器 Up 19 hours, /health ok (status ok, passthrough, 5 keys, port 40666)
- 当前参数与基线一致：UPSTREAM_TIMEOUT=50, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=90,
  KEY_COOLDOWN_S=30, NVU_TIER_BUDGET_DSV4F0731_NV=180, NVU_KEYMGR_429_*=120,
  NVU_KEYMGR_CONN_*=30/60/120, NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_EMPTY_200_FASTBREAK=3,
  NV_KEY_INTEGRATE_KEYS 空, NVU_PEER/MS_FALLBACK_ENABLED=0

## 为什么不改参数（逐项排除本地杠杆）

- `UPSTREAM_TIMEOUT=50`: 三个错误均 ≥176s (stream_absolute_cap 176486 / ATE 180087 / client_gone 186854)
  —— 全是 budget 层截断 (≈180s TIER_TIMEOUT_BUDGET_S 烧满)，非 UPSTREAM_TIMEOUT 读超时截断。
- `all_tiers_exhausted @180s`: 5 key 全被 NVCF 过载拖垮后才 exhaust，非 budget 设错。缩短 budget 减少
  重试，加长增加死链烧时，180s 为合理平衡。
- `stream_absolute_cap @176s`: 接近 180s budget 上限，属 budget 烧满时流级保护，非独立劣化信号。
- `fast-break` (PEXEC_TIMEOUT=3, EMPTY_200=3): 无单 key 连续触发模式，fast-break 不适用。
- `KEY_COOLDOWN/CONN_COOLDOWN/429_COOLDOWN`: 429=0、无单 key 持续劣化，冷却调参无收益。
- `integrate 路由` (NV_KEY_INTEGRATE_KEYS 空): 本轮 100% pexec，SR 92.3%，切 integrate 无数据支持且
  历史证明更差 (R1017 integrate SR 50% 劣于 pexec 70.5%)。
- **hm4104 fallback 传导是设计兜底**：PRIMARY-BREAKER-SKIP-STREAM → FALLBACK-STREAM，端到端可用性由
  adapter 的 breaker/fallback 逻辑保障，非本容器可调。

## 上次修改效果 (RN1072 → RN1073)

RN1072 为 NOP，参数未变。对比两轮：
- **SR**: 85.4% (35/41) → **92.3%** (36/39)。NVCF 过载振荡内回升。
- **错误构成**: IncompleteRead×2+ATE×2+absolute_cap×1+client_gone×1 → 本轮 ATE×1+absolute_cap×1+
  client_gone×1。全部孤立 (<3)，count 下降 (6→3)。
- **fallback 传导续**: hm4104 本轮 PRIMARY-BREAKER-SKIP-STREAM → FALLBACK-STREAM 连续 4 次。链路兜底
  持续被触发，端到端可用性由 ms_gw/breaker 保障。
- 参数零改动，纯上游波动。

## 结论

RN1068→RN1073 确认 NVCF 对 dsv4f0731_nv 的过载**持续振荡**（tier exhaust + 流级截断混合相位），本轮
SR 回升至 92.3%，错误数回落 (6→3)。错误全孤立 (<3)、无单 key 聚集、无净 429。hm4104 fallback 传导为
设计 failover 兜底（breaker skip → ms_gw），验证安全网持续正常，非本容器可调问题。为保持健康稳态基线，
本轮 **NOP**。

## 下一步建议

- 持续监测 SR：NVCF 过载振荡 (RN1072 85.4% → 本轮 92.3%)。关注是否出现连续 2+ 窗口 SR>95% + 错误
  归零确认进入恢复期。
- **重点观察 hm4104 fallback 频率**：本轮 breaker-skip 连续 4 次，若继续频繁化（多请求/短间隔），说明
  nv_gw 502 已实质性影响上层可用性 —— 但那属架构决策（Peer/ms fallback 兜底配置），不在容器自优化
  范围 (NVU_MS_FALLBACK_ENABLED=0, NVU_PEER_FALLBACK_ENABLED=0)。
- 若 all_tiers_exhausted / stream_absolute_cap 聚集至 ≥3/30min 且伴随 hm4104 fallback 频繁化，才重新
  评估 TIER_TIMEOUT_BUDGET_S=180 是否过长（长 tool_calls 链常烧满预算）。当前 count=1 且为 tier 级
  （5 key 全过载），非单 key 可调，继续观察。
- 保持当前参数；仅在 NVCF 完全恢复后仍有模式化错误聚集时，才重新评估超时/预算/fast-break。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] 数据完整: 30min SR/延迟/错误分类/per-key/upstream/finish_reason/429/key_cycle/6h/3h/24h/fallback 均已采集
- [x] 错误分类: ATE×1 + absolute_cap×1 + client_gone×1, 全孤立各<3
- [x] per-key: 无既慢又错单key, 错误散布 k0×2/k2×1, 非 SOCKS5/出口 IP 问题
- [x] 请求级: 200×36 + 错误×3, p95≈176s budget 烧满, 与 hm4104 fallback 传导吻合
- [x] hm4104 fallback: PRIMARY-BREAKER-SKIP-STREAM → FALLBACK-STREAM 连续 4 次, 属设计 failover 兜底
- [x] 决策数据驱动: SR 92.3% + 错误全孤立 + 0 净429 + fallback 为设计兜底 → NOP, 本地无可调杠杆, 不扰动链路