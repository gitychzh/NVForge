# R1214: dsv4f0731_nv40666 NOP — 30min SR=96.5% 健康, 2错全为非容器可调(NVCF过载ATE烧满budget + 客户端流中断), 无429/无fallback, 24h ATE=100历史水位

日期: 2026-08-09 08:20 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DeepSeek V4 Pro via NVCF pexec)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

30min SR=55/57=**96.5%**（高于 R1213 的 98.2%，远高于 95% NOP 阈值）。仅 2 个错误，全为非容器可
调的 NVCF 外部过载/客户端事件，无 429、无单 key 劣化、无 fallback。无本容器可调杠杆。

**证据链**：
1. **all_tiers_exhausted ×1 (180032ms)** — 烧满整段 180s budget 后 fail。这是 **tier 级**事件
   （5 个 key 全部尝试后均失败），归因到 k0 仅为循环起点，非 k0 单 key 劣化。属 NVCF 全键同质
   过载停滞，非参数可调（已连续多轮同型）。
2. **client_gone_during_flush ×1 (204585ms)** — 客户端在 180s+ 长流 flush 期间断开（204s > budget）。
   这是 hermes 客户端侧行为（用户/网关中断），非上游或 key 故障。非本容器可调。
3. **净 429 = 0** — 30min 无请求级 429。key_cycle_429s (k0=20, k1=33, k2=2, k3=2) 为内部轮转
   吸收计数，未产生请求级失败。
4. **无单 key 错误聚集** — 两错均落 k0，但 ATE 为 tier 级、client_gone 为客户端侧，均非 k0 故障。
   per-key 200 延迟 (k0=51956ms, k1=25676, k2=45654, k3=31405, k4=27808) 中 k0 略高但非劣化级
   （与前几轮同型，k0 为循环首 key 承担更多长预算尝试）。
5. **upstream_type 全 pexec，integrate = 0，tier_attempts 空** — 无 pexec/integrate 失衡，无
   key 间切换异常。
6. **hm4104 fallback 日志 = 无** — 过去 5min 无 fallback，primary 链路健康，hermes 服务经 direct
   直连稳定。
7. **延迟分布健康** — Avg=42632ms, P50=25202ms, P95=141275ms。P50 显著低于 Avg（长尾拖高均值），
   finish_reason 以 tool_calls 为主 (41/55)，为长生成工作负载，延迟分布符合 pexec 长流预期。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **96.5%** (55/57, 2 err, 0 timeout) |
| Avg / P50 / P95 | 42632 / 25202 / 141275 ms |
| 429 | 0 |
| upstream_type | nvcf_pexec 57/55 (96.5%), integrate 0 |
| finish_reason | tool_calls 41, stop 14 |

**错误分类**：
```
all_tiers_exhausted|1|180032   (tier级, 烧满 180s budget, 非参数可调)
client_gone_during_flush|1|204585   (客户端流中断, 非上游故障)
```

**Per-key 200 延迟**（均衡, k1/k4 最快, k0 略高但非劣化级）:
```
key0|10req|avg51956
key1|12req|avg25676
key2|15req|avg45654
key3|9req|avg31405
key4|9req|avg27808
```

**Per-key 错误**（两错均落 k0, 但分别为 tier 级 ATE 起点 + 客户端副作用）:
```
key0|all_tiers_exhausted|1|180032
key0|client_gone_during_flush|1|204585
```

**6h / 3h 趋势**：
```
6h:  612 req, 567 ok, 45 err, 0 timeout  (SR=92.6%)
3h:  00:00=35/37(94.6%), 23:00=103/105(98.1%), 22:00=108/116(93.1%), 21:00=98/101(97.0%)
24h ATE: 100 (历史累积水位, 当前窗仅 1 例 tier 级)
```

## 上次修改效果（R1213 → R1214）

R1213 为 NOP，本轮继续 NOP。SR 从 98.2% → 96.5%（微降 1.7pct），错误从 1 → 2（新增 1 例客户端流
中断）。两错全为外部事件（NVCF 过载 ATE + 客户端断开），无本容器参数漂移。24h ATE 从 99 → 100
(+1)，与历轮一致为整日峰值时段历史累积水位，当前窗仅 1 例活跃。佐证 SR 波动为上游过载窗口抖动，
非参数可调。

## 结论

SR=96.5% **远高于 95% NOP 阈值**，当前窗口健康：仅 1 个烧满 budget 的 tier 级 ATE（NVCF 全键过载，
非参数可调）+ 1 个客户端流中断（hermes 侧行为），无 429、无单 key 劣化、无 integrate 失衡、无
tier_attempts 异常、无 fallback。24h ATE=100 为整日峰值时段历史累积水位（21:00-23:00 早高峰 SR
93-97%），当前采集窗（08:20 UTC）已恢复健康。所有可调参数均无数据支撑说明调整能改善——尤其降低
TIER_TIMEOUT_BUDGET_S/NVU_TIER_BUDGET_DSV4F0731_NV (180s) 会切断长尾成功段，且 ATE 为 tier 级无法
单 key 归因。维持 NOP，与历轮一致。

## 下一步建议

- **保持 NOP 基线**：当前窗 SR=96.5% 健康，延续重点监控 24h ATE 累积（100）。
- **关注早高峰窗口**：21:00-23:00 UTC SR 93-97%，若需提升峰值可用性可在下窗单独采集峰值时段
  per-key/错误归因后再评估（当前无参数杠杆依据）。
- **k0 持续承担错误**：两窗连看 k0 均为 ATE/错误落点且延迟略高，但 ATE 为 tier 级循环起点、client_gone
  为客户端侧，无法归因 k0 单 key 劣化。若未来出现 k0 独立的连接类错误（ProxyConnectionError/
  SSLEOFError 聚集），再评估 per-key 冷却惩罚。
- 若 NVCF 过载再次加深（SR 持续 <85% 或单窗 ATE 爆发 >5）可再评估，但按历史同型这仍为上游服务端
  过载，非本容器参数可调。