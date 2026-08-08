# R1200: dsv4f0731_nv40666 NOP — 30min SR=90.9% ATE=3越阈值但NVCF瞬态窗口已过(近18min 100%成功), 根因外部不动作

日期: 2026-08-08 16:20 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF 链路)

## 决策：NOP（不改任何参数）

30min SR=40/44=**90.9%**，4 个错误含 **`all_tiers_exhausted` ×3**（达 R1199 设定的 ≥3/30min 动作阈值）
+ `client_gone_during_flush` ×1。虽 ATE 首次越阈值，但深入溯源判定**根因在 NVCF 外部瞬态**，
本容器无可归因调参杠杆，且当前链路已恢复完美，重创容器为修复已自我解决的问题属本末倒置。

**关键证据链**：
1. **ATE 全为 all-5-key 同质停滞** — 逐 request 查 tier_attempts，均见 5 key 同时以
   `NVCFPexecRemoteDisconnected`(~35s) / `NVCFPexecTimeout`(~30-51s) / `529_nv_overloaded`
   失败，键位无关。此症状是 **NVCF 服务端瞬时全停**，非任何单 key/单参数可调。
2. **瞬态窗口已过** — 近 18 分钟粒度查询：08:09-08:28 **每 min 全部成功 (0 err)**，3-4 req/min
   稳态。ATE 聚集时段 (06:00=5, 07:00=6, 08:00=2) 已结束，NVCF 已自我恢复。
3. **调预算不解决 ATE 计数** — all-5-key 停滞时无论预算 180 还是 150，所有 key 都失败 → 仍
   exhaust。缩短预算仅缩短 ATE 时长（更快 fallback），不降 ATE 数，且会牺牲~1% 长链成功率。
4. **改 env 需容器 recreate** — `docker update` 不支持 env，`docker restart` 不换 env；改
   `NVU_TIER_BUDGET_DSV4F0731_NV` 必须 `docker compose up -d --force-recreate`。在链上当前
   100% 成功时做此高风险操作，违背"稳定性优先"铁律。

守"改前必有数据"铁律——越阈值但无容器可归因杠杆，且危害已自愈，**不因单窗 ATE 越线而盲目动作**。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **90.91%** (40/44, 4 err, 0 timeout) |
| 错误 / DB-fallback | 4 / 0 |
| Avg / P50 / Max | 58631 / 24089 / 311258 ms |
| 429 / timeout | 0 / 0 |
| upstream_type | nvcf_pexec 44/44 (100%) — 无 integrate |
| finish_reason | tool_calls 26, stop 14 |

**错误分类**：
```
all_tiers_exhausted|3|246089    (k0×2, k2×1)  ← 达 ≥3 阈值, 但为 NVCF 瞬态停滞尾段
client_gone_during_flush|1|216412              (k2, 客户端长链主动断开, 非上游)
```

**Per-key 200 延迟**（分散, 无 key 级错误聚集）:
```
key0|7req|avg41617|max111684|err:ATE×2
key1|8req|avg21957|max54738
key2|3req|avg14414|max20137|err:ATE×1+client_gone×1
key3|11req|avg61596|max150312
key4|11req|avg39757|max125233
```

**key_cycle_429s**: 0|16, 1|24, 2|3, 3|1 — 30min **净 429=0**，key0/key1 的 16/24 次 key_cycle 429
全部被轮转到下一 key 成功，rotation 正常。tier_attempts 空。

## hm4104 fallback 日志（近 5min）

```
(无 fallback 日志)
```
本窗口 **0 次 fallback 事件** — adapter 未触发任何切换，链路平稳。

## 趋势

| 窗口 | SR | 备注 |
|---|---|---|
| 6h | **95.96%** (808/842) | 34 error, 0 timeout |
| 3h 逐小时 | 08:00 32/34=94.1%, 07:00 88/96=91.7%, 06:00 103/111=92.8% | 近3h受NVCF停滞压制 |
| 24h | all_tiers_exhausted=24 (聚集 06:00=5, 07:00=6, 08:00=2, 17:00=5) | 瞬态窗口向午间聚集 |

## 关键判断

- ATE 趋势 R1195=1→R1196=2→R1197=2→R1198=1→R1199=2→**R1200=3**，首次越 ≥3 阈值。
- 但逐 tier_attempt 溯源：5 key 同质 `RemoteDisconnected`+`Timeout`+`529_overloaded`
  = **NVCF 服务端瞬时全停**，非本容器参数所能及。
- **近 18 min 100% 成功**（逐 min 0 err）证明 NVCF 已自愈，危害已消散。
- 改 env 必须容器 recreate，属最高风险操作，且在链上当前完美时执行 = 制造新的中断。
- 6h SR=96.0% 稳定；0 DB fallback；hm4104 0 fallback 事件；全 pexec 无 integrate 分叉。

**无容器可归因的调参依据。** NVCF 瞬态停滞非本容器可控，越阈值但已自愈，NOP 正确。

## 上次修改效果 (R1199 → R1200)

R1199 SR=93.0% (40/43)，本轮 SR=90.9% (40/44)。错误 3→4：R1199 为 ATE×2+client_gone×1，
本轮 ATE×3+client_gone×1（absolute_cap/client_gone 持续，ATE +1 越阈值）。净 429=0 持续、
0 DB fallback、hm4104 fallback 事件 0 持续。R1199-R1200 均无参数变更。6h SR 96.5%→96.0%
（受 NVCF 停滞拖累，非参数退化）。**无需要修的参数。**

## 下一步建议

1. **持续观察 ATE 是否随 NVCF 恢复回落到 <3**：本轮越阈值但根因外部且已自愈。仅当 ATE 在
   **持续活动窗口**（非 tail end）仍 ≥3/30min，且伴随 hm4104 fallback 频繁化，才需评估
   `NVU_TIER_BUDGET_DSV4F0731_NV=180`。
2. **重点监控 382s 预算过冲异常**：本窗 ATE k2=382808ms（2× 180s 预算）说明部分路径未硬性
   掐预算。若此过冲重复出现（>1/窗），才考虑降预算或在代码层加硬 cap——但需先确认该 outlier
   是否因长链 attempt 压过 budget 检查所致。
3. 维持现有参数不动（UPSTREAM_TIMEOUT=50, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=90,
   KEY_COOLDOWN_S=30, NVU_KEYMGR_429_*=120, NVU_KEYMGR_CONN_*=30/60/120,
   NVU_TIER_BUDGET_DSV4F0731_NV=180），直至出现**持续活动**的可归因配置性劣化信号。