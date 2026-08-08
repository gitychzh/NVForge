# R1211: dsv4f0731_nv40666 NOP — 30min SR=93.3%, 3错全为 NVCF 外部过载 ATE, 无单key劣化, 无容器可归因杠杆

日期: 2026-08-09 02:18 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DeepSeek V4 Pro via NVCF pexec)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

30min SR=42/45=**93.3%**（低于 95% NOP 阈值但较上窗 R1210 的 84.6% 回升），3 个错误经逐条归因
全为**非参数可归因事件**，与 R1191-R1210 反复判定的同一 **NVCF 外部过载** 根因完全延续。
无本容器可调杠杆。

**证据链**：
1. **all_tiers_exhausted ×3 (k0×2 + 空key×1, 各 ~176-180s)** — 与历轮相同的 NVCF 全键同质停滞模式，
   烧满整段 180s budget 后 fail，属上游服务端过载 jitter，非任何单 key/单参数可调。
   **24h ATE=73**（R1210=73 → 本轮 73，持平），无明显爬升，确证为持续外部过载基线。
2. **净 429 = 0** — key_cycle_429s (k0=15, k1=29, k2=1) 为内部轮转吸收计数，未产生请求级 429。
3. **无单 key 错误聚集** — 3 ATE 全落 k0/空key，但 k0 avg_ok=38814ms 非最差（k2=51816ms 最慢），
   per-key 200 延迟相对均衡 (k0 38.8s, k1 31.2s, k2 51.8s, k3 44.1s, k4 25.7s)，
   无固定某 key 的 SOCKS5/出口 IP 劣化；错误随机散布，属全键过载。
4. **integrate = 0，tier_attempts 空** — 无 pexec/integrate 失衡，无 key 间切换异常。
5. **hm4104 fallback 静默** — 最近 5min 无 fallback 日志，服务经 primary 直接成功，无振荡。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **93.3%** (42/45, 3 err, 0 timeout) |
| Avg / P50 / P95 / Max | 48345 / 33451 / 162583 / 180030 ms (p95 贴近 180s budget) |
| 429 | 0 |
| upstream_type | nvcf_pexec 44/42 (95.5%), integrate 0 |
| finish_reason | tool_calls 33, stop 9 |

**错误分类**：
```
all_tiers_exhausted|3|178707    (k0×2 + 空key×1, 各烧满 ~176-180s budget)
```

**Per-key 200 延迟**（均衡, 无单 key 错误聚集）:
```
key0|7req|avg38814|max67924
key1|9req|avg31225|max54704
key2|9req|avg51816|max106933
key3|10req|avg44060|max93741
key4|7req|avg25676|max63506
```

**Per-key 错误**（随机散布, 无固定劣化 key）:
```
key0|all_tiers_exhausted|2|180030
|all_tiers_exhausted|1|176063
```

**6h / 3h 趋势**：
```
6h:  536 req, 486 ok, 50 err, 0 timeout  (SR=90.7%)
3h:  18:00=32/31(96.9%), 17:00=90/79(87.8%), 16:00=89/81(91.0%), 15:00=74/71(95.9%)
24h ATE: 73 (持平)
```

## 上次修改效果（R1210 → R1211）

R1210 为 NOP（未改参数），本轮继续 NOP。SR 从上窗 84.6% → 93.3%（回升 8.7pct），
错误数从 6 → 3（减半），24h ATE 持平 73。证实上窗 SR 低谷为 NVCF 过载窗口抖动，非参数漂移。

## 结论

SR=93.3% 低于 95% 阈值，但 3 个错误经逐条归因全部为非容器可调的外部事件：
- 3× ATE（NVCF 全键过载，烧满 budget）

无单 key 劣化、无 429、无 integrate 失衡、无 tier_attempts 异常、24h ATE 持平(73)、fallback 静默。
所有可调参数（UPSTREAM_TIMEOUT/TIER_BUDGET/KEY_COOLDOWN/FASTBREAK）均无数据支撑说明调整能改善——
尤其降低 budget 会切断 p95≈163s 处仍能成功的请求。维持 NOP，与历轮一致。

## 下一步建议

- 持续观察 24h ATE 是否爬升（73 持平，若加速至 +5/窗 以上需升级关注）。
- 若 NVCF 过载持续加深导致 SR 长期 <90%，可考虑在下游 hm4104 侧评估 fallback 路由策略
  （但那是 hermes 侧配置，非本容器范围，仅记录）。
- 下一窗继续 NOP 判定条件：错误仍为 ATE/外部流事件主导且无单 key 聚集。