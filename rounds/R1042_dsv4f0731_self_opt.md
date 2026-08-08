# R1042: NVCF 过载持续恶化 (SR 82.9%, all_tiers_exhausted 频发, hm4104 fallback 加深) — NOP (外部根因)

> 时间: 2026-08-08 17:10 UTC (紧接 R1041 16:50, 过载事件持续)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
> 状态: **NOP (无参数修改)** — 30min SR 82.9% (29/35), 较 R1041 (92.6%) 进一步恶化, 为 NVCF 上游过载持续, 非本容器可调
> Fallback: hm4104 近 5min **触发 fallback** (PRIMARY-FAIL-STREAM 502 + breaker-skip → ms_gw)

## 1. 背景 (改前必有数据)

R1041 判定 NVCF 上游系统性过载 (529_nv_overloaded + RemoteDisconnected + Timeout 全 5 key 均等) 后 NOP。
16 分钟后 (本轮) 过载事件**持续且恶化**: 30min SR 跌破 90% (82.9%), all_tiers_exhausted 频发,
hm4104 fallback 加深 (出现显式 PRIMARY-FAIL-STREAM 502)。

### 30min 窗口 — nv_requests (tier_model='dsv4f0731_nv')
- 总量 35, 200=29, err=6, **SR=82.9%** (29/35)
- Avg/P50/P95/Max: 68912ms / 36430ms / 180043ms / 248333ms
  (延迟显著抬升: p95=180s 恰好顶满 TIER_TIMEOUT_BUDGET_S=180, p50=36.4s — 过载下请求普遍挂起)
- 错误: `all_tiers_exhausted|3|178386`, `stream_absolute_cap|2|165260`,
  `client_gone_during_flush|1|283501`
- upstream: nvcf_pexec 全部 (35/35), integrate 0
- finish_reason: tool_calls=26, stop=3
- 429: **0**, key_cycle_429s: k0=11, k1=20, k2=2, k3=1, k4=1

### 30min per-key 200 延迟
| key | n | avg_ok_ms | max_ok_ms |
|-----|---|-----------|-----------|
| 0   | 4 | 16522     | 32513     |
| 1   | 5 | 57251     | 111277    |
| 2   | 5 | 16716     | 30522     |
| 3   | 9 | 55048     | 124158    |
| 4   | 6 | 55233     | 110968    |

两簇延迟 (16.5-16.7s vs 55.0-57.3s): k0/k2 正常快, k1/k3/k4 慢 (过载排队)。**无单 key 代理劣化** —
慢 key 的 max 达 110-124s, 属 NVCF 过载下长时推理/排队, 非 SOCKS5 故障。

### 30min per-key 错误
| key | error | count | avg_ms |
|-----|-------|-------|--------|
| 0   | all_tiers_exhausted | 3 | 178386 |
| 0   | stream_absolute_cap | 1 | 177350 |
| 2   | client_gone_during_flush | 1 | 283501 |
| 3   | stream_absolute_cap | 1 | 153170 |

k0 承载 4/6 错误 (3 all_tiers + 1 stream_cap), 但 k0 avg_ok=16.5s 为全 key 最低 — **k0 是因 key 轮转起始位
被尝试最多**, 过载下消耗最多 budget 而触发 all_tiers_exhausted 的出口 key, 非 k0 代理劣化。all_tiers_exhausted
为 **tier 级**错误 (整 tier 循环烧满 budget), 归属 k0 仅因它是末次尝试 key。

### 6h / 3h / 24h 趋势
- **6h: 741 总, 701 ok, SR=94.6%**, 40 err, 0 429
- 3h 逐小时: 09:00=1/2(50%), 08:00=96/104(92.3%), 07:00=88/96(91.7%), 06:00=87/95(91.6%)
  → 自 05:00 起连续 6h SR<95%, 过载持续。09:00 窗口样本少 (2 请求) 不具统计意义。
- **24h all_tiers_exhausted: 28** (中长累积, 过载期间逐量累积)

### Fallback 日志 (hm4104, 最近 5min)
- **触发 fallback 加深**: `PRIMARY-FAIL-STREAM nv_gw 流式 server_5xx status=502 after 175069ms 切 fallback`
  + `PRIMARY-BREAKER-SKIP-STREAM (circuit OPEN)` + `FALLBACK-STREAM 切 ms_gw` 多次。
  nv_gw 主链路 502 且 circuit 打开, hm4104 已深度切 ms_gw 兜底。

## 2. 决策: NOP (无参数修改) — 根因仍为 NVCF 上游过载, 且无参数可干净归因

**依据:**
1. **Root cause 与 R1041 同源且更明确**: R1041 已证 529_nv_overloaded + RemoteDisconnected(68) + Timeout(31)
   全 5 key 均等 = NVCF 后端容量问题。本轮该事件持续, 表现形态转为 all_tiers_exhausted +
   stream_absolute_cap (165-178s) + 502 (175s), 均为**过载下请求挂起/连接被上游丢弃**的结果, 非本容器
   env/SOCKS5/超时配置可解。
2. **all_tiers_exhausted=3 是过载结果非 budget 配置问题**: 错误耗时 178s 恰好 = TIER_TIMEOUT_BUDGET_S=180。
   过载时每 key 需 35-50s 才失败, 5 key 循环烧满 budget → ATE。**缩短 budget 会让更多请求过早 fail,
   拉长会让更多请求在死连接上空耗** — 均非正解。当前 180s 为合理平衡。
3. **k0 错误集中是轮转伪象, 非 key 劣化**: 铁律要求"改前必有数据", ��数据支撑 k0 被冷却标记或移出
   轮转。k0 avg_ok=16.5s (最低) 明确证明 k0 代理健康; 其 4 错误全为 tier 级 (ATE) + 过载流截断, 由
   轮转起始位承担最多尝试所致。
4. **一次只改一个参数 / 不扰动**: 当前为外部上游过载, 无干净参数归因目标。调整 UPSTREAM_TIMEOUT /
   冷却/预算均无法改变 NVCF 容量, 属"瞎调", 违反铁律。NOP 最稳。
5. **端到端可用性由 fallback 保障**: hm4104 已正确显式 fail (502) + circuit-open 直走 ms_gw, 端到端
   降级但可用。本容器无需干预即可由 fallback 兜底。

当前 env (已 docker exec 复核, 全部维持): UPSTREAM_TIMEOUT=50, TIER_TIMEOUT_BUDGET_S=180,
NVU_TIER_BUDGET_DSV4F0731_NV=180, KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90,
NVU_KEYMGR_429_BASE/MAX_COOLDOWN=120, NVU_KEYMGR_CONN_BASE=30/MAX=60/FAIL_THRESHOLD=3/LONG=120,
NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_EMPTY_200_FASTBREAK=3。**无改动。**

## 3. 当前状态 (30min 主指标 + 6h 趋势)

- 30min SR: **82.9%** (29/35) / **6h SR: 94.6%** (701/741)
- Avg/P50/P95: 68912ms / 36430ms / 180043ms
- 错误 (30min): `all_tiers_exhausted` 3 (178s), `stream_absolute_cap` 2 (165s), `client_gone_during_flush` 1 (283s)
- 429: 0
- upstream: pexec 全部 (35/35), integrate 0
- fallback: **触发且加深** (hm4104 PRIMARY-FAIL-STREAM 502 + breaker-skip → ms_gw)

## 4. 上次修改效果 (R1041 NOP → 本轮)

- **SR 再度下滑**: 92.6% (R1041) → **82.9%** (本轮) — NVCF 过载**持续且恶化**, 非参数退化 (env 全程未动),
  是上游环境劣化延续。
- **错误形态变化**: R1041 为 RemoteDisconnected/Timeout/529 (tier_attempts 层), 本轮转 nv_requests 层
  all_tiers_exhausted + stream_absolute_cap + 502 — 过载从"连接抖动"深化为"请求挂起烧 budget + 显式 502"。
- **fallback 加深**: R1041 为 content_filter zombie + breaker-skip, 本轮新增显式 `server_5xx 502 after 175s`
  → 主链路确定性恶化的证据更强。
- **429 仍 0**: 无 rate-limit/key 冷却问题, 排除本地 key 管理因素。

## 5. 下一步建议

1. **本轮 NOP, 继续等待 NVCF 过载消退**: 外部上游过载, 非本容器可调。下轮若 SR 回暖 ≥95% 且
   ATE/502 消退, 维持现状即可。
2. **若过载持续 ≥6h (合计) 且 SR<90%**: 才评估降级干预 — 将部分流量引向 integrate lane
   (NV_INTEGRATE_KEYS) 作为 pexec 过载时的冗余, 或进一步依赖 hm4104 ms_gw fallback (当前已深度兜底)。
   但 integrate 路由属架构级变更, 需多轮数据支撑, 且当前 integrate egress IP 池 (134.195.x) 与 pexec
   直连未必缓解 NVCF 容量瓶颈, 不急于本轮。
3. **下轮重点**: 观察 (a) all_tiers_exhausted 是否仍逐时 5-6 次, (b) 502/stream_absolute_cap 是否持续,
   (c) 09:00 后样本量恢复后 SR 是否仍在 90% 下。若持续, 记录为持续 NVCF 过载事件, 不归因于本容器参数。
4. **过载消退后复核**: 5 key 负载/延迟回到健康均匀态; 确认无 key 因过载期大量错误被冷却标记而长期规避
   (重点复核 k0, 因本轮它在轮转起始位承担最多 ATE 出口)。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] 数据完整: 30min/6h/3h/24h/per-key/fallback 均已采集
- [x] 错误深度: all_tiers_exhausted 3 (178s=budget 烧满) + stream_absolute_cap 2 (165s) + client_gone 1 (283s),
      429=0, 均过载结果非配置因素
- [x] k0 错误集中 (4/6) 判定为轮转起始位伪象 (avg_ok 16.5s 最低, 代理健康), 非 key 劣化
- [x] hm4104 fallback 加深 (PRIMARY-FAIL-STREAM 502 after 175s + breaker-skip → ms_gw), 端到端由 fallback 兜底
- [x] 决策数据驱动: NVCF 上游过载持续恶化, 无参数可干净归因 → NOP, 不扰动配置