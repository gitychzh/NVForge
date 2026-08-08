# R1041: NVCF 后端系统性过载 (all 5 keys RemoteDisconnected/Timeout/529), hm4104 fallback 触发 — NOP (外部根因)

> 时间: 2026-08-08 16:50 UTC
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
> 状态: **NOP (无参数修改)** — 30min SR 92.6% (50/54), 但为 **NVCF 后端系统性过载**所致, 非本容器可调 env 可解
> Fallback: hm4104 近 5min **触发 fallback** (content_filter zombie + breaker-skip → ms_gw)

## 1. 背景 (改前必有数据)

多轮健康稳态后 (R1030-R1040 曾连续 100%/98%+ SR), 本轮 30min 窗口 SR 跌至 **92.6%** (50/54),
且 hm4104 fallback 日志显示 nv_gw→ms_gw 降级。需判定根因: 是容器参数问题, 还是 NVCF 上游过载。

### 30min 窗口 — nv_requests
- 总量 54, 200=50, err=4, **SR=92.6%** (50/54)
- Avg/P50/P95/Max: 49486ms / 25747ms / 161298ms / 228680ms (延迟显著抬升, p95 161s 属 pexec 长尾 + 过载)
- 错误: `all_tiers_exhausted|2|178229`, `client_gone_during_flush|1|283501`,
  `stream_absolute_cap|1|153170`
- upstream: nvcf_pexec 全部 (54/54), integrate 0
- finish_reason: tool_calls=39, stop=11
- 429: **0**, key_cycle_429s: k0=18, k1=32, k2=3, k3=1 (轮转计数)

### 2h tier_attempts — 根因定位
| error_type | count | avg_ms |
|---|---|---|
| pexec_success | 114 | 16800 |
| **NVCFPexecRemoteDisconnected** | **68** | 35685 |
| **NVCFPexecTimeout** | **31** | 43486 |
| **529_nv_overloaded** | **6** | — |
| budget_exhausted_after_connect | 1 | 2076 |

**All 5 keys 均等受影响** (2h 窗口):
| key | RemoteDisconnected | Timeout | 529 |
|-----|-----|-----|-----|
| 0 | 10 | 9 | 0 |
| 1 | 13 | 4 | 1 |
| 2 | 17 | 4 | 1 |
| 3 | 11 | 7 | 2 |
| 4 | 14 | 5 | 1 |

**无单 key 劣化** — 各 key 错误量 (17-21) 与延迟 (28.5-51.2s) 完全均等分布。系统性 NVCF 上游问题。

### 逐分钟错误分布 (1h)
RemoteDisconnected/Timeout 散落在 08:28-08:51 各分钟 (峰值 08:51=6), 非固定单 key 或固定时间点突发,
符合**持续上游过载**特征而非单 key 代理故障。

### 6h / 24h 趋势 — 持续 4h 下滑
- **6h: 775 总, 738 ok, SR=95.2%**, 37 err, 0 429
- 24h all_tiers_exhausted: 27
- 3h 逐小时 (SR 持续低于 95%): 06:00=103/111(92.8%), 07:00=88/96(91.7%), 08:00=82/88(93.2%)
- 12h 逐小时: 04:00=142/145, 05:00=128/137, 06:00=103/111, 07:00=88/96, 08:00=90/97 —
  **自 05:00 起连续 4 小时 SR<95%**, 且 06:00 起 all_tiers_exhausted 逐小时 5-6 次频发。

### Fallback 日志 (hm4104, 最近 5min)
- **触发 fallback**: "content_filter 流中检测 (R840 zombie)" + "PRIMARY-BREAKER-SKIP-STREAM (circuit OPEN 或冷却)" +
  "从 primary 切到 ms_gw 流式" 多次。nv_gw 主链路降级, hm4104 已切 ms_gw。

## 2. 决策: NOP (无参数修改) — 根因为 NVCF 后端系统性过载

**依据:**
1. **Root cause 明确为 NVCF 上游过载, 非本容器可调**: `529_nv_overloaded` (显式 NVCF 过载信号) +
   `NVCFPexecRemoteDisconnected` (68, 连接中途被上游丢弃) + `NVCFPexecTimeout` (31) 全部均等散布于
   **5 个 key**。若为容器 env/超时/SOCKS5 代理问题, 应表现为单 key 或单类错误集中; 实际为全 key 全覆盖的
   上游连接抖动, 属 NVCF 后端容量/稳定性问题。
2. **改前必有数据**: 无任何参数改动有数据支撑可归因于此。改变 UPSTREAM_TIMEOUT / TIER_TIMEOUT_BUDGET /
   冷却参数均无法解决 NVCF 自身过载 (529 是 NVCF 显式拒绝, 本地超时微调只会让请求在死连接上多等/少等,
   不改变 NVCF 容量)。
3. **一次只改一个参数**: 当前异常为外部偶发, 无干净的参数归因目标。贸然调参 (如 UPSTREAM_TIMEOUT 50→60
   或 KEY_COOLDOWN 30→60) 属"瞎调", 违反铁律, 且可能在高过载期放大 budget 浪费。
4. **all_tiers_exhausted 频发 (2/30min, 5-6/h)**: 因 NVCF 过载时每 key 需 35-50s 才失败, 5 key 循环
   恰好烧满 180s budget。这是过载的**结果**而非 budget 配置问题。缩短 budget 只会让更多请求过早 fail,
   拉长会让更多请求在死连接上空耗 — 均非正解。
5. **NOP 最稳**: 保留现有参数直至 NVCF 过载消退, 待数据回暖再评估。hm4104 已正确 fallback 到 ms_gw,
   端到端可用性由 fallback 保障, 无需本容器干预。

当前 env (已 docker exec 复核, 全部维持): UPSTREAM_TIMEOUT=50, TIER_TIMEOUT_BUDGET_S=180,
NVU_TIER_BUDGET_DSV4F0731_NV=180, KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90,
NVU_KEYMGR_429_BASE/MAX_COOLDOWN=120, NVU_KEYMGR_CONN_BASE=30/MAX=60/FAIL_THRESHOLD=3/LONG=120,
NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_EMPTY_200_FASTBREAK=3。**无改动。**

## 3. 当前状态 (30min 主指标 + 6h 趋势)

- 30min SR: **92.6%** (50/54) / **6h SR: 95.2%** (738/775)
- Avg/P50/P95: 49486ms / 25747ms / 161298ms
- 错误 (30min): `all_tiers_exhausted` 2 (178s), `client_gone_during_flush` 1 (283s), `stream_absolute_cap` 1 (153s)
- 429: 0 (但 2h 有 6× `529_nv_overloaded` — NVCF 显式过载)
- upstream: pexec 全部 (54/54), integrate 0
- fallback: **触发** (hm4104 已切 ms_gw, content_filter zombie + breaker-skip)

## 4. 上次修改效果 (R1040 NOP → 本轮)

- **SR 骤降**: 98.48% (R1040, 单次 NVStream_IncompleteRead) → **92.6%** (本轮) — 但病因从单次瞬态
  转为系统性 NVCF 过载 (多类错误 + 529 + 全 key 覆盖), 非参数退化, 是上游环境变化。
- **fallback 由 0 → 触发**: 多轮 0 fallback 后本轮 hm4104 切 ms_gw。nv_gw 链路健康度下降, 由 fallback 兜底。
- **延迟抬升**: avg 26.1s → 49.5s, p50 18.4s → 25.7s — 反映 NVCF 过载下响应变慢。
- **429 仍 0**: 无 rate-limit 问题, 进一步排除本地 key 冷却/429 配置因素。

## 5. 下一步建议

1. **本轮 NOP, 等待 NVCF 过载消退**: 这是外部上游过载, 非本容器可调。下轮若 SR 回暖至 ≥95% 且
   529/RemoteDisconnected 消退, 维持现状即可。
2. **若过载持续 ≥6h 且 SR<90%**: 才考虑降级干预 — 例如评估将部分流量引向 integrate lane
   (NV_INTEGRATE_KEYS) 或依赖 hm4104 的 ms_gw fallback 兜底 (当前已生效)。但修改 integrate 路由属
   **架构级变更**, 需多轮数据支撑, 不应急于本轮。
3. **下轮重点**: 观察 all_tiers_exhausted 是否仍逐小时 5-6 次, 及 529_nv_overloaded 是否持续。
   若持续, 记录为 NVCF 上游过载事件, 不归因于本容器参数。
4. **可在 NVCF 过载消退后**: 复核 5 key 负载是否回到均匀健康态; 确认无单 key 因本轮大量错误被
   冷却标记而长期规避。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] 数据完整: 30min/2h tier_attempts/6h/12h/24h/fallback 均已采集
- [x] 根因定位: 2h 窗口 RemoteDisconnected=68 + Timeout=31 + 529=6, 全 5 key 均等, 系统性 NVCF 过载
- [x] 12h 逐小时: 05:00 起连续 4h SR<95%, 06:00 起 all_tiers_exhausted 逐小时 5-6 次 (过载结果非根因)
- [x] hm4104 fallback 已触发 (content_filter zombie + breaker-skip → ms_gw), 端到端由 fallback 兜底
- [x] 决策数据驱动: 外部上游过载, 无参数可干净归因 → NOP, 不扰动配置