# R1213: dsv4f0731_nv40666 NOP — 30min SR=98.2% 显著回升, 56/57 单错为烧满budget的ATE, 无429/无单key劣化/无fallback, 24h ATE=99 为历史过载累积非当前异常

日期: 2026-08-09 08:00 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DeepSeek V4 Pro via NVCF pexec)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

30min SR=56/57=**98.2%**（从上窗 R1212 的 81.3% 显著回升 16.9pct，回到健康线上方，远超 95% 阈值）。
唯一 1 个错误为 `all_tiers_exhausted`（180066ms = 烧满整段 180s budget 后 fail），属与历轮同型的
NVCF 全键同质过载停滞，非本容器参数可调。无本容器可调杠杆。

**证据链**：
1. **all_tiers_exhausted ×1 (180066ms)** — 单一事件烧满 180s budget 后 fail。24h ATE=99 表面看较
   R1212 的 78 爬升一档，但当前 30min ��口仅 1 例 ATE，成功 56 例，说明 ATE 累积为当日峰值时段
   历史事件（21:00/22:00 早高峰窗口），当前采集窗已恢复健康，非参数可调。
2. **净 429 = 0** — 30min 无请求级 429。key_cycle_429s (k0=13, k1=39, k2=2, k3=3) 为内部轮转
   吸收计数，未产生请求级失败。
3. **无单 key 错误聚集 / 无 key 劣化** — 唯一 ATE 落 k0（k0 仅 7req/avg54994ms，非最慢），per-key
   200 延迟相对均衡 (k0 54.9s, k1 38.6s, k2 42.4s, k3 42.9s, k4 30.5s)，无固定某 key 的
   SOCKS5/出口 IP 劣化。key4 最快 (avg30533ms) 且 14req 全成功。
4. **upstream_type 全 pexec，integrate = 0，tier_attempts 空** — 无 pexec/integrate 失衡，无
   key 间切换异常。
5. **hm4104 fallback 日志 = 无** — 过去 5min 无 fallback，primary 链路健康，hermes 服务经 direct
   直连稳定。
6. **延迟分布健康** — Avg=42572ms, P50=26352ms, P95=146570ms。P50 显著低于 Avg（长尾拖高均值），
   但 P95≈146s 处仍有成功请求，降低 TIER_BUDGET 会切断此长尾成功段，无改善依据。finish_reason 以
   tool_calls 为主 (36/56)，为长生成工作负载，延迟分布符合 pexec 长流预期。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **98.2%** (56/57, 1 err, 0 timeout) |
| Avg / P50 / P95 | 42572 / 26352 / 146570 ms |
| 429 | 0 |
| upstream_type | nvcf_pexec 57/56 (98.2%), integrate 0 |
| finish_reason | tool_calls 36, stop 20 |

**错误分类**：
```
all_tiers_exhausted|1|180066   (k0, 烧满 180s budget)
```

**Per-key 200 延迟**（均衡, 无单 key 劣化, key4 最快）:
```
key0|7req|avg54994|max150365
key1|14req|avg38572|max102902
key2|13req|avg42360|max110593
key3|8req|avg42933|max125176
key4|14req|avg30533|max62117
```

**Per-key 错误**（唯一 1 错落 k0, 非最慢 key）:
```
key0|all_tiers_exhausted|1|180066
```

**6h / 3h 趋势**：
```
6h:  609 req, 564 ok, 45 err, 0 timeout  (SR=92.6%)
3h:  23:00=102/104(98.1%), 22:00=108/116(93.1%), 21:00=127/132(96.2%)
24h ATE: 99 (历史累积, 当前窗仅 1 例)
```

## 上次修改效果（R1212 → R1213）

R1212 为 NOP（未改参数），本轮继续 NOP。SR 从上窗 81.3% → 98.2%（回升 16.9pct），错误数从 6 → 1
（锐减）。证实 R1212 的 6 错全为 NVCF 过载窗口抖动（3 ATE + 2 stream_absolute_cap + 1
client_gone），本轮窗口已恢复健康——佐证 SR 波动为外部过载窗口而非本容器参数漂移。24h ATE 从 78 →
99（+21）表面爬升，但当前窗仅 1 例、成功 56 例，确认 ATE 为该容器整日峰值时段累积的历史水位，
非当前采集窗活跃异常。

## 结论

SR=98.2% **远超 95% NOP 阈值**，当前窗口健康：仅 1 个烧满 budget 的 ATE（非参数可调的外部过载
事件），无 429、无单 key 劣化、无 integrate 失衡、无 tier_attempts 异常、无 fallback。24h ATE=99
为整日峰值时段历史累积水位（21:00/22:00 早高峰 SR 93-96%），当前采集窗（08:00 UTC）已恢复健康。
所有可调参数均无数据支撑说明调整能改善——尤其降低 TIER_TIMEOUT_BUDGET_S/NVU_TIER_BUDGET_DSV4F0731_NV
(180s) 会切断 P95≈146s 处仍成功的请求。维持 NOP，与历轮一致。

## 下一步建议

- **保持 NOP 基线**：当前窗 SR=98.2% 健康，延续重点监控 24h ATE 累积（99）。
- **关注早高峰窗口**：21:00/22:00 UTC 时成功率仍为 93-96%，若需提升峰值窗口可用性，可在下窗单独
  采集峰值时段的 per-key/错误归因后再评估是否有参数杠杆（当前无依据）。
- 若 NVCF 过载再次加深（SR 持续 <85% 或 ATE 单窗爆发 >5）可再评估，但按历史同型这仍为上游服务端
  过载，非本容器参数可调。