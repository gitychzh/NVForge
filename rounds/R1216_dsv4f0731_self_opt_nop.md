# R1216: dsv4f0731_nv40666 NOP — 30min SR=96.97% 健康线上方, 2错全为NVCF侧流事件(stream_absolute_cap×1 + tier级ATE×1), 无429/无单key劣化/无fallback, 24h ATE=103 历史水位

日期: 2026-08-09 09:18 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DeepSeek V4 Pro via NVCF pexec)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

30min SR=64/66=**96.97%**（在 95% NOP 阈值线上方，延续 R1213 98.2% → R1214 96.5% → R1215 95.2%
→ 本轮回升至 96.97% 的健康波动）。2 个错误全为 NVCF 侧流生成事件，无本容器可调杠杆。

**证据链**：
1. **stream_absolute_cap ×1 (158948ms)** — ~159s 处 NVCF 服务端流绝对上限事件（上游截断流），
   落 k2。非客户端、非 key 故障、非参数可调。事件在 180s budget 内，说明 budget 未提前切断，
   是 NVCF 自身对长流的 cap。
2. **all_tiers_exhausted ×1 (180057ms)** — 烧满整段 180s budget 的 tier 级事件（5 个 key 全部
   尝试后均失败），归因 k0 仅为循环起点。与历轮同型的 NVCF 全键同质过载，非参数可调。
3. **净 429 = 0** — 30min 无请求级 429。key_cycle_429s (k0=11, k1=53, k2=1, k4=1) 为内部轮转
   吸收计数，k1 虽吸收 53 次内部 429 但 17req 全成功 (avg42354ms)，轮转机制工作正常。
4. **无单 key 错误聚集** — k0 一错（ATE 为 tier 级起点）、k2 一错 (stream_absolute_cap)，均为
   NVCF 侧事件，非单 key 故障。per-key 200 延迟均衡 (avg 26.5-42.4s)。
5. **upstream_type 全 pexec，integrate = 0，tier_attempts 空** — 无 pexec/integrate 失衡，
   无 key 间切换异常。
6. **hm4104 fallback 日志 = 无（采集窗口内）** — 预采集脚本 (09:18) 确认过去 5min 无 fallback，
   primary 链路健康。**但后续验证发现窗口外单例 fallback**：hm4104 日志显示 09:25:35 一条
   `PRIMARY-FAIL-STREAM ... 502 after 180059ms`（烧满 180s budget 后 nv_gw 返回 502，是
   all_tiers_exhausted 的对外表现），随后切 ms_gw。DB 10min 窗口 fallback_occurred=0（nv_requests
   主链路），hm4104 侧为单例 fallback 事件，非系统性劣化。属 ATE 全键过载的既有模式，非参数可调。
7. **延迟分布健康** — Avg=37001ms, P50=29335ms, P95=83139ms。P50 显著低于 Avg（长尾拖高均值），
   P95=83.1s 处仍有成功请求，降低 budget 会切断长尾成功段。finish_reason 以 tool_calls 为主
   (48/66)，为长生成工作负载，符合 pexec 长流预期。

## 30min 窗口数据（脚本注入 + DB 复核）

| 指标 | 值 |
|---|---|
| SR | **96.97%** (64/66, 2 err, 0 timeout) |
| Avg / P50 / P95 | 37001 / 29335 / 83139 ms |
| 429 | 0 |
| upstream_type | nvcf_pexec 66/64 (96.97%), integrate 0 |
| finish_reason | tool_calls 48, stop 16 |

**错误分类**（30min 窗口 2 错）：
```
all_tiers_exhausted|1|180057   (tier级, 烧满 180s budget, 非参数可调)
stream_absolute_cap|1|158948   (NVCF 服务端流 cap, 非参数可调)
```

**Per-key 200 延迟**（均衡, 无单 key 劣化）:
```
key0|7req|avg33701
key1|17req|avg42354
key2|13req|avg28869
key3|14req|avg30496
key4|13req|avg26530
```

**Per-key 错误**（k0 = tier级起点, k2 = NVCF流cap, 均非 key 故障）:
```
key0|all_tiers_exhausted|1|180057
key2|stream_absolute_cap|1|158948
```

**6h / 3h 趋势**：
```
6h:  656 req, 615 ok, 41 err  (SR=93.8%)
逐小时: 22:00=88req(81ok), 23:00=105req(103ok), 00:00=117req(109ok), 01:00=39req(38ok, 97.4%)
24h ATE: 103 (历史累积水位, 当前窗仅 1 例 tier 级)
```

## 上次修改效果（R1215 → R1216）

R1215 为 NOP，本轮继续 NOP。SR 从 95.2% → 96.97%（回升 1.8pct），错误从 4 → 2（减少
stream_absolute_cap 1 例 + buffer_exhausted 1 例，仅剩 ATE 1 例 + stream_absolute_cap 1 例）。
所有错误均为 NVCF 流生成侧事件（服务端 cap / 全键过载），无本容器参数漂移。3h 逐小时确认
00:00 UTC (SR 93.2%) 至 01:00 UTC (SR 97.4%) 健康恢复。24h ATE 从 102 → 103 (+1)，仍为整日
峰值时段历史累积，当前窗仅 1 例活跃。

## 结论

SR=96.97% **在 95% NOP 阈值线上方**，30min 采集窗口健康：2 错全为 NVCF 侧流生成事件（stream_absolute_cap
×1 服务端流 cap、ATE ×1 烧满 budget 的全键过载），无 429、无单 key 劣化、无 integrate 失衡、
无 tier_attempts 异常，采集窗口内无 fallback。**窗口外单例 fallback**（09:25:35 hm4104 502
after 180059ms → ms_gw）是 ATE 全键过载的对外表现，符合既有模式。所有可调参数均无数据支撑说明
调整能改善——降低 TIER_TIMEOUT_BUDGET_S/NVU_TIER_BUDGET_DSV4F0731_NV (180s) 会切断 P95≈83s
处仍成功的请求且 stream_absolute_cap 事件本就在 budget 内被 NVCF 截断；调高 budget 只会延长
ATE 燃烧时间。维持 NOP。

## 下一步建议

- **保持 NOP 基线**：当前窗 SR=96.97% 健康，延续重点监控 24h ATE 累积（103）。
- **监控 stream_absolute_cap 频率**：连续两轮出现此错误类型（R1215×2, R1216×1，~159s）。
  若后续窗口该类型持续 >3 例/窗，说明 NVCF 对 dsv4f0731 长流的服务端 cap 收紧，可评估是否
  将长 task 拆短（客户端侧行为，非本容器参数）。
- **关注 19:00-20:00 UTC 劣化窗口**：R1215 记录的 6h 劣化时段（SR 81-85%）已过去，当前 01:00
  UTC 窗口恢复 97.4%。若需提升峰值可用性需单独采集该时段（当前无参数杠杆依据）。
- 若 NVCF 过载再次加深（SR 持续 <85% 或 ATE 单窗爆发 >5）可再评估，但按历史同型这仍为上游服务端
  过载，非本容器参数可调。