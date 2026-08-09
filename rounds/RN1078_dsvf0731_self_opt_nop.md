# RN1078: dsvf0731_nv40666 NOP — 30min SR=100% (63/63), 零错误零429零fallback, 完全健康, 24h ATE=99 为历史过载累积非当前异常

日期: 2026-08-09 08:08 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DeepSeek V4 Pro via NVCF pexec)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

30min SR=63/63=**100%**（上窗 R1213 的 98.2% 基础上再回升 1.8pct 至满额），本窗**零错误**、
**零 429**、**零 fallback**、**零单 key 劣化**，为完全健康窗口，远超 95% NOP 阈值。无任何可归因杠杆。

**证据链**：
1. **零错误** — 30min 窗口 63 请求全成功，错误分类表完全为空。无 all_tiers_exhausted /
   stream_absolute_cap / NVCF 过载事件（对比 R1211/R1212 的 6-3 例 ATE 显著好转）。
2. **净 429 = 0** — key_cycle_429s (k0=17, k1=41, k2=2, k3=3) 为内部轮转吸收计数，
   未产生请求级 429。k1 轮转最频繁但 13req 全成功 avg34586ms 非最慢，属正常配额轮询。
3. **无单 key 劣化** — per-key 200 延迟相对均衡 (k0 50.4s/11req, k1 34.6s/13, k2 39.7s/16,
   k3 36.8s/9, k4 30.8s/14)，key4 最快且 14req 全成功，无固定某 key 的 SOCKS5/出口 IP 劣化。
4. **upstream_type 全 pexec，integrate = 0，tier_attempts 空** — 无 pexec/integrate 失衡，
   无 key 间切换异常。
5. **hm4104 fallback 日志 = 无** — 过去 5min 无 fallback，primary 链路健康，hermes 服务经
   direct 直连稳定。
6. **24h ATE=99 为历史累积** — 当前 30min 窗零 ATE，成功 63 例，ATE 累积为当日早高峰
   (21:00/22:00) 历史事件，非当前窗口异常，非参数可调。
7. **延迟分布健康** — Avg=38096ms, P50=25234ms, P95=119754ms。P50 显著低于 Avg（长尾拖高均值），
   P95≈120s 处仍有成功请求。finish_reason 以 tool_calls 为主 (44/63)，为长生成工作负载，
   延迟分布符合 pexec 长流预期。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **100%** (63/63, 0 err, 0 timeout) |
| Avg / P50 / P95 | 38096 / 25234 / 119754 ms |
| 429 | 0 |
| upstream_type | nvcf_pexec 63/63 (100%), integrate 0 |
| finish_reason | tool_calls 44, stop 19 |

**错误分类**：`(空)` — 本窗零错误。

**Per-key 200 延迟**（均衡, 无单 key 劣化, key4 最快）:
```
key0|11req|avg50399
key1|13req|avg34586
key2|16req|avg39652
key3|9req|avg36753
key4|14req|avg30775
```

**趋势**:
- 6h: 613 req, SR=92.8% (569 ok / 44 err)
- 3h 逐小时: 00:00=14/14(100%), 23:00=105/103(98.1%), 22:00=116/108(93.1%), 21:00=115/111(96.5%)
- 24h all_tiers_exhausted = 99 (历史累积, 本窗零)

## 决策依据汇总

本窗为**完全健康窗口**：100% SR、零错误、零 429、零 fallback、无单 key 劣化、无
pexec/integrate 失衡。所有抖动指标（ATE/429/fallback）均收敛至零，无任何参数层面的
可归因问题。按"必须有数据支撑 + 一次只改一个参数"原则，此时无任何改动依据，维持
当前参数（UPSTREAM_TIMEOUT=50, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=90,
KEY_COOLDOWN_S=30）即可。

## 下一步建议

- 24h ATE=99 仍为当日早高峰累积，若后续窗口复现 ATE 聚集（非历史静默），再评估
  TIER_COOLDOWN_S(90) 或 fast-break 阈值是否需要针对 NVCF 过载阶段的微调。
- 持续观察 per-key key_cycle_429s：k1 轮转频繁 (41) 但全成功，若 k1 未来出现错误聚集，
  需评估其 SOCKS5 出口 (7904) 是否劣化。
- 当前链路完全健康，建议保持 NOP 直至出现新的可归因退化信号。