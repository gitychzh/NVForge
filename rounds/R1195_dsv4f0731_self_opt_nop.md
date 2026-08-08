# R1195: dsv4f0731_nv40666 NOP — 30min SR=92.9% 但 2/4 错误为 client_gone(客户端侧)，真实上游 SR=96.3%，孤立事件无聚集 (0 429, 0 fallback)

日期: 2026-08-08 14:07 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF 链路)

## 决策：NOP（不改任何参数）

30min SR=92.9% (52/56) 表面低于 95% 阈值，但细看 4 个错误:
- **`client_gone_during_flush` ×2** (k2 185513ms, k4 193737ms) — 客户端在流 flush 前断开，
  **属客户端侧行为，非 gateway/NVCF 上游失败**。剔除后真实上游 SR=52/54=**96.3%**。
- **`all_tiers_exhausted` ×1** (k0 180056ms) — 180s tier 预算烧满仍无成功，同 RN1065/R1194
  已反复记录的 NVCF 全 5 key 偶发停滞瞬态。
- **`stream_absolute_cap` ×1** (k3 172928ms) — 流式绝对上限命中，同 ATE 模式的孤立长请求。

三类错误各 count<3，**均未触及"同种 ≥3/30min 才动作"阈值**；分布在 k0/k2/k3/k4 四个不同 key，
无 fast-break 聚集；429=0、tier_attempts 空、0 DB fallback、无 integrate。守"改前必有数据"
铁律——孤立瞬态错误不构成调参凭据，健康稳态不动作。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **92.86%** (52/56, 4 err, 0 timeout) |
| 错误 / DB-fallback | 4 / 0 |
| Avg / P50 / P95 / Max | 40986 / 18853 / 174710 / 189214 ms |
| 429 / timeout | 0 / 0 |
| upstream_type | nvcf_pexec 56/56 (100%) — 无 integrate |
| finish_reason | tool_calls 38, stop 14 |

**错误分类**（各 <3，孤立）:
```
client_gone_during_flush|2   (k2 185513ms, k4 193737ms) ← 客户端断开，非上游失败
all_tiers_exhausted|1        (k0 180056ms) ← 已知 NVCF 偶发停滞瞬态
stream_absolute_cap|1        (k3 172928ms) ← 流式绝对上限命中
```

**Per-key 200 延迟**（全 5 key 负载/延迟均匀，无劣化 key）:
```
key0|15req|avg36229|max91524
key1|12req|avg33248|max111722
key2|8req|avg26689|max68773
key3|13req|avg25299|max75203
key4|4req|avg19544|max28282
```
key4 负载较低 (4 req) 但延迟最优 (19.5s)，无异常。key0 承载 ATE 单事件但 200 延迟正常。

**key_cycle_429s**: 0|17, 1|36, 2|2, 4|1 — 30min 429=0，验明无 429/循环压力。tier_attempts 空。

## hm4104 fallback 日志（近 5min）

```
PRIMARY-FAIL-STREAM: nv_gw 流式 server_5xx status=502 after 180065ms, 切 fallback
FALLBACK-STREAM: 从 primary 切到 ms_gw (×2)
PRIMARY-BREAKER-SKIP-STREAM: primary 流式跳过 circuit OPEN/fallback 冷却 (×2)
```

**解读**: 单次 502 after 180065ms = 一个请求烧满 180s tier 预算后被返回 502，与窗口内
`all_tiers_exhausted`(180056ms) 相互印证 —— 同一 NVCF 偶发停滞瞬态。hm4104 已正确切换到
ms_gw 兜住（fallback 成功），随后 circuit breaker 短暂 OPEN 期间直走 ms_gw。这是**本容器
上游偶发瞬态**，非本容器参数可归因问题（5 key 全停滞为 NVCF 侧事件，超时/冷却/预算对
单次全 key 停滞无缓解原理）。事件稀疏（1 次 502），先观察。

## 趋势

| 窗口 | SR | 备注 |
|---|---|---|
| 6h | **98.58%** (1181/1198) | 17 error, 0 timeout |
| 3h 逐小时 | 06:00 17/17=100%, 05:00 128/137=93.4%, 04:00 142/145=97.9%, 03:00 142/144=98.6% | 05:00 的 9 错中有 client_gone，高流量下仍健康 |
| 24h | all_tiers_exhausted=25（滚动陈旧口径，正被甩走） | 本 6h 无 ATE 聚集 |

## 关键判断

- 30min 表面 SR=92.9% 偏低，但 **2/4 错误为 client_gone_during_flush（客户端断开，非上游失败）**，
  剔除后真实上游 SR=96.3%。
- 剩余 ATE×1 + absolute_cap×1 均为孤立单事件，分布在 k0/k3 不同 key，count<3 未触动作阈值，
  与 RN1048-1065/R1192-1194 已记录的 NVCF 偶发停滞瞬态同模式。
- 429=0、0 DB fallback、per-key 均匀无劣化、无 integrate、全 pexec、6h SR=98.58% → 链路健康稳态。
- hm4104 单次 502-after-180s 已由 fallback 正确兜住，非本容器参数可归因。

**无任何调参依据。** 守"改前必有数据"铁律——健康窗口不动作，避免为调而调。

## 上次修改效果 (R1194 → R1195)

R1194 SR=96.2% (75/78)，本轮 SR=92.9% (52/56)。窗口请求量下降 (78→56，部分被 hm4104 502
后 circuit OPEN 分流到 ms_gw)，错误数 3→4。但 R1194 的错误为 IncompleteRead×2+zombie×1
（上游质量问题），本轮 4 错中 2 个为 client_gone（客户端侧），真实上游错误仅 2 个 →
实质上游质量基本持平甚至略优。延迟 P50 14.9s→18.9s（样本量小噪声）。429=0 持续、0 DB fallback、
R1194-R1195 均无参数变更。6h SR 99.2%→98.6%，仍健康。**无需要修的参数。**

## 下一步建议

1. **持续观察 ATE/absolute_cap/502-after-180s**：若未来窗口同类事件 ≥3/30min 或 hm4104
   fallback 频繁化，则需评估 TIER_TIMEOUT_BUDGET_S=180 是否过长（长 tool_calls 链常烧满预算）。
   当前单次偶发，先观察。
2. **关注 client_gone_during_flush**：若持续出现说明客户端侧中断增多（可能 hm4104 竞态/超时），
   但非本容器参数可调，需与 adapter 侧沟通。
3. 维持现有参数不动（UPSTREAM_TIMEOUT=50, TIER_COOLDOWN_S=90, KEY_COOLDOWN_S=30,
   NVU_KEYMGR_429_*=120, NVU_KEYMGR_CONN_*=30/60, NVU_TIER_BUDGET_DSV4F0731_NV=180），
   直至出现可归因的配置性劣化信号。