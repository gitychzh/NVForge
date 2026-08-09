# R1217: dsv4f0731_nv40666 NOP — 30min SR=96.49% 健康线上方, 2错全为NVCF侧tier级ATE(烧满180s budget), 无429/无单key劣化/无fallback, 24h ATE=104 历史水位

日期: 2026-08-09 09:34 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DeepSeek V4 Pro via NVCF pexec)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

30min SR=55/57=**96.49%**（在 95% NOP 阈值线上方，延续 R1213 98.2% → R1214 96.5% → R1215 95.2%
→ R1216 96.97% → 本轮 96.49% 的健康波动）。2 个错误全为 NVCF 侧 tier 级 ATE，无本容器可调杠杆。

**证据链**：
1. **all_tiers_exhausted ×2 (180054ms ×2)** — 两例均烧满整段 180s budget 的 tier 级事件（5 个 key
   全部尝试后均失败），归因 k0 仅为循环起点。与历轮同型的 NVCF 全键同质过载，非参数可调。两例同
   落 k0 均为循环首 key 承担长预算尝试的既有模式，非 k0 单 key 故障。
2. **净 429 = 0** — 30min 无请求级 429。key_cycle_429s (k0=16, k1=39, k2=2) 为内部轮转吸收计数，
   k1 虽吸收 39 次内部 429 但 14req 全成功 (avg48963ms)，轮转机制工作正常。
3. **无单 key 错误聚集** — 两错均落 k0，但均为 tier 级 ATE 的循环起点（烧满预算后 5 key 全失败的
   tier 级归因），非 k0 单 key 故障。per-key 200 延迟均衡 (avg 16.2-49.0s)，k3 最快 (16176ms)。
4. **upstream_type 全 pexec，integrate = 0，tier_attempts 空** — 无 pexec/integrate 失衡，
   无 key 间切换异常。
5. **hm4104 fallback 日志 = 无（采集窗口内）** — 预采集脚本 (09:34) 确认过去 5min 无 fallback，
   primary 链路健康。
6. **延迟分布健康** — Avg=41664ms, P50=28850ms, P95=107522ms。P50 显著低于 Avg（长尾拖高均值），
   P95=107.5s 处仍有成功请求，降低 budget 会切断长尾成功段。finish_reason 以 tool_calls 为主
   (42/55)，为长生成工作负载，符合 pexec 长流预期。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **96.49%** (55/57, 2 err, 0 timeout) |
| Avg / P50 / P95 | 41664 / 28850 / 107522 ms |
| 429 | 0 |
| upstream_type | nvcf_pexec 57/55 (96.49%), integrate 0 |
| finish_reason | tool_calls 42, stop 13 |

**错误分类**（30min 窗口 2 错）：
```
all_tiers_exhausted|2|180054   (tier级, 烧满 180s budget, 非参数可调)
```

**Per-key 200 延迟**（均衡, k3 最快, 无单 key 劣化）:
```
key0|10req|avg32277
key1|14req|avg48963
key2|13req|avg40146
key3|10req|avg16176
key4|8req|avg40350
```

**Per-key 错误**（两错均落 k0 = tier级循环起点, 非 key 故障）:
```
key0|all_tiers_exhausted|2|180054
```

**6h / 3h 趋势**：
```
6h:  661 req, 621 ok, 40 err  (SR=93.9%)
逐小时: 22:00=50/45(90.0%), 23:00=105/103(98.1%), 00:00=117/109(93.2%), 01:00=67/65(97.0%)
24h ATE: 104 (历史累积水位, 当前窗仅 2 例 tier 级)
```

## 上次修改效果（R1216 → R1217）

R1216 为 NOP，本轮继续 NOP。SR 从 96.97% → 96.49%（微降 0.48pct，健康波动），错误从 2 → 2
（R1216 的 stream_absolute_cap ×1 + ATE ×1 变为本轮 ATE ×2，stream_absolute_cap 消失，新增 1 例
tier 级 ATE）。所有错误均为 NVCF 流生成侧事件（全键过载），无本容器参数漂移。3h 逐小时确认
22:00 UTC (SR 90.0%) 至 01:00 UTC (SR 97.0%) 健康恢复。24h ATE 从 103 → 104 (+1)，仍为整日
峰值时段历史累积，当前窗仅 2 例活跃。

## 结论

SR=96.49% **在 95% NOP 阈值线上方**，30min 采集窗口健康：2 错全为 NVCF 侧 tier 级 ATE（烧满
180s budget 的全键过载），无 429、无单 key 劣化、无 integrate 失衡、无 tier_attempts 异常、
无 fallback。所有可调参数均无数据支撑说明调整能改善——降低 TIER_TIMEOUT_BUDGET_S/
NVU_TIER_BUDGET_DSV4F0731_NV (180s) 会切断 P95≈107.5s 处仍成功的请求且 ATE 事件本就在 budget
内烧满；调高 budget 只会延长 ATE 燃烧时间。维持 NOP。

## 下一步建议

- **保持 NOP 基线**：当前窗 SR=96.49% 健康，延续重点监控 24h ATE 累积（104）。
- **监控 stream_absolute_cap 是否反复**：R1215×2 / R1216×1 出现后本轮消失（0 例），说明 NVCF
  服务端流 cap 为间歇性，非持续收紧。若未来窗口重新 >3 例/窗再评估客户端侧拆短长 task。
- **关注 19:00-20:00 UTC 劣化窗口**：R1215 记录的当日劣化时段 (SR 81-85%) 已过去，当前 22:00-01:00
  UTC 窗口 SR 90-98% 健康波动。若需提升峰值可用性需单独采集该时段（当前无参数杠杆依据）。
- 若 NVCF 过载再次加深（SR 持续 <85% 或 ATE 单窗爆发 >5）可再评估，但按历史同型这仍为上游服务端
  过载，非本容器参数可调。