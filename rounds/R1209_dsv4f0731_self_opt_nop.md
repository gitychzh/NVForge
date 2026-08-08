# R1209: dsv4f0731_nv40666 NOP — 30min SR=87.2%, 5错全为 NVCF 外部过载/流事件, 无单key劣化, 无容器可归因杠杆

日期: 2026-08-09 01:46 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DeepSeek V4 Pro via NVCF pexec)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

30min SR=34/39=**87.2%**（低于 95% NOP 阈值），5 个错误经逐条归因全为**非参数可归因事件**，
与 R1191-R1208 反复判定的同一 **NVCF 外部过载** 根因完全延续。无本容器可调杠杆。

**证据链**：
1. **all_tiers_exhausted ×2 (全落 k0, 各 ~177s)** — 与历轮相同的 NVCF 全键同质停滞模式，
   烧满整段 180s budget 后 fail，属上游服务端过载 jitter，非任何单 key/单参数可调。
   **24h ATE=74**（R1208=74 → 本轮 74，持平），无明显爬升，确证为持续外部过载基线。
2. **NVStream_IncompleteRead ×1 (k1, 35114ms)** — 流被上游截断，单次事件（该窗仅 1 例），
   非定时/聚集模式，非参数可调。完成为 35s 快速失败，非烧满 budget，属 NVCF 端流中断。
3. **client_gone_during_flush ×1 (k1, 165238ms)** — 客户端在 flush 阶段断开，调用方侧事件，
   非本容器参数可调。
4. **stream_absolute_cap ×1 (k4, 171983ms)** — k4 为 per-key 最快 key (avg_ok=22215ms)，
   该流为超长请求 (~172s) 触达流绝对上限，非 key 劣化信号（k4 其余 3 次 200 全正常）。
5. **净 429 = 0** — key_cycle_429s (k0=14, k1=24, k4=1) 为内部轮转吸收计数，未产生请求级 429。
6. **无单 key 错误聚集** — 2 ATE 全落 k0，但 k0 avg_ok=35876ms 非最差（k2=75067ms 最慢），
   per-key 200 延迟相对均衡 (k0 35.9s, k1 64.2s, k2 75.1s, k3 54.3s, k4 22.2s)，
   无固定某 key 的 SOCKS5/出口 IP 劣化；错误随机散布，属全键过载。
7. **integrate = 0，tier_attempts 空** — 无 pexec/integrate 失衡，无 key 间切换异常。
8. **hm4104 fallback 活跃但目标健康** — PRIMARY-ZOMBIE-FALLBACK (content_filter)
   + PRIMARY-BREAKER-SKIP (circuit OPEN) + FALLBACK-STREAM 振荡，但 ms_gw 目标健康，
   hermes 服务经 fallback 保住，此振荡为 NVCF primary 过载/断路器窗口的同步镜像（历轮同型）。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **87.2%** (34/39, 5 err, 0 timeout) |
| Avg / P50 / P95 / Max | 63524 / 39489 / 172300 / 178200 ms (p95 贴近 180s budget) |
| 429 | 0 |
| upstream_type | nvcf_pexec 39/34 (100%), integrate 0 |
| finish_reason | tool_calls 30, stop 4 |

**错误分类**：
```
all_tiers_exhausted|2|177610    (k0×2, 各烧满 ~177s budget)
NVStream_IncompleteRead|1|35114  (k1, 流被上游截断, 单次)
client_gone_during_flush|1|165238  (k1, 调用方断开)
stream_absolute_cap|1|171983   (k4, 超长流触达上限, k4 本身最快)
```

**Per-key 200 延迟**（均衡, 无单 key 错误聚集）:
```
key0|6req|avg35876|max85905
key1|6req|avg64185|max114361
key2|4req|avg75067|max147583
key3|14req|avg54313|max130540
key4|4req|avg22215|max27535
```

**Per-key 错误**（随机散布, 无固定劣化 key）:
```
key0|all_tiers_exhausted|2
key1|NVStream_IncompleteRead|1
key1|client_gone_during_flush|1
key4|stream_absolute_cap|1
```

**6h / 3h 趋势**：
```
6h:  535 req, 482 ok, 53 err, 0 timeout  (SR=90.1%)
3h:  17:00=72/64(88.9%), 16:00=89/81(91.0%), 15:00=100/96(96.0%), 14:00=13/10(76.9%)
24h ATE: 74 (持平)
```

## 结论

SR=87.2% 低于 95% 阈值，但 5 个错误经逐条归因全部为非容器可调的外部事件：
- 2× ATE（NVCF 全键过载，烧满 budget）
- 1× NVStream_IncompleteRead（上游流截断，单次）
- 1× 客户端断开（调用方侧）
- 1× 超长流触达上限（k4 本身最快，非劣化）

无单 key 劣化、无 429、无 integrate 失衡、无 tier_attempts 异常、24h ATE 持平(74)。
所有可调参数（UPSTREAM_TIMEOUT/TIER_BUDGET/KEY_COOLDOWN/FASTBREAK）均无数据支撑说明调整能改善——
尤其降低 budget 会切断 p95≈172s 处仍能成功的请求。维持 NOP，与历轮一致。

## 下一步建议

- 持续观察 24h ATE 是否爬升（74 持平，若加速至 +5/窗 以上需升级关注）。
- 若 NVCF 过载持续加深导致 SR 长期 <90%，可考虑在下游 hm4104 侧评估 fallback 路由策略
  （但那是 hermes 侧配置，非本容器范围，仅记录）。
- 下一窗继续 NOP 判定条件：错误仍为 ATE/外部流事件主导且无单 key 聚集。