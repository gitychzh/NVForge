# R1220: dsv4f0731_nv40666 NOP — 30min SR=100% 健康, 0错/0超时/0错误分类, 无429/无单key劣化/无fallback, 24h ATE=107 历史水位

日期: 2026-08-09 10:44 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DeepSeek V4 Pro via NVCF pexec)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

30min SR=61/61=**100%**（远高于 95% NOP 阈值，为本轮系列近 7 轮最高，延续
R1213 98.2% → R1214 96.5% → R1215 95.2% → R1216 96.97% → R1217 96.49% → R1218 95.74% →
R1219 98.04% → 本轮 100% 的健康波动）。0 错误、0 超时、错误分类为空，无本容器可调杠杆。
独立复核 (10:44) DB 确认 last 30min `nv_requests` tier_model=dsv4f0731_nv: 63/63=100%。

**证据链**：
1. **错误分类 = 空** — 30min 窗口 0 错误、0 超时。无 all_tiers_exhausted、无 stream_absolute_cap、
   无 429、无 IncompleteRead。NVCF 侧本窗口无任何过载迹象。
2. **净 429 = 0** — 请求级 429=0。key_cycle_429s (k0=11, k1=46, k2=1, k3=3, k4=0) 为内部轮转
   吸收计数，k1 虽吸收 46 次内部 429 但 12req 全成功 (avg38183ms)，轮转机制工作正常。
3. **无单 key 错误聚集 / 延迟均衡** — 全窗口 0 错误。per-key 200 延迟均衡 (avg 29.7-38.2s)，
   k2 最快 (29728ms)，无劣化 key。
4. **upstream_type 全 pexec (61/61=100%)，integrate=0，tier_attempts 空** — 无 pexec/integrate
   失衡，无 key 间切换异常。
5. **hm4104 fallback 日志 = 无（采集窗口内）** — 预采集脚本 (10:44) 确认过去 5min 无 fallback，
   primary 链路健康。
6. **延迟分布健康** — Avg=34733ms, P50=19897ms, P95=120710ms。P50 显著低于 Avg（长尾拖高均值），
   P95≈120.7s 处仍有成功请求，降低 budget 会切断长尾成功段。finish_reason tool_calls 35/stop 26，
   长生成工作负载为主，符合 pexec 长流预期。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **100%** (61/61, 0 err, 0 timeout) |
| Avg / P50 / P95 | 34733 / 19897 / 120710 ms |
| 429 | 0 |
| upstream_type | nvcf_pexec 61/61 (100%), integrate 0 |
| finish_reason | tool_calls 35, stop 26 |

**错误分类**（30min 窗口 0 错）：空

**Per-key 200 延迟**（均衡, k2 最快, 无单 key 劣化）:
```
key0|12req|avg36679
key1|12req|avg38183
key2|10req|avg29728
key3|11req|avg33097
key4|16req|avg34937
```

**Per-key 错误**（无）:
```
(空)
```

**6h / 3h 趋势**：
```
6h:  689 req, 657 ok, 32 err  (SR=95.4%)
逐小时: 23:00=34/34(100%), 00:00=109/117(93.2%), 01:00=100/104(96.2%), 02:00=90/91(98.9%)
24h ATE: 107 (历史累积水位, 当前窗 0 例活跃)
```

## 上次修改效果（R1219 → R1220）

R1219 为 NOP，本轮继续 NOP。SR 从 98.04% → **100%**（+1.96pct，健康波动），错误从 1 → 0
（R1219 仅 1 例 tier 级 ATE，本轮 NVCF 侧完全无过载）。stream_absolute_cap 连续 4 轮 (R1217-R1220)
为 0 例，维持稳定。3h 逐小时 23:00 (100%) 至 02:00 UTC (98.9%) 全健康区间。24h ATE 从 106 → 107
(+1)，仍为整日峰值时段历史累积，当前窗 0 例活跃。

## 结论

SR=100% **远高于 95% NOP 阈值**，30min 采集窗口完全健康：0 错误、0 超时、错误分类为空、
无 429、无单 key 劣化、无 integrate 失衡、无 tier_attempts 异常、无 fallback。所有可调参数均无
数据支撑说明调整能改善——降低 TIER_TIMEOUT_BUDGET_S/NVU_TIER_BUDGET_DSV4F0731_NV (180s) 会切断
P95≈120.7s 处仍成功的请求；调高 budget 无益（当前无 ATE 事件）。维持 NOP。

## 下一步建议

- **保持 NOP 基线**：当前窗 SR=100% 健康，延续重点监控 24h ATE 累积（107）。
- **监控 stream_absolute_cap 是否反复**：R1215/R1216 间歇出现后已连续 4 轮 (R1217-R1220) 为 0 例，
  说明 NVCF 服务端流 cap 为间歇性，非持续收紧。若未来窗口重新 >3 例/窗再评估客户端侧拆短长 task。
- **关注峰值时段劣化**：当前 23:00-02:00 UTC 全健康（93-100%）。若需提升峰值可用性需单独采集
  劣化时段（当前无参数杠杆依据）。
- 若 NVCF 过载再次加深（SR 持续 <85% 或 ATE 单窗爆发 >5）可再评估，但按历史同型这仍为上游服务端
  过载，非本容器参数可调。