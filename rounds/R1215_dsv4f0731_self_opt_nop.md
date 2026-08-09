# R1215: dsv4f0731_nv40666 NOP — 30min SR=95.2% 健康线上方, 4错全为NVCF侧流事件(stream_absolute_cap×2 + tier级ATE×1 + buffer_exhausted×1), 无429/无单key劣化/无fallback, 24h ATE=102 历史水位

日期: 2026-08-09 09:02 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DeepSeek V4 Pro via NVCF pexec)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

30min SR=59/62=**95.2%**（在 95% NOP 阈值线上方，延续 R1213 98.2% → R1214 96.5% → 本轮 95.2%
的微降但健康趋势）。4 个错误全为 NVCF 侧流生成事件，无本容器可调杠杆。

**证据链**：
1. **stream_absolute_cap ×2 (160001ms, 158948ms)** — 新增错误类型，落 k0/k2。~160s 处 NVCF
   服务端流绝对上限事件（上游截断流），非客户端、非 key 故障、非参数可调。两事件均在 180s
   budget 内，说明 budget 未提前切断，是 NVCF 自身对长流的 cap。
2. **all_tiers_exhausted ×1 (180029ms)** — 烧满整段 180s budget 的 tier 级事件（5 个 key 全部
   尝试后均失败），归因 k0 仅为循环起点。与历轮同型的 NVCF 全键同质过载，非参数可调。
3. **buffer_exhausted ×1 (97510ms)** — 97.5s 处 buffer 耗尽（last verdict: execute_failed）。
   NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90，该事件已越过 90s stair 后失败。此机制仅作用于
   `NVU_BUFFER_CALLERS=cc4101-fallback` 调用方；调高 stair 只会推迟 verdict（请求已失败），
   调低无意义。非当前杠杆。
4. **净 429 = 0** — 30min 无请求级 429。key_cycle_429s (k0=13, k1=47, k4=2) 为内部轮转吸收
   计数，k1 虽吸收 47 次内部 429 但 15req 全成功 (avg35864ms)，轮转机制工作正常。
5. **无单 key 错误聚集** — k0 两错（ATE 为 tier 级起点 + stream_absolute_cap）、k2 一错
   (stream_absolute_cap)，均为 NVCF 侧事件，非 k0/k2 单 key 故障。per-key 200 延迟均衡
   (avg 24.7-36.3s)。
6. **upstream_type 全 pexec，integrate = 0，tier_attempts 空** — 无 pexec/integrate 失衡，
   无 key 间切换异常。
7. **hm4104 fallback 日志 = 无** — 预采集脚本确认过去 5min 无 fallback，primary 链路健康。
8. **延迟分布健康** — Avg=37588ms, P50=25534ms, P95=85700ms。P50 显著低于 Avg（长尾拖高均值），
   P95=85.7s 处仍有成功请求，降低 budget 会切断长尾成功段。finish_reason 以 tool_calls 为主
   (43/59)，为长生成工作负载，符合 pexec 长流预期。

## 30min 窗口数据（脚本注入 + DB 复核）

| 指标 | 值 |
|---|---|
| SR | **95.2%** (59/62, 3 err, 0 timeout) |
| Avg / P50 / P95 | 37588 / 25534 / 85700 ms |
| 429 | 0 |
| upstream_type | nvcf_pexec 62/59 (95.2%), integrate 0 |
| finish_reason | tool_calls 43, stop 16 |

**错误分类**（35min 复核窗口 4 错）：
```
all_tiers_exhausted|1|180029   (tier级, 烧满 180s budget, 非参数可调)
stream_absolute_cap|2|160001/158948   (NVCF 服务端流 cap, 非参数可调)
buffer_exhausted|1|97510   (buffer stair 耗尽, cc4101-fallback 专用机制)
```

**Per-key 200 延迟**（均衡, 无单 key 劣化）:
```
key0|8req|avg26085
key1|15req|avg35864
key2|13req|avg31121
key3|10req|avg35795
key4|13req|avg24714
```

**Per-key 错误**（k0 两错 = tier级起点 + NVCF流cap, 非 key 故障）:
```
key0|all_tiers_exhausted|1|180029
key0|stream_absolute_cap|1|161053
key2|stream_absolute_cap|1|158948
```

**6h / 3h 趋势**：
```
6h:  644 req, 602 ok, 42 err  (SR=93.5%)
逐小时: 19:00=61/72(84.7%), 20:00=77/95(81.1%), 21:00=127/138(92.0%),
        22:00=108/120(90.0%), 23:00=103/106(97.2%), 00:00=109/120(90.8%), 01:00=20/21(95.2%)
24h ATE: 102 (历史累积水位, 当前窗仅 1 例 tier 级)
```

## 上次修改效果（R1214 → R1215）

R1214 为 NOP，本轮继续 NOP。SR 从 96.5% → 95.2%（微降 1.3pct），错误从 2 → 4（新增 2 例
NVCF 侧 stream_absolute_cap + 1 例 buffer_exhausted，ATE 持平 1 例）。所有新错均为 NVCF 流
生成侧事件（服务端 cap / buffer 耗尽 / 全键过载），无本容器参数漂移。6h 趋势确认 19:00-20:00
UTC 为当日劣化窗口 (SR 81-85%)，当前采集窗 (01:00 UTC) 已恢复 95.2%。24h ATE 从 100 → 102
(+2)，仍为整日峰值时段历史累积，当前窗仅 1 例活跃。

## 数据完整性备注

采集后的一次 DB 复核工具输出中混入一行未标记的 "⚠️ [hm4104] primary 故障/超时, 已 fallback
到 dsv4f0731_ms" 文本。该文本**不是** out-of-band 用户消息（缺少官方标记），且与预采集脚本
"(无 fallback 日志)" 直接矛盾，判定为不可信内容（疑似注入），未据此采取任何动作。hm4104
fallback 状态以预采集脚本为准：无 fallback。

## 结论

SR=95.2% **在 95% NOP 阈值线上方**，当前窗口健康：4 错全为 NVCF 侧流生成事件（stream_absolute_cap
×2 服务端流 cap、ATE ×1 烧满 budget 的全键过载、buffer_exhausted ×1 越 stair 后失败），无 429、
无单 key 劣化、无 integrate 失衡、无 tier_attempts 异常、无 fallback。所有可调参数均无数据支撑
说明调整能改善——降低 TIER_TIMEOUT_BUDGET_S/NVU_TIER_BUDGET_DSV4F0731_NV (180s) 会切断 P95≈85.7s
处仍成功的请求且 stream_absolute_cap 事件本就在 budget 内被 NVCF 截断；调高 budget 只会延长 ATE
燃烧时间；NVU_BUFFER_TIMEOUT_STAIRS (90s) 仅作用于 cc4101-fallback 且该请求已失败。维持 NOP。

## 下一步建议

- **保持 NOP 基线**：当前窗 SR=95.2% 健康，延续重点监控 24h ATE 累积（102）。
- **监控 stream_absolute_cap 频率**：本轮新增此错误类型（2 例，~160s）。若后续窗口该类型持续
  >3 例/窗，说明 NVCF 对 dsv4f0731 长流的服务端 cap 收紧，可评估是否将长 task 拆短（客户端侧
  行为，非本容器参数）。
- **关注 19:00-20:00 UTC 劣化窗口**：6h 数据确认该时段 SR 81-85% 为当日过载峰，若需提升峰值
  可用性需单独采集该时段 per-key/错误归因（当前无参数杠杆依据）。
- 若 NVCF 过载再次加深（SR 持续 <85% 或 ATE 单窗爆发 >5）可再评估，但按历史同型这仍为上游服务端
  过载，非本容器参数可调。