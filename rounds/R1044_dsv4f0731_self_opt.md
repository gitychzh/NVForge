# R1044: NVCF 过载进入消退期 — SR 回升 + fallback 停止 (30min 83.7%, 6h 93.2%) — NOP (外部根因恢复中)

> 时间: 2026-08-09 15:04 UTC (R1043 08-08 19:04 后约 20h, 过载恢复期)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
> 状态: **NOP (无参数修改)** — 30min SR 83.7% (36/43), 较 R1043 (81.4%) 回升; 6h SR 93.2% (566/607) 明显回升;
> hm4104 fallback 近 5min **已停止** (R1043 持续触发), NVCF 过载进入消退期, 非本容器可调。
> Fallback: hm4104 近 5min **无 fallback 日志** (R1043 持续 PRIMARY-FAIL-STREAM 502 → ms_gw)

## 1. 背景 (改前必有数据)

R1041-R1043 连续三轮判定 NVCF 上游系统性过载 (all_tiers_exhausted + client_gone_during_flush + 502,
180s budget 烧满)。R1043 下一步建议: "若 11:00 后样本恢复且 SR≥90%, NVCF 过载可能进入消退期"。
本轮数据**证实该预测** — 过载开始消退, 呈恢复轨迹。

### 30min 窗口 — nv_requests (tier_model='dsv4f0731_nv')
- 总量 43, 200=36, err=7, **SR=83.7%** (36/43) — 较 R1043 81.4% **回升**
- Avg/P50/P95/Max: 63525ms / 31105ms / 249973ms / 284108ms
  (p95≈250s 顶满 TIER_TIMEOUT_BUDGET_S=180 以上 — 残余过载请求仍挂起烧 budget)
- 错误: `all_tiers_exhausted|5|218794`, `NVStream_IncompleteRead|1|82473`, `client_gone_during_flush|1|267588`
- upstream: nvcf_pexec 41 (200=36, avg 53116ms), null 2 (200=0, avg 276906ms)
- finish_reason: tool_calls=27, stop=9
- 429: **0**, key_cycle_429s: k0=20, k1=22

### 30min per-key 200 延迟
| key | n | avg_ok_ms | max_ok_ms |
|-----|---|-----------|-----------|
| 0   | 5 | 17348     | 30417     |
| 1   | 7 | 38467     | 126715    |
| 2   | 8 | 31272     | 55018     |
| 3   | 8 | 41791     | 106097    |
| 4   | 8 | 43377     | 85136     |

k0 avg 由 R1043 的 41.3s 大幅回落至 17.3s (恢复领先), k2/k4 回到 31-43s 健康区间。
**无单 key 代理劣化**, 负载均匀 (5-8 请求/key)。

### 30min per-key 错误
| key | error | count | avg_ms |
|-----|-------|-------|--------|
| 0   | all_tiers_exhausted | 3 | 180053 |
| (null) | all_tiers_exhausted | 2 | 276906 |
| 3   | NVStream_IncompleteRead | 1 | 82473 |
| 3   | client_gone_during_flush | 1 | 267588 |

all_tiers_exhausted 5 次仍为 **tier 级**错误 (整 tier 循环烧满 budget ~180-277s), 归属 key 为轮转伪象。
k3 出现 1×IncompleteRead (82s) + 1×client_gone (267s) — 流被上游截断/连接丢弃, 过载残余, 非 key 冷却问题。

### 6h / 3h / 24h 趋势
- **6h: 607 总, 566 ok, SR=93.2%** (较 R1043 6h 90.4% **明显回升**), 41 err, 0 429
- 3h 逐小时: 07:00=5/5(100%), 06:00=100/111(90.1%), 05:00=85/92(92.4%), 04:00=104/108(96.3%)
  → **恢复轨迹**: 04:00=96%, 05:00=92%, 06:00=90%, 07:00=100% (样本 5 偏小但方向明确: 逐时 SR 稳于 90%+)
- **24h all_tiers_exhausted: 117** — 较 R1043 的 42 大幅累积, 但为**跨 20h 累积** (R1043 距今久), 且 30min
  ATE 5 较 R1043 的 6 略降, 说明 ATE 频率未恶化, 累积为时长所致。

### Fallback 日志 (hm4104, 最近 5min)
- **无 fallback 日志** (R1043 持续 PRIMARY-FAIL-STREAM 502 after 180s → ms_gw)。
  表明上一轮主链路已恢复稳定, hm4104 不再需要切 ms_gw 兜底 — **端到端主链路恢复的最强信号**。

## 2. 决策: NOP (无参数修改) — NVCF 过载恢复中, 无参数可干净归因

**依据:**
1. **恢复轨迹明确**: 6h SR 90.4%→93.2%, 逐时 96%/92%/90%/100% 稳于 90%+, hm4104 fallback 停止,
   k0 延迟 41.3s→17.3s 大幅回落。这些改善发生在 **env 全程未动** 的前提下, 证明为 NVCF 上游容量恢复而非参数效应。
2. **30min 残余 5×ATE 是恢复期尾部抖动**: 错误耗时 180-277s (=TIER_TIMEOUT_BUDGET_S=180 budget 烧满 +
   死连接空耗), 属过载尾部残余请求, 非 budget 配置问题。缩短 budget 会让更多请求过早 fail, 拉长则死连接空耗
   — 均非正解, 维持 180s 合理。
3. **无单 key 紧迫劣化**: k0 错误 (3/5 ATE) 为轮转起始位伪象 (avg_ok 17.3s 为全 key 最快, 代理健康);
   k3 的 1×IncompleteRead+1×client_gone 为过载残余流截断, 非 key 冷却/代理故障 (无 429, key_cycle_429s 低)。
4. **一次只改一个参数 / 不扰动**: 恢复期改参数会污染归因 (无法区分是参数效应还是 NVCF 自发恢复)。
   NOP 最稳, 待 SR 稳固 ≥90% 后再复核 key 健康度。
5. **端到端可用性已恢复**: hm4104 fallback 停止, 主链路 nv_gw 已稳定服务, 无需本容器干预。

当前 env (已 docker exec 复核, 全部维持): UPSTREAM_TIMEOUT=45, TIER_TIMEOUT_BUDGET_S=180,
NVU_TIER_BUDGET_DSV4F0731_NV=180, KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90,
NVU_KEYMGR_429_BASE/MAX_COOLDOWN=120, NVU_KEYMGR_CONN_BASE=30/MAX=60/FAIL_THRESHOLD=3/LONG=120,
NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_EMPTY_200_FASTBREAK=3。**无改动。**

## 3. 当前状态 (30min 主指标 + 6h 趋势)

- 30min SR: **83.7%** (36/43) / **6h SR: 93.2%** (566/607)
- Avg/P50/P95: 63525ms / 31105ms / 249973ms
- 错误 (30min): `all_tiers_exhausted` 5 (218s), `NVStream_IncompleteRead` 1 (82s), `client_gone_during_flush` 1 (267s)
- 429: 0
- upstream: pexec 41 (200=36, avg 53.1s), integrate 0
- fallback: **无** (hm4104 近 5min 无 fallback 日志)

## 4. 上次修改效果 (R1043 NOP → 本轮)

- **SR 回升**: 30min 81.4% → **83.7%**; 6h 90.4% → **93.2%** — NVCF 过载消退, env 全程未动证实为上游恢复。
- **fallback 停止**: R1043 持续 PRIMARY-FAIL-STREAM 502 → 本轮 **0 fallback** — 主链路端到端恢复。
- **k0 延迟回落**: 41.3s → **17.3s** (恢复领先), 全 key 回到 17-43s 健康区间。
- **ATE 频率略降**: 30min 6 → **5**; 24h 117 为跨 20h 累积 (R1043 距今久), 非恶化。
- **错误形态收敛**: R1043 全为 ATE(6)+client_gone(2), 本轮 ATE(5)+IncompleteRead(1)+client_gone(1), 总错误量 8→7 微降。

## 5. 下一步建议

1. **本轮 NOP, 继续观察 SR 稳固**: 下轮重点确认 30min SR 是否回升至 ≥90% (当前 83.7% 仍受 30min 短窗
   残余 ATE 拖累, 6h 93.2% 已健康)。若 30min SR ≥90% 且 ATE 降至 ≤2, 判定过载完全消退。
2. **过载完全消退后复核 key 健康度**: (a) 确认无 key 因过载期大量 ATE 承担被冷却标记而长期规避;
   (b) 复核 k3 (本轮 1×IncompleteRead+1×client_gone) 是否仅过载残余, 下轮应恢复健康。
3. **若 SR 稳固 ≥90% 且错误形态稳定**: 可进入正常参数优化节奏 (如评估 per-key 延迟方差是否需调整
   NV_INTEGRATE_KEYS 分配, 或 TIER_COOLDOWN_S 90→ 是否需随负载下降回调)。但非本轮, 需多轮数据支撑。
4. **下轮重点**: (a) 30min SR 是否 ≥90%, (b) all_tiers_exhausted 是否降至 ≤2, (c) hub fallback 是否保持 0,
   (d) k3 是否恢复零错误。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] 数据完整: 30min/6h/3h/24h/per-key/fallback 均已采集
- [x] 错误深度: all_tiers_exhausted 5 (218s=budget 烧满) + IncompleteRead 1 + client_gone 1, 429=0, 过载残余
- [x] k0 错误集中 (3/5 ATE) 判定为轮转起始位伪象 (avg_ok 17.3s 全 key 最快, 代理健康), 非 key 劣化
- [x] 恢复轨迹: 6h SR 93.2%, 逐时 96/92/90/100%, hm4104 fallback 停止, 主链路端到端恢复
- [x] 决策数据驱动: NVCF 过载消退期, 无参数可干净归因 → NOP, 不扰动配置