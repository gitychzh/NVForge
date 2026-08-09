# R1045: NVCF 过载复发 — SR 回落 (30min 80.3%, 6h 88.2%) + fallback 重启 — NOP (外部根因回归)

> 时间: 2026-08-09 16:50 UTC (R1044 15:04 后约 2h, 过载复发)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
> 状态: **NOP (无参数修改)** — 30min SR 80.3% (49/61), 较 R1044 (83.7%) **回落**; 6h SR 88.2% (518/587) 较 R1044 (93.2%) 明显回落;
> hm4104 fallback **再次触发** (PRIMARY-FAIL-STREAM 502 after 180s → ms_gw), R1044 的消退判断被证伪, 过载回归。
> Fallback: hm4104 近 5min 触发 fallback (nv_gw 502 after 180081ms → ms_gw 流式)

## 1. 背景 (改前必有数据)

R1044 曾观察到恢复轨迹 (30min SR 83.7%, 6h 93.2%, k0 延迟 41.3→17.3s, fallback 停止) 后判定"过载进入消退期"并 NOP。
本轮数据**证伪该判断** — 过载在约 2h 内回归, 各项指标回落至 R1043 的过载水平。conclusion: NVCF 过载为**周期性/潮汐性**, 非一次性消退。

### 30min 窗口 — nv_requests (tier_model='dsv4f0731_nv')
- 总量 61, 200=49, err=12, **SR=80.3%** (49/61) — 较 R1044 83.7% **回落**
- Avg/P50/P95/Max: 74238ms / 47148ms / 192962ms / 282092ms
  (avg 74s 为全 key 最高档, p95≈193s 仍顶满 TIER_TIMEOUT_BUDGET_S=180 附近 — 请求挂起烧 budget)
- 错误: `all_tiers_exhausted|6|162212`, `client_gone_during_flush|3|248103`, `NVStream_IncompleteRead|1|38595`,
  `buffer_exhausted|1|149047`, `stream_absolute_cap|1|165481`
- upstream: nvcf_pexec 59 (200=49, avg 68792), null 2 (200=0, avg 234896) — 全量 pexec, integrate 0
- finish_reason: tool_calls=39, stop=6, (null)=4
- 429: **0**, key_cycle_429s: **k0=27, k1=32** (k2=1, k3=1)

### 30min per-key 200 延迟
| key | n | avg_ok_ms | max_ok_ms |
|-----|---|-----------|-----------|
| 0   | 17| 56083     | 125222    |
| 1   | 9 | 37973     | 88119     |
| 2   | 12| 51031     | 128538    |
| 3   | 8 | 54671     | 92179     |
| 4   | 3 | 37647     | 52579     |

k0 承量 17 为全 key 最高 (负载倾斜), avg_ok 56.1s 为全 key 最高 — 过载排队下的延迟抬升。
**无单 key 代理劣化**: 各 key avg_ok 38-56s 均处过载高位, 无孤立异常 key。

### 30min per-key 错误
| key | error | count | avg_ms |
|-----|-------|-------|--------|
| 0   | all_tiers_exhausted | 4 | 125870 |
| (null) | all_tiers_exhausted | 2 | 234896 |
| 4   | client_gone_during_flush | 2 | 227162 |
| 3   | stream_absolute_cap | 1 | 165481 |
| 3   | client_gone_during_flush | 1 | 289985 |
| 3   | buffer_exhausted | 1 | 149047 |
| 0   | NVStream_IncompleteRead | 1 | 38595 |

all_tiers_exhausted 6 次为 **tier 级**错误 (整 tier 循环烧满 budget), 归属 k0/null 为轮转伪象。
k3 集中 3 种流错误 (stream_absolute_cap 165s + client_gone 290s + buffer_exhausted 149s) — 上游流截断/缓冲耗尽,
过载残余, 非 key 冷却问题 (无 429 最终态, key_cycle 低)。

### 6h / 3h / 24h 趋势
- **6h: 587 总, 518 ok, SR=88.2%** (较 R1044 6h 93.2% **明显回落**), 69 err, 0 429
- 3h 逐小时: 08:00=83/103(80.6%), 07:00=63/77(81.8%), 06:00=100/111(90.1%), 05:00=12/13(92.3%)
  → **清晰下降轨迹**: 05:00=92% → 06:00=90% → 07:00=82% → 08:00=81%, 过载在近 3h 内逐步加深。
- **24h all_tiers_exhausted: 129** (较 R1044 的 117 累积, 过载复发加深)

### Fallback 日志 (hm4104, 最近 5min)
- **触发 fallback**: `PRIMARY-FAIL-STREAM nv_gw 流式 server_5xx status=502 after 180081ms 切 fallback`
  + `FALLBACK-STREAM 从 primary 切到 ms_gw 流式`。主链路 nv_gw 502 (180s=budget 烧满后), hm4104 走 ms_gw 兜底。
  与 R1044 (fallback 停止) 相反, 主链路确定性恶化证据回归。

## 2. 决策: NOP (无参数修改) — 根因仍为 NVCF 上游过载周期性复发, 无参数可干净归因

**依据:**
1. **Root cause 与 R1041-R1043 同源且周期性复发**: 表现形态为 all_tiers_exhausted (tier 级 budget 烧满 162s)
   + client_gone_during_flush (248s) + stream_absolute_cap (165s) + buffer_exhausted (149s) + 显式 502 (180s),
   均为**过载下请求挂起/流被上游截断**的结果, 非本容器 env/SOCKS5/超时配置可解。
   R1044 的消退仅是过载潮汐的低谷, 本轮回归证实其周期性。
2. **all_tiers_exhausted=6 是过载结果非 budget 配置问题**: 错误耗时 125-162s 靠近 TIER_TIMEOUT_BUDGET_S=180。
   过载时每 key 需长时推理/排队才失败, 5 key 循环烧满 budget → ATE。**缩短 budget 会让更多请求过早 fail,
   拉长会让更多请求在死连接上空耗** — 均非正解。当前 180s 为合理平衡。
3. **无单 key 紧迫劣化**: k0 承重 (4/6 ATE + 1 IncompleteRead) 因其承量最高 (17 请求), 且 avg_ok 56.1s 非孤立
   异常 (k2/k3 同处 51-55s 过载高位); k3 的 3 种流错误为过载残余流截断, 非 key 冷却/代理故障。
   **key_cycle_429s 不对称 (k0=27, k1=32 vs k2=1, k3=1)** 需关注, 但最终 429=0, 为过载期 key 循环中偶遇
   429 的计数, 非确定性 key 故障, 不足以支撑冷却参数改动。
4. **一次只改一个参数 / 不扰动**: 外部上游过载复发, 无干净参数归因目标。调整 UPSTREAM_TIMEOUT / 冷却 / 预算
   均无法改变 NVCF 容量, 属"瞎调", 违反铁律。NOP 最稳。
5. **端到端可用性由 fallback 保障**: hm4104 已正确显式 fail (502 after 180s) + 切 ms_gw 流式, 端到端降级但可用。
   本容器无需干预即可由 fallback 兜底。

当前 env (已 docker exec 复核, 全部维持): UPSTREAM_TIMEOUT=45, TIER_TIMEOUT_BUDGET_S=180,
NVU_TIER_BUDGET_DSV4F0731_NV=180, KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90,
NVU_KEYMGR_429_BASE/MAX_COOLDOWN=120, NVU_KEYMGR_CONN_BASE=30/MAX=60/FAIL_THRESHOLD=3/LONG=120,
NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_EMPTY_200_FASTBREAK=3。**无改动。**

## 3. 当前状态 (30min 主指标 + 6h 趋势)

- 30min SR: **80.3%** (49/61) / **6h SR: 88.2%** (518/587)
- Avg/P50/P95: 74238ms / 47148ms / 192962ms
- 错误 (30min): `all_tiers_exhausted` 6 (162s), `client_gone_during_flush` 3 (248s), `NVStream_IncompleteRead` 1
  (39s), `buffer_exhausted` 1 (149s), `stream_absolute_cap` 1 (165s)
- 429: 0 (key_cycle_429s: k0=27, k1=32 — 过载期 key 循环偶遇数, 无最终 429)
- upstream: pexec 59 (200=49, avg 68.8s), integrate 0
- fallback: **已触发** (hm4104 PRIMARY-FAIL-STREAM 502 after 180s → ms_gw 流式)

## 4. 上次修改效果 (R1044 NOP → 本轮)

- **SR 回落**: 30min 83.7% → **80.3%**; 6h 93.2% → **88.2%** — R1044 恢复判断被证伪, 过载周期性回归。
- **fallback 重启**: R1044 无 fallback → 本轮 **PRIMARY-FAIL-STREAM 502 after 180s → ms_gw** — 主链路再度劣化。
- **延迟抬升**: R1044 avg 63.5s → **74.2s**, p50 31.1s → **47.1s** — 过载排队延迟加深。
- **错误形态扩展**: R1044 为 ATE(5)+IncompleteRead(1)+client_gone(1), 本轮 ATE(6)+client_gone(3)+IncompleteRead(1)
  +buffer_exhausted(1)+stream_absolute_cap(1) — 过载从"单一挂起"扩展为"挂起+流截断+缓冲耗尽"多形态。
- **24h ATE**: 117 → **129** (累积加深)。

## 5. 下一步建议

1. **本轮 NOP, 等待 NVCF 过载潮汐退去**: 定时器周期性 (R1044 低谷 → 本轮高峰) 表明 NVCF 容量为潮汐性,
   非本容器可调。下轮若 SR 回升至 ≥90% 且 fallback 停止, 判定进入低谷期。
2. **持续监测 fallback**: hm4104 fallback 是否持续触发是端到端主链路可用性的最强信号。若 502 after 180s
   持续, 说明 NVCF 深度过载; 若停止, 判定退潮。
3. **过载低谷期复核 key_cycle_429s 不对称 (k0=27, k1=32)**: 若在 SR≥90% 且 429 终态仍为 0 时 k0/k1
   key_cycle_429s 持续高, 需评估是否 k0/k1 特定 IP 被 NVCF 边缘限流, 再决定是否调整 NVU_KEYMGR_429_COOLDOWN
   或 key 分配。但**非过载期不轻易动**。
4. **下轮重点**: (a) 30min SR 是否回升 ≥90%, (b) all_tiers_exhausted 是否降至 ≤2, (c) fallback 是否停止,
   (d) key_cycle_429s 不对称是否在健康期消失。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] 数据完整: 30min/6h/3h/24h/per-key/fallback 均已采集
- [x] 错误深度: all_tiers_exhausted 6 (162s=budget 烧满) + client_gone 3 (248s) + IncompleteRead 1 + buffer_exhausted
  1 + stream_absolute_cap 1, 429=0, 均过载结果非配置因素
- [x] k0 错误集中 (4/6 ATE) 判定为收量倾斜伪象 (承量 17 全 key 最高, avg_ok 56s 非孤立), 非 key 劣化
- [x] 下行轨迹: 逐时 92%→90%→82%→81%, 6h SR 93.2%→88.2%, fallback 重启, 过载周期性回归
- [x] 决策数据驱动: NVCF 上游过载复发, 无参数可干净归因 → NOP, 不扰动配置