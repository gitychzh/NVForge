# R1199: dsv4f0731_nv40666 NOP — 30min SR=93.0% 3错全孤立瞬态(各<3), 0净429, 0 DB fallback, 6h SR=96.5% 健康

日期: 2026-08-08 15:58 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF 链路)

## 决策：NOP（不改任何参数）

30min SR=40/43=**93.0%**，3 个错误全为孤立瞬态（count<3），未触及"同种 ≥3/30min 才动作"阈值:
- **`all_tiers_exhausted` ×2** (均 key0, 180029ms) — 180s tier 预算烧满仍无成功，与 RN1048-1065/
  R1192-1198 已反复记录的 NVCF 全 5 key 偶发停滞瞬态同模式。**本窗 count=2，较 R1198 的 1 回升，
  但仍 <3 未触动作阈值。**
- **`client_gone_during_flush` ×1** (key2, 216412ms) — 客户端在长 tool_calls 链中主动断开，非上游
  归因 (216s 远超 180s 预算，是 client 侧放弃)。
- 0 净 429、tier_attempts 空、0 DB fallback、无 integrate、per-key 200 延迟无错误集中。

错误分布 key0×2 + key2×1，分散，无单 key 聚集劣化。守"改前必有数据"铁律——健康稳态不动作。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **93.02%** (40/43, 3 err, 0 timeout) |
| 错误 / DB-fallback | 3 / 0 |
| Avg / P50 / P95 / Max | 54398 / 32907 / 175750 / 201132 ms |
| 429 / timeout | 0 / 0 |
| upstream_type | nvcf_pexec 43/43 (100%) — 无 integrate |
| finish_reason | tool_calls 27, stop 13 |

**错误分类**（各 count<3，孤立瞬态）:
```
all_tiers_exhausted|2|180029    (均 key0 180029ms)  ← 已知 NVCF 偶发停滞瞬态 (本窗 count=2, 较 R1198=1 回升)
client_gone_during_flush|1|216412 (key2 216412ms)  ← 客户端长链主动断开, 非上游
```

**Per-key 200 延迟**（高方差但无错误集中劣化）:
```
key0|5req|avg12986|max26819   ← 承载 ATE×2 但 200 延迟最低
key1|8req|avg57376|max120114
key2|8req|avg41119|max112121  ← 承载 client_gone
key3|13req|avg49113|max112110
key4|6req|avg45213|max93610
```
key 间负载 (5-13 req) 尚均衡、延迟方差大 (13k-57k ms) 但错误分散 (k0×2, k2×1)，无 key 级劣化。
高延迟来自长 tool_calls 链 (67.5% finish_reason=tool_calls) 落在对应 key。

**key_cycle_429s**: 0|10, 1|28, 2|4, 3|1, 4|0 — 30min **净 429=0**，key1 的 28 次 key_cycle 429
全部被轮转吸收到下一 key 成功，rotation 机制正常。tier_attempts 空。

## hm4104 fallback 日志（近 5min）

```
(无 fallback 日志)
```
本窗口内 **0 次 fallback 事件** — adapter (hm4104) 未触发任何 PRIMARY/ms_gw 切换，链路平稳。

## 趋势

| 窗口 | SR | 备注 |
|---|---|---|
| 6h | **96.51%** (858/889) | 31 error, 0 timeout |
| 3h 逐小时 | 07:00 83/90=92.2%, 06:00 103/111=92.8%, 05:00 128/137=93.4% | 高流量下健康 |
| 24h | all_tiers_exhausted=25 (滚动陈旧口径) | 本窗 ATE=2，无聚集 |

## 关键判断

- 30min SR=93.0% 略低于 95% 阈值，但 3 个错误全为孤立瞬态 (count<3)，不构成可归因调参信号。
- **ATE 信号震荡未聚集**：R1195=1 → R1196=2 → R1197=2 → R1198=1 → **R1199=2**，始终在 1-2 间
  摆动，从未达 ≥3 动作阈值，不构成调参凭据。
- `client_gone_during_flush` (216s) 为客户端长链主动断开，非本容器可归因。
- 0 净 429、0 DB fallback、hm4104 0 fallback 事件、per-key 无错误集中、全 pexec → 链路健康稳态。
- 6h SR=96.5% 稳定健康。

**无调参依据。** 守"改前必有数据"铁律——SR 略低但由瞬态错误驱动，不因单窗 SR<95% 而盲目调参，
避免为调而调。

## 上次修改效果 (R1198 → R1199)

R1198 SR=96.4% (54/56)，本轮 SR=93.0% (40/43)。请求量 56→43（波动）。错误数 2→3：R1198 为
ATE×1+absolute_cap×1，本轮 ATE×2+client_gone×1（absolute_cap 消失，client_gone 出现）。
净 429=0 持续、0 DB fallback、hm4104 fallback 事件 2→0 明显改善。ATE 1→2 属震荡，未达聚集。
R1198-R1199 均无参数变更。6h SR 96.7%→96.5%，仍健康。**无需要修的参数。**

## 下一步建议

1. **持续观察 all_tiers_exhausted**：本窗回升至 2 (R1195=1→R1196=2→R1197=2→R1198=1→R1199=2)，
   仍未达 ≥3 聚集阈值。仅当未来窗口 ATE 达 **≥3/30min** 或伴随 hm4104 fallback 频繁化，才评估
   TIER_TIMEOUT_BUDGET_S=180 是否过长（长 tool_calls 链常烧满预算）。当前 2 次孤立，继续观察。
2. **client_gone_during_flush**：216s 客户端断开，若未来频繁出现 (>3/窗) 需评估是否长 tool_calls
   链在 180s 预算内无法完成导致客户端放弃——但当前 count=1 孤立，不动作。
3. 维持现有参数不动（UPSTREAM_TIMEOUT=50, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=90,
   KEY_COOLDOWN_S=30, NVU_KEYMGR_429_*=120, NVU_KEYMGR_CONN_*=30/60/120,
   NVU_TIER_BUDGET_DSV4F0731_NV=180），直至出现可归因的配置性劣化信号。