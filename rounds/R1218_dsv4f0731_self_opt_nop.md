# R1218: dsv4f0731_nv40666 NOP — 30min SR=95.74% 健康线上方, 2错全为NVCF侧tier级ATE(烧满180s budget), 无429/无单key劣化/无fallback, 24h ATE=105 历史水位

日期: 2026-08-09 09:46 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DeepSeek V4 Pro via NVCF pexec)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

30min SR=45/47=**95.74%**（在 95% NOP 阈值线上方，延续 R1213 98.2% → R1214 96.5% → R1215 95.2%
→ R1216 96.97% → R1217 96.49% → 本轮 95.74% 的健康波动）。2 个错误全为 NVCF 侧 tier 级 ATE，
无本容器可调杠杆。

**证据链**：
1. **all_tiers_exhausted ×2 (180050ms ×2)** — 两例均烧满整段 180s budget 的 tier 级事件（5 个 key
   全部尝试后均失败），归因 k0 仅为循环起点。与历轮同型的 NVCF 全键同质过载，非参数可调。两错同
   落 k0 均为循环首 key 承担长预算尝试的既有模式，非 k0 单 key 故障。
2. **净 429 = 0** — 30min 无请求级 429。key_cycle_429s (k0=15, k1=30, k2=2) 为内部轮转吸收计数，
   k1 虽吸收 30 次内部 429 但 10req 全成功 (avg55238ms)，轮转机制工作正常。
3. **无单 key 错误聚集** — 两错均落 k0，但均为 tier 级 ATE 的循环起点（烧满预算后 5 key 全失败的
   tier 级归因），非 k0 单 key 故障。per-key 200 延迟均衡 (avg 22.1-55.2s)，k3 最快 (22084ms)。
4. **upstream_type 全 pexec，integrate = 0，tier_attempts 空** — 无 pexec/integrate 失衡，
   无 key 间切换异常。
5. **hm4104 fallback 日志 = 无（采集窗口内）** — 预采集脚本 (09:46) 确认过去 5min 无 fallback，
   primary 链路健康。
6. **延迟分布健康** — Avg=46202ms, P50=28652ms, P95=113081ms。P50 显著低于 Avg（长尾拖高均值），
   P95=113.1s 处仍有成功请求，降低 budget 会切断长尾成功段。finish_reason 以 tool_calls 为主
   (35/45)，为长生成工作负载，符合 pexec 长流预期。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **95.74%** (45/47, 2 err, 0 timeout) |
| Avg / P50 / P95 | 46202 / 28652 / 113081 ms |
| 429 | 0 |
| upstream_type | nvcf_pexec 47/45 (95.74%), integrate 0 |
| finish_reason | tool_calls 35, stop 10 |

**错误分类**（30min 窗口 2 错）：
```
all_tiers_exhausted|2|180050   (tier级, 烧满 180s budget, 非参数可调)
```

**Per-key 200 延迟**（均衡, k3 最快, 无单 key 劣化）:
```
key0|7req|avg29696
key1|10req|avg55238
key2|12req|avg40651
key3|8req|avg22084
key4|8req|avg48333
```

**Per-key 错误**（两错均落 k0 = tier级循环起点, 非 key 故障）:
```
key0|all_tiers_exhausted|2|180050
```

**6h / 3h 趋势**：
```
6h:  655 req, 615 ok, 40 err  (SR=93.9%)
逐小时: 22:00=29/31(93.5%), 23:00=103/105(98.1%), 00:00=109/117(93.2%), 01:00=81/84(96.4%)
24h ATE: 105 (历史累积水位, 当前窗仅 2 例 tier 级)
```

## 上次修改效果（R1217 → R1218）

R1217 为 NOP，本轮继续 NOP。SR 从 96.49% → 95.74%（微降 0.75pct，健康波动），错误从 2 → 2
（均为 tier 级 ATE，stream_absolute_cap 仍未复现，维持 0 例）。所有错误均为 NVCF 流生成侧事件
（全键过载），无本容器参数漂移。3h 逐小时确认 22:00 UTC (SR 93.5%) 至 01:00 UTC (SR 96.4%)
健康波动。24h ATE 从 104 → 105 (+1)，仍为整日峰值时段历史累积，当前窗仅 2 例活跃。

## 结论

SR=95.74% **在 95% NOP 阈值线上方**，30min 采集窗口健康：2 错全为 NVCF 侧 tier 级 ATE（烧满
180s budget 的全键过载），无 429、无单 key 劣化、无 integrate 失衡、无 tier_attempts 异常、
无 fallback。所有可调参数均无数据支撑说明调整能改善——降低 TIER_TIMEOUT_BUDGET_S/
NVU_TIER_BUDGET_DSV4F0731_NV (180s) 会切断 P95≈113s 处仍成功的请求且 ATE 事件本就在 budget
内烧满；调高 budget 只会延长 ATE 燃烧时间。维持 NOP。

## 下一步建议

- **保持 NOP 基线**：当前窗 SR=95.74% 健康，延续重点监控 24h ATE 累积（105）。
- **监控 stream_absolute_cap 是否反复**：R1215/R1216 间歇出现后已连续 2 轮 (R1217/R1218) 为 0 例，
  说明 NVCF 服务端流 cap 为间歇性，非持续收紧。若未来窗口重新 >3 例/窗再评估客户端侧拆短长 task。
- **关注峰值时段劣化**：当前 22:00-01:00 UTC 窗口 SR 93-98% 健康波动。若需提升峰值可用性需单独
  采集劣化时段（当前无参数杠杆依据）。
- 若 NVCF 过载再次加深（SR 持续 <85% 或 ATE 单窗爆发 >5）可再评估，但按历史同型这仍为上游服务端
  过载，非本容器参数可调。