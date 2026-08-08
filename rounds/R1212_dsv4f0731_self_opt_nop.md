# R1212: dsv4f0731_nv40666 NOP — 30min SR=81.3%, 6错全为 NVCF 外部过载/流事件, 无单key劣化, 24h ATE 爬升至78(+5) 维持外部根因判定, 无容器可归因杠杆

日期: 2026-08-09 03:04 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DeepSeek V4 Pro via NVCF pexec)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

30min SR=26/32=**81.3%**（低于 95% NOP 阈值但较上窗 R1211 的 93.3% 回落），6 个错误经逐条归因
全为**非参数可归因事件**，与 R1191-R1211 反复判定的同一 **NVCF 外部过载** 根因完全延续。
无本容器可调杠杆。

**证据链**：
1. **all_tiers_exhausted ×3 (k0×2 + 空key×1, 各 ~176-180s)** — 与历轮相同的 NVCF 全键同质停滞模式，
   烧满整段 180s budget 后 fail，属上游服务端过载 jitter，非任何单 key/单参数可调。
   **24h ATE=78**（R1211=73 → 本轮 78，+5，爬升一档），仍为持续外部过载基线，由 R1210/R1211 的
   持平段转为小幅爬升——需关注是否进入加速段，但 3 ATE 全为烧满 budget 的过载停滞，非参数可调。
2. **stream_absolute_cap ×2 (k0, k4, ~151-159s)** — 两条超长流触达绝对上限，非 key 劣化
   （k0 avg_ok=41958ms、k4 avg_ok=60764ms 均非最差，k1=76611ms 最慢）。单窗 2 例同型，为
   NVCF 端超长请求处理过载，非定时聚集参数异常。
3. **client_gone_during_flush ×1 (k2, 210313ms)** — 客户端在 flush 阶段断开，调用方侧事件，
   非本容器参数可调。
4. **净 429 = 0** — key_cycle_429s (k0=10, k1=19, k2=1, k3=1, k4=1) 为内部轮转吸收计数，
   未产生请求级 429。
5. **无单 key 错误聚集** — 3 ATE 全落 k0/空key + 2 stream_absolute_cap 落 k0/k4，但 k0 avg_ok=41958ms
   非最差（k1=76611ms 最慢），per-key 200 延迟相对均衡 (k0 41.9s, k1 76.6s, k2 34.2s, k3 43.3s, k4 60.8s)，
   无固定某 key 的 SOCKS5/出口 IP 劣化；错误随机散布，属全键过载。
6. **integrate = 0，tier_attempts 空** — 无 pexec/integrate 失衡，无 key 间切换异常。
7. **hm4104 fallback 振荡但 primary 最终恢复** — FALLBACK-STREAM + PRIMARY-BREAKER-SKIP (circuit OPEN)
   + ms_gw 503 (67670ms) + PRIMARY-RETRY-OK，为 NVCF primary 过载/断路器窗口的同步镜像（历轮同型），
   hermes 服务经 retry/fallback 保住。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **81.3%** (26/32, 6 err, 0 timeout) |
| Avg / P50 / P95 / Max | 72021 / 52414 / 180027 / 200924 ms (p95 贴近 180s budget) |
| 429 | 0 |
| upstream_type | nvcf_pexec 31/26 (83.9%), integrate 0 |
| finish_reason | tool_calls 20, stop 6 |

**错误分类**：
```
all_tiers_exhausted|3|178652    (k0×2 + 空key×1, 各烧满 ~176-180s budget)
stream_absolute_cap|2|154999    (k0, k4, 超长流触达绝对上限 ~151-159s)
client_gone_during_flush|1|210313  (k2, 调用方断开)
```

**Per-key 200 延迟**（均衡, 无单 key 错误聚集）:
```
key0|6req|avg41958|max80335
key1|4req|avg76611|max137588
key2|6req|avg34179|max71555
key3|7req|avg43262|max98862
key4|3req|avg60764|max130823
```

**Per-key 错误**（随机散布, 无固定劣化 key）:
```
key0|all_tiers_exhausted|2|180027
key0|stream_absolute_cap|1|151344
key2|client_gone_during_flush|1|210313
key4|stream_absolute_cap|1|158653
|all_tiers_exhausted|1|175901
```

**6h / 3h 趋势**：
```
6h:  527 req, 474 ok, 53 err, 0 timeout  (SR=89.9%)
3h:  19:00=6/5(83.3%), 18:00=84/74(88.1%), 17:00=90/79(87.8%), 16:00=84/77(91.7%)
24h ATE: 78 (爬升, R1211=73 → +5)
```

## 上次修改效果（R1211 → R1212）

R1211 为 NOP（未改参数），本轮继续 NOP。SR 从上窗 93.3% → 81.3%（回落 12pct），错误数从 3 → 6（翻倍），
但 6 错全为历史同型外部事件（3 ATE + 2 stream_absolute_cap + 1 client_gone）。24h ATE 从 R1210/R1211
持平的 73 爬升至 78（+5）。证实 SR 波动为 NVCF 过载窗口抖动，非参数漂移；ATE 进入小幅爬升但未加速到
异常爆发段。

## 结论

SR=81.3% 低于 95% 阈值，但 6 个错误经逐条归因全部为非容器可调的外部事件：
- 3× ATE（NVCF 全键过载，烧满 budget）
- 2× stream_absolute_cap（超长流触达上限，k0/k4 本身非最慢）
- 1× 客户端断开（调用方侧）

无单 key 劣化、无 429、无 integrate 失衡、无 tier_attempts 异常、fallback 为 primary 过载的同步镜像。
24h ATE 爬升 73→78（+5）为唯一新信号，但仍为同一外部过载基线，非本容器参数可调。
所有可调参数（UPSTREAM_TIMEOUT/TIER_BUDGET/KEY_COOLDOWN/FASTBREAK）均无数据支撑说明调整能改善——
尤其降低 budget 会切断 p95≈180s 处仍能成功的请求。维持 NOP，与历轮一致。

## 下一步建议

- **升级关注 24h ATE 爬升**（73→78, +5）：若下窗继续爬升至 +5/窗 以上（即 ≥83）或 SR 持续 <85%，
  进入 NVCF 过载加深警戒。但按历史同型，这仍为上游服务端过载，非本容器参数可调。
- 若 NVCF 过载持续加深导致 SR 长期 <90%，可考虑在下游 hm4104 侧评估 fallback/断路器参数
  （hermes 侧配置，非本容器范围，仅记录）。
- 下一窗继续 NOP 判定条件：错误仍为 ATE/外部流事件主导且无单 key 聚集。