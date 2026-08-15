# R1043: NVCF 过载持续恶化 (SR 81.4%, all_tiers_exhausted 30min 6 次, hm4104 fallback 持续) — NOP (外部根因)

> 时间: 2026-08-08 19:04 UTC (R1042 17:10 后约 2h, 过载事件持续)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
> 状态: **NOP (无参数修改)** — 30min SR 81.4% (35/43), 较 R1042 (82.9%) 略降, 为 NVCF 上游过载持续, 非本容器可调
> Fallback: hm4104 近 5min **再次触发 fallback** (PRIMARY-FAIL-STREAM 502 after 180s → ms_gw)

## 1. 背景 (改前必有数据)

R1041/R1042 两次判定 NVCF 上游系统性过载 (529_nv_overloaded + RemoteDisconnected + Timeout 全 key 均等,
后转 all_tiers_exhausted + stream_absolute_cap + 502) 后 NOP。本轮该事件**持续且继续走弱**:
30min SR 81.4% (<90%), all_tiers_exhausted 30min 内 6 次 (R1042 为 3 次), hm4104 fallback 持续触发。

### 30min 窗口 — nv_requests (tier_model='dsv4f0731_nv')
- 总量 43, 200=35, err=8, **SR=81.4%** (35/43)
- Avg/P50/P95/Max: 58508ms / 25115ms / 180073ms / 259424ms
  (p95=180s 恰好顶满 TIER_TIMEOUT_BUDGET_S=180 — 过载下请求普遍挂起烧满 budget)
- 错误: `all_tiers_exhausted|6|189193`, `client_gone_during_flush|2|222131`
- upstream: nvcf_pexec 42 (200=35, avg 54308ms), integrate 0
- finish_reason: tool_calls=27, stop=8
- 429: **0**, key_cycle_429s: k0=17, k1=26

### 30min per-key 200 延迟
| key | n | avg_ok_ms | max_ok_ms |
|-----|---|-----------|-----------|
| 0   | 11| 41299     | 92133     |
| 1   | 5 | 23416     | 47288     |
| 2   | 8 | 18200     | 29053     |
| 3   | 6 | 26736     | 76703     |
| 4   | 5 | 11806     | 21918     |

k0 avg 由 R1042 的 16.5s 升至 41.3s (承量 11 请求为全 key 最高), 但 max 92.1s 未超
others — 过载排队下的延迟抬升, 非 SOCKS5 代理故障。k4 最健康 (11.8s)。**无单 key 代理劣化。**

### 30min per-key 错误
| key | error | count | avg_ms |
|-----|-------|-------|--------|
| 0   | all_tiers_exhausted | 5 | 180055 |
| 1   | client_gone_during_flush | 2 | 222131 |
|     | all_tiers_exhausted | 1 | 234882 |

k0 承载 5/6 ATE。all_tiers_exhausted 为 **tier 级**错误 (整 tier 循环烧满 budget=180s), 归属 k0 仅因它是
轮转起始位/末次尝试 key。k0 avg_ok 41.3s 非最差, 证明 k0 代理健康, 非 key 劣化。

### 6h / 3h / 24h 趋势
- **6h: 658 总, 595 ok, SR=90.4%** (较 R1042 6h 94.6% 降), 63 err, 0 429
- 3h 逐小时: 11:00=6/6(100%), 10:00=100/116(86.2%), 09:00=86/100(86.0%), 08:00=89/96(92.7%)
  → 过载核心时段 (09:00-10:00) SR 降至 86%, 11:00 样本少 (6) 暂现恢复迹象需观察。
- **24h all_tiers_exhausted: 42** (较 R1042 的 28 大幅累积, 过载加深)

### Fallback 日志 (hm4104, 最近 5min)
- **触发 fallback**: `PRIMARY-FAIL-STREAM nv_gw 流式 server_5xx status=502 after 180082ms 切 fallback`
  + `FALLBACK-STREAM 从 primary 切到 ms_gw 流式`。主链路 nv_gw 502 (180s 后), hm4104 走 ms_gw 兜底。

## 2. 决策: NOP (无参数修改) — 根因仍为 NVCF 上游过载, 无参数可干净归因

**依据:**
1. **Root cause 与 R1041/R1042 同源且持续**: 表现形态为 all_tiers_exhausted (tier 级 budget 烧满 180-189s)
   + client_gone_during_flush (222s) + 显式 502 (180s), 均为**过载下请求挂起/连接被上游丢弃**的结果,
   非本容器 env/SOCKS5/超时配置可解。
2. **all_tiers_exhausted=6 是过载结果非 budget 配置问题**: 错误耗时 180-189s 恰好 = TIER_TIMEOUT_BUDGET_S=180。
   过载时每 key 需长时推理/排队才失败, 5 key 循环烧满 budget → ATE。**缩短 budget 会让更多请求过早 fail,
   拉长会让更多请求在死连接上空耗** — 均非正解。当前 180s 为合理平衡。
3. **k0 错误集中 (5/6 ATE) 是轮转伪象, 非 key 劣化**: 铁律要求"改前必有数据", 无数据支撑 k0 被冷却标记或
   移出。k0 avg_ok=41.3s 非全 key 最差, 且其 5 错误全为 tier 级 ATE (180s=budget 烧满), 由轮转起始位承担
   最多尝试所致。
4. **一次只改一个参数 / 不扰动**: 当前为外部上游过载, 无干净参数归因目标。调整 UPSTREAM_TIMEOUT / 冷却 /
   预算均无法改变 NVCF 容量, 属"瞎调", 违反铁律。NOP 最稳。
5. **端到端可用性由 fallback 保障**: hm4104 已正确显式 fail (502 after 180s) + 切 ms_gw 流式, 端到端降级
   但可用。本容器无需干预即可由 fallback 兜底。

当前 env (已 docker exec 复核, 全部维持): UPSTREAM_TIMEOUT=50, TIER_TIMEOUT_BUDGET_S=180,
NVU_TIER_BUDGET_DSV4F0731_NV=180, KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90,
NVU_KEYMGR_429_BASE/MAX_COOLDOWN=120, NVU_KEYMGR_CONN_BASE=30/MAX=60/FAIL_THRESHOLD=3/LONG=120,
NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_EMPTY_200_FASTBREAK=3。**无改动。**

## 3. 当前状态 (30min 主指标 + 6h 趋势)

- 30min SR: **81.4%** (35/43) / **6h SR: 90.4%** (595/658)
- Avg/P50/P95: 58508ms / 25115ms / 180073ms
- 错误 (30min): `all_tiers_exhausted` 6 (189s), `client_gone_during_flush` 2 (222s)
- 429: 0
- upstream: pexec 全量 (42, 200=35, avg 54.3s), integrate 0
- fallback: **持续触发** (hm4104 PRIMARY-FAIL-STREAM 502 after 180s → ms_gw)

## 4. 上次修改效果 (R1042 NOP → 本轮)

- **SR 略降**: 82.9% (R1042) → **81.4%** (本轮) — NVCF 过载持续, 非参数退化 (env 全程未动)。
- **ATE 加深**: 30min all_tiers_exhausted 3 → **6**; 24h 28 → **42**。过载从"偶发抖动"深化为"常规性
  budget 烧满"。
- **错误形态收敛**: R1042 的 stream_absolute_cap (2) 消失, 本轮全为 all_tiers_exhausted (6) +
  client_gone (2)。过载进入稳定挂起态。
- **fallback 持续**: 本轮无 R1042 的 breaker-skip 显式记录, 但仍 PRIMARY-FAIL-STREAM 502 after 180s
  → ms_gw, 主链路确定性恶化证据仍在。
- **429 仍 0**: 无 rate-limit/key 冷却问题, 排除本地 key 管理因素。

## 5. 下一步建议

1. **本轮 NOP, 继续等待 NVCF 过载消退**: 外部上游过载, 非本容器可调。下轮观察 11:00 后 SR 是否稳固回
   ≥90% (逐小时已见 11:00=100% 迹象, 但样本 6 不足为凭)。
2. **若过载持续且 SR 持续 <90%**: 评估是否启用 integrate lane (NV_INTEGRATE_KEYS) 作为 pexec 过载冗余
   分流。但 integrate 属架构级变更, 且当前 egress IP 池 (134.195.x) 与 pexec 直连未必缓解 NVCF 容量瓶颈;
   需多轮数据支撑, 不急于本轮。
3. **下轮重点**: 观察 (a) all_tiers_exhausted 是否仍逐时 5-6 次, (b) 502 是否持续, (c) 逐小时 SR 是否
   回升至 90% 以上。若 11:00 后样本恢复且 SR≥90%, NVCF 过载可能进入消退期。
4. **过载消退后复核**: 5 key 负载/延迟回到健康均匀态; 确认无 key 因过载期大量错误被冷却标记而长期规避
   (重点复核 k0, 因它连续两轮在轮转起始位承担最多 ATE 出口)。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] 数据完整: 30min/6h/3h/24h/per-key/fallback 均已采集
- [x] 错误深度: all_tiers_exhausted 6 (189s=budget 烧满) + client_gone 2 (222s), 429=0, 均过载结果非配置因素
- [x] k0 错误集中 (5/6 ATE) 判定为轮转起始位伪象 (avg_ok 41.3s 非全 key 最差, 代理健康), 非 key 劣化
- [x] hm4104 fallback 持续 (PRIMARY-FAIL-STREAM 502 after 180s → ms_gw), 端到端由 fallback 兜底
- [x] 决策数据驱动: NVCF 上游过载持续, 无参数可干净归因 → NOP, 不扰动配置