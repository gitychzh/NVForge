# R1219: dsv4f0731_nv40666 NOP — 30min SR=98.04% 健康, 1错为NVCF侧tier级ATE(烧满180s budget), 无429/无单key劣化/无fallback, 24h ATE=106 历史水位

日期: 2026-08-09 10:06 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DeepSeek V4 Pro via NVCF pexec)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

30min SR=50/51=**98.04%**（显著高于 95% NOP 阈值，为本轮系列近 6 轮最高之一，延续
R1213 98.2% → R1214 96.5% → R1215 95.2% → R1216 96.97% → R1217 96.49% → R1218 95.74%
→ 本轮 98.04% 的健康波动）。仅 1 个错误为 NVCF 侧 tier 级 ATE，无本容器��调杠杆。

**证据链**：
1. **all_tiers_exhausted ×1 (180086ms)** — 单例烧满整段 180s budget 的 tier 级事件（5 个 key
   全部尝试后均失败，归因 k0 仅为循环起点）。与历轮同型的 NVCF 全键同质过载，非参数可调。
2. **净 429 = 0** — 30min 无请求级 429。key_cycle_429s (k0=5, k1=40, k2=5, k3=1) 为内部轮转
   吸收计数，k1 虽吸收 40 次内部 429 但 13req 全成功 (avg49010ms)，轮转机制工作正常。
3. **无单 key 错误聚集 / 延迟均衡** — 唯一错误落 k0 为 tier 级 ATE 循环起点，非 k0 故障。
   per-key 200 延迟均衡 (avg 34.9-49.0s)，k3 最快 (34933ms)，无劣化 key。
4. **upstream_type 全 pexec，integrate=0，tier_attempts 空** — 无 pexec/integrate 失衡，
   无 key 间切换异常。
5. **hm4104 fallback 日志 = 无（采集窗口内）** — 预采集脚本 (10:06) 确认过去 5min 无 fallback，
   primary 链路健康。
6. **延迟分布健康** — Avg=43310ms, P50=24470ms, P95=112541ms。P50 显著低于 Avg（长尾拖高均值），
   P95=112.5s 处仍有成功请求，降低 budget 会切断长尾成功段。finish_reason 以 tool_calls 为主
   (35/50)，为长生成工作负载，符合 pexec 长流预期。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **98.04%** (50/51, 1 err, 0 timeout) |
| Avg / P50 / P95 | 43310 / 24470 / 112541 ms |
| 429 | 0 |
| upstream_type | nvcf_pexec 51/50 (98.04%), integrate 0 |
| finish_reason | tool_calls 35, stop 15 |

**错误分类**（30min 窗口 1 错）：
```
all_tiers_exhausted|1|180086   (tier级, 烧满 180s budget, 非参数可调)
```

**Per-key 200 延迟**（均衡, k3 最快, 无单 key 劣化）:
```
key0|7req|avg42468
key1|13req|avg49010
key2|11req|avg39022
key3|11req|avg34933
key4|8req|avg35104
```

**Per-key 错误**（唯一错误落 k0 = tier级循环起点, 非 key 故障）:
```
key0|all_tiers_exhausted|1|180086
```

**6h / 3h 趋势**：
```
6h:  674 req, 637 ok, 37 err  (SR=94.5%)
逐小时: 23:00=90/92(97.8%), 00:00=109/117(93.2%), 01:00=100/104(96.2%), 02:00=20/20(100%)
24h ATE: 106 (历史累积水位, 当前窗仅 1 例 tier 级)
```

## 上次修改效果（R1218 → R1219）

R1218 为 NOP，本轮继续 NOP。SR 从 95.74% → 98.04%（回升 +2.3pct，健康波动），错误从 2 → 1
（均为 tier 级 ATE，stream_absolute_cap 连续 3 轮 0 例，维持稳定）。所有错误均为 NVCF 流生成
侧事件（全键过载），无本容器参数漂移。3h 逐小时确认 23:00 UTC (SR 97.8%) 至 02:00 UTC
(SR 100%) 健康波动。24h ATE 从 105 → 106 (+1)，仍为整日峰值时段历史累积，当前窗仅 1 例活跃。

## 结论

SR=98.04% **远高于 95% NOP 阈值**，30min 采集窗口健康：1 错为 NVCF 侧 tier 级 ATE（烧满
180s budget 的全键过载），无 429、无单 key 劣化、无 integrate 失衡、无 tier_attempts 异常、
无 fallback。所有可调参数均无数据支撑说明调整能改善——降低 TIER_TIMEOUT_BUDGET_S/
NVU_TIER_BUDGET_DSV4F0731_NV (180s) 会切断 P95≈112.5s 处仍成功的请求且 ATE 事件本就在 budget
内烧满；调高 budget 只会延长 ATE 燃烧时间。维持 NOP。

## 下一步建议

- **保持 NOP 基线**：当前窗 SR=98.04% 健康，延续重点监控 24h ATE 累积（106）。
- **监控 stream_absolute_cap 是否反复**：R1215/R1216 间歇出现后已连续 3 轮 (R1217-R1219) 为 0 例，
  说明 NVCF 服务端流 cap 为间歇性，非持续收紧。若未来窗口重新 >3 例/窗再评估客户端侧拆短长 task。
- **关注峰值时段劣化**：当前 23:00-02:00 UTC 窗口 SR 93-100% 健康波动。若需提升峰值可用性需单独
  采集劣化时段（当前无参数杠杆依据）。
- 若 NVCF 过载再次加深（SR 持续 <85% 或 ATE 单窗爆发 >5）可再评估，但按历史同型这仍为上游服务端
  过载，非本容器参数可调。