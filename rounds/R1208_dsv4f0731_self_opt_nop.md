# R1208: dsv4f0731_nv40666 NOP — 30min SR=88.9%, 5错全为 NVCF 外部过载/流事件, 无单key劣化, 无容器可归因杠杆

日期: 2026-08-09 01:42 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DeepSeek V4 Pro via NVCF pexec)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

30min SR=40/45=**88.9%**（低于 95% NOP 阈值），5 个错误全为**非参数可归因事件**，
与 R1191-R1207 反复判定的同一 **NVCF 外部过载** 根因完全延续。无本容器可调杠杆。

**证据链**：
1. **all_tiers_exhausted ×3 (全落 k0, 各 ~169s)** — 与历轮相同的 NVCF 全键同质停滞模式，
   每次烧满整段 180s budget 后 fail，属上游服务端过载 jitter，非任何单 key/单参数可调。
   **24h ATE=74**（R1207=73 → 本轮 74，+1/窗），缓慢爬升，确证 NVCF 过载持续，非本窗异常聚集。
2. **client_gone_during_flush ×1 (k1, 165238ms)** — 客户端在 flush 阶段断开，调用方侧事件，
   非本容器参数可调（烧满 ~165s 说明上游已尽力返回，客户端先行放弃）。
3. **stream_absolute_cap ×1 (k4, 171983ms)** — k4 为 per-key 最快 key (avg_ok=18741ms)，
   该流为超长请求 (~172s) 触达流绝对上限，非 key 劣化信号（k4 其余 6 次 200 全正常）。
4. **净 429 = 0** — key_cycle_429s (k0=12, k1=32, k4=1) 为内部轮转吸收计数，未产生请求级 429。
5. **无单 key 错误聚集** — 3 ATE 全落 k0，但 k0 avg_ok=44106ms 非最差（k2=53070ms 最慢），
   per-key 200 延迟相对均衡 (k0 44.1s, k1 47.9s, k2 53.1s, k3 45.1s, k4 18.7s)，
   无固定某 key 的 SOCKS5/出口 IP 劣化；错误随机散布，属全键过载。
6. **integrate = 0，tier_attempts 空** — 无 pexec/integrate 失衡，无 key 间切换异常。
7. **hm4104 fallback 活跃但目标健康** — PRIMARY-FAIL-STREAM 502 after 180079ms (烧满 budget)
   + FALLBACK-FAIL-STREAM (ms_gw timeout 250s)，但 ms_gw 目标健康，hermes 服务经 fallback 保住，
   此振荡为 NVCF primary 过载窗口的同步镜像（R1205=14 → R1206=0 → R1207=7 → 本轮 502）。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **88.9%** (40/45, 5 err, 0 timeout) |
| Avg / P50 / P95 | 56827 / 34278 / 170634 ms (p95 贴近 180s budget) |
| 429 | 0 |
| upstream_type | nvcf_pexec 45/40 (100%), integrate 0 |
| finish_reason | tool_calls 35, stop 5 |

**错误分类**：
```
all_tiers_exhausted|3|169466    (k0×3, 各烧满 ~169s budget)
client_gone_during_flush|1|165238  (k1, 调用方断开)
stream_absolute_cap|1|171983   (k4, 超长流触达上限, k4 本身最快)
```

**Per-key 200 延迟**（均衡, 无单 key 错误聚集）:
```
key0|5req|avg44106|max86747
key1|8req|avg47893|max89589
key2|6req|avg53070|max138680
key3|15req|avg45136|max117750
key4|6req|avg18741|max27141
```

**Per-key 错误**（随机散布, 无固定劣化 key）:
```
key0|all_tiers_exhausted|3
key1|client_gone_during_flush|1
key4|stream_absolute_cap|1
```

**6h / 3h 趋势**：
```
6h:  535 req, 482 ok, 53 err, 0 timeout  (SR=90.1%)
3h:  17:00=67/60(89.6%), 16:00=89/81(91.0%), 15:00=100/96(96.0%), 14:00=14/10(71.4%)
24h ATE: 74 (缓慢爬升)
```

## 结论

SR=88.9% 低于 95% 阈值，但 5 个错误经逐条归因全部为非容器可调的外部事件：
- 3× ATE（NVCF 全键过载，烧满 budget）
- 1× 客户端断开（调用方侧）
- 1× 超长流触达上限（k4 本身最快，非劣化）

无单 key 劣化、无 429、无 integrate 失衡、无 tier_attempts 异常。所有可调参数
（UPSTREAM_TIMEOUT/TIER_BUDGET/KEY_COOLDOWN/FASTBREAK）均无数据支撑说明调整能改善——
尤其降低 budget 会切断 p95≈170s 处仍能成功的请求。维持 NOP，与历轮一致。

## 下一步建议

- 持续观察 24h ATE 爬升速率（73→74，若加速至 +5/窗 以上需升级关注）。
- 若 NVCF 过载持续加深导致 SR 长期 <90%，可考虑在下游 hm4104 侧评估 fallback 路由策略
  （但那是 hermes 侧配置，非本容器范围，仅记录）。
- 下一窗继续 NOP 判定条件：错误仍为 ATE 主导且无单 key 聚集。