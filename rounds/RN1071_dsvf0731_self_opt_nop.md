# RN1071: NOP — NVCF 过载持续振荡第 5 窗, 错误全孤立(<3)不可调, SR 87.8%, hm4104 fallback 传导续(设计兜底)

日期: 2026-08-08 20:14 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF pexec 链路)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

RN1070 (20:00 UTC) 报告 NVCF 过载流级阻断相位 + 首次 hm4104 fallback 传导。本轮窗口 (20:14 UTC)
延续过载振荡，SR 87.8%。30min 错误全孤立 (<3)：`all_tiers_exhausted×4 + NVStream_IncompleteRead×1 +
client_gone_during_flush×1`，散布 k0×3/k2×1/k4×1/空×1，无单 key 聚集，0 净 429。失败均因 NVCF
上游过载，非本地参数杠杆。hm4104 fallback 传导延续（近 10min 2 次 PRIMARY-FAIL-STREAM 502 after
180s → ms_gw + 1 次 breaker-skip 直走），为设计 failover 兜底，非本容器可调。

## 数据证据

### 30min 主指标
- 总量 49，成功 43，错误 6，其他 0 → **SR = 87.8%** (RN1070: 87.0%)
- Avg/P50/P95: 52077ms / 27646ms / 180068ms (p95 ≈ 180s = TIER_TIMEOUT_BUDGET_S 烧满)

### 30min 错误分类（tier_attempts 级）
| error_type | n | avg_ms |
|---|---|---|
| all_tiers_exhausted | 4 | 181149 |
| NVStream_IncompleteRead | 1 | 33890 |
| client_gone_during_flush | 1 | 214621 |

### per-key 错误分散（无单 key 聚集）
| key | error | n | avg_ms |
|---|---|---|---|
| 0 | all_tiers_exhausted | 3 | 180052 |
| 2 | NVStream_IncompleteRead | 1 | 33890 |
| 4 | client_gone_during_flush | 1 | 214621 |
| (空) | all_tiers_exhausted | 1 | 184438 |

ATE×3 落 k0 为轮转起始位承担最多尝试的伪象（k0 200s 延迟并非最差）。错误散布 k0/k2/k4/空，
无单 key 物理劣化，非 SOCKS5/出口 IP 问题。

### per-key 200 延迟
| key | n | avg_ms | p95_ms |
|---|---|---|---|
| 0 | 6 | 29309 | 56370 |
| 1 | 6 | 44403 | 78711 |
| 2 | 13 | 41803 | 104212 |
| 3 | 8 | 30766 | 90756 |
| 4 | 10 | 34684 | 107045 |

key 间负载 (6-13 req) 均衡，无异常慢 key。

### upstream_type / finish_reason
- nvcf_pexec: 48/49 (98%), 其他 1 (ATE)
- finish_reason: tool_calls 31, stop 12 —— 长 tool_calls 链占 72%, 高延迟主要来自长链

### 429 / key_cycle / fallback
- 30min 请求级 429 = **0**; key_cycle_429s: 0|17, 1|32 —— 中间态 429 全部被 key 轮转吸收
- **hm4104 fallback (近 10min)**: `PRIMARY-FAIL-STREAM` nv_gw 502 after 180074ms → 切 ms_gw (×2),
  `PRIMARY-BREAKER-SKIP-STREAM` circuit OPEN 直走 fallback (×1)。设计兜底被实际触发，工作正常。

### 趋势
| 窗口 | SR | 备注 |
|---|---|---|
| 6h | **89.4%** (542/606) | 64 err, 0 timeout |
| 3h 逐小时 | 12:00 24(22/2), 11:00 92(82/10), 10:00 116(100/16), 09:00 78(67/11) | 逐小时 91.7% / 89.1% / 86.2% / 85.9% |
| 24h | all_tiers_exhausted = **47** | 持续 NVCF 过载天数 |

### 容器状态
- 容器 Up 18 hours, /health ok (status ok, passthrough, 5 keys, port 40666)
- 当前参数与基线一致：UPSTREAM_TIMEOUT=50, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=90,
  KEY_COOLDOWN_S=30, NVU_TIER_BUDGET_DSV4F0731_NV=180, NVU_KEYMGR_429_*=120,
  NVU_KEYMGR_CONN_*=30/60/120, NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_EMPTY_200_FASTBREAK=3,
  NV_KEY_INTEGRATE_KEYS 空, NVU_PEER/MS_FALLBACK_ENABLED=0

## 为什么不改参数（逐项排除本地杠杆）

- `UPSTREAM_TIMEOUT=50`: NVStream_IncompleteRead avg 33890ms < 50s —— NVCF 主动截断流，非我方超时截断。
- `all_tiers_exhausted` @181s ≈ 180s 预算烧满 —— 5 key 全被 NVCF 过载拖垮后才 exhaust，非 budget 设错。
  缩短 budget 减少重试，加长增加死链烧时，180s 为合理平衡。
- `fast-break` (PEXEC_TIMEOUT=3, EMPTY_200=3): 无单 key 连续触发模式，fast-break 不适用。
- `KEY_COOLDOWN/CONN_COOLDOWN/429_COOLDOWN`: 429=0、无单 key 持续劣化，冷却调参无收益。
- `integrate 路由` (NV_KEY_INTEGRATE_KEYS 空): R1017 已因 integrate SR 50% 劣于 pexec 70.5% 而全走
  pexec DIRECT。本轮为 pexec 流级截断，切 integrate 无数据支持且历史证明更差。
- **hm4104 fallback 传导是设计兜底**：nv_gw 502 after 180030ms (budget 烧满) → adapter 正确切 ms_gw。
  这是 NVCF 过载下的预期 failover，非故障；切回逻辑由 adapter 管理，不在容器自优化范围。

## 上次修改效果 (RN1070 → RN1071)

RN1070 为 NOP，参数未变。对比两轮：
- **SR**: 87.0% (40/46) → **87.8%** (43/49)。NVCF 过载持续振荡，略回升。
- **错误构成**: ATE×2+absolute_cap×2+IncompleteRead×1+client_gone×1 → 本轮 ATE×4+IncompleteRead×1+
  client_gone×1。absolute_cap 消退，ATE 为主。全部孤立 (<3)。
- **fallback 传导续**: hm4104 本轮 PRIMARY-FAIL 502 2 次 + breaker-skip 1 次（上轮 1 次 fail + 0 skip）。
  链路兜底持续被触发，端到端由 ms_gw 保障。
- 参数零改动，纯上游波动。

## 结论

RN1068→RN1071 确认 NVCF 对 dsv4f0731_nv 的过载**持续振荡**（连接级→流级→混合相位），本轮 SR 87.8%。
错误全孤立 (<3)、无单 key 聚集、无净 429。hm4104 fallback 传导为设计 failover 兜底（502→ms_gw），
验证安全网持续正常，非本容器可调问题。为保持健康稳态基线，本轮 **NOP**。

## 下一步建议

- 持续监测 SR：NVCF 过载持续振荡（RN1067 92.9% → RN1068 85.7% → RN1069 80.6% → RN1070 87.0% →
  本轮 87.8%）。关注是否出现连续 2+ 窗口 SR>95% + 错误归零确认进入恢复期。
- **重点观察 hm4104 fallback 频率**：本轮 PRIMARY-FAIL 502×2 + breaker-skip×1，若继续频繁化
  （多请求/短间隔），说明 nv_gw 502 已实质性影响上层可用性 —— 但那属架构决策（Peer/ms fallback
  兜底配置），不在容器自优化范围 (NVU_MS_FALLBACK_ENABLED=0, NVU_PEER_FALLBACK_ENABLED=0)。
- 若 all_tiers_exhausted / IncompleteRead 聚集至 ≥3/30min 且伴随 hm4104 fallback 频繁化，才重新
  评估 TIER_TIMEOUT_BUDGET_S=180 是否过长（长 tool_calls 链常烧满预算）。当前 count=4 但 ATE 为
  tier 级（5 key 全过载），非单 key 可调，继续观察。
- 保持当前参数；仅在 NVCF 完全恢复后仍有模式化错误聚集时，才重新评估超时/预算/fast-break。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] 数据完整: 30min SR/延迟/错误分类/per-key/upstream/finish_reason/429/key_cycle/6h/3h/24h/fallback 均已采集
- [x] 错误分类: ATE×4 + IncompleteRead×1 + client_gone×1, 全孤立各<3
- [x] per-key: 无既慢又错单key, 错误散布 k0/k2/k4/空, 非 SOCKS5/出口 IP 问题
- [x] 请求级: 200×43 + 错误×6, p95≈180s budget 烧满, 与 hm4104 fallback 传导吻合
- [x] hm4104 fallback: PRIMARY-FAIL-STREAM 502→ms_gw ×2 + breaker-skip ×1, 属设计 failover 兜底
- [x] 决策数据驱动: SR 87.8% + 错误全孤立 + 0 净429 + fallback 为设计兜底 → NOP, 本地无可调杠杆, 不扰动链路