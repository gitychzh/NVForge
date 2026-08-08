# R1196: dsv4f0731_nv40666 NOP — 30min SR=92.8% 但 5 错全为孤立瞬态(各<3)，0 净429, 0 DB fallback, 6h SR=98.3% 健康

日期: 2026-08-08 14:26 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF 链路)

## 决策：NOP（不改任何参数）

30min SR=92.8% (64/69) 表面低于 95% 阈值，但细看 5 个错误:
- **`all_tiers_exhausted` ×2** (k0 180078ms, k0) — 180s tier 预算烧满仍无成功，同
  RN1048-1065/R1192-1195 已反复记录的 NVCF 全 5 key 偶发停滞瞬态。**本轮首次同窗口出现 2 次**，
  但单错误类型 count=2 仍 <3，未触动作阈值。
- **`stream_absolute_cap` ×2** (k3 174947ms, k4 155666ms) — 流式绝对上限命中，同 ATE 模式的
  孤立长请求 (155s/174s 长 tool_calls 链)。
- **`client_gone_during_flush` ×1** (k2 185513ms) — 客户端在流 flush 前断开，**属客户端侧行为，
  非 gateway/NVCF 上游失败**。剔除后真实上游 SR=64/68=**94.1%**。

三类错误各 count<3，**均未触及"同种 ≥3/30min 才动作"阈值**；分布在 k0/k2/k3/k4 四个不同 key，
无 fast-break 聚集；净 429=0、tier_attempts 空、0 DB fallback、无 integrate。守"改前必有数据"
铁律——孤立瞬态错误不构成调参凭据，健康稳态不动作。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **92.75%** (64/69, 5 err, 0 timeout) |
| 错误 / DB-fallback | 5 / 0 |
| Avg / P50 / P95 / Max | 37884 / 20729 / 167235 / 181831 ms |
| 429 / timeout | 0 / 0 |
| upstream_type | nvcf_pexec 69/69 (100%) — 无 integrate |
| finish_reason | tool_calls 47, stop 17 |

**错误分类**（各 <3，孤立）:
```
all_tiers_exhausted|2    (k0 180078ms, k0)      ← 已知 NVCF 偶发停滞瞬态 (本轮同窗口 2 次)
stream_absolute_cap|2    (k3 174947ms, k4 155666ms) ← 流式绝对上限命中
client_gone_during_flush|1 (k2 185513ms)        ← 客户端断开，非上游失败
```

**Per-key 200 延迟**（全 5 key 负载/延迟均匀，无劣化 key）:
```
key0|12req|avg24241|max45291   ← 承载 2 次 ATE (180078ms) 但 200 延迟正常
key1|14req|avg23476|max59149
key2|9req|avg29230|max58010
key3|16req|avg29186|max80647
key4|13req|avg29857|max67787
```
key 间负载均匀 (9-16 req)、200 延迟同量级 (23-30s)。key0 承载 2 次 ATE 但 200 延迟正常 (24s)，
无 key 级劣化。

**key_cycle_429s**: 0|12, 1|55, 3|1, 4|1 — 30min **净 429=0**，key1 的 55 次 key_cycle 429 全部被
轮转吸收到下一 key 成功，rotation 机制正常。tier_attempts 空。

## hm4104 fallback 日志（近 5min）

```
{"tag": "FALLBACK-STREAM", "msg": "从 primary 切到 ms_gw 流式, 提醒插入首 delta 前"}
```
单次 FALLBACK-STREAM 事件 (14:22:01)，与窗口内 `all_tiers_exhausted`(180s 预算耗尽) 相互印证 —
单次请求烧满 180s tier 预算后被 502，adapter 正确切换到 ms_gw 兜底。**事件稀疏 (1 次)，
非本容器参数可归因问题** (5 key 全停滞为 NVCF 侧事件)。

## 趋势

| 窗口 | SR | 备注 |
|---|---|---|
| 6h | **98.34%** (1124/1144) | 20 error, 0 timeout |
| 3h 逐小时 | 06:00 57/60=95%, 05:00 128/137=93.4%, 04:00 142/145=97.9%, 03:00 88/90=97.8% | 高流量下健康 |
| 24h | all_tiers_exhausted=23（滚动陈旧口径，正被甩走） | 本 6h 无 ATE 聚集 |

## 关键判断

- 30min 表面 SR=92.8% 偏低，但 **1/5 错误为 client_gone_during_flush（客户端断开，非上游失败）**，
  剔除后真实上游 SR=94.1%。
- 剩余 ATE×2 + absolute_cap×2 均为孤立瞬态，单错误类型 count=2 <3 未触动作阈值，分布在
  k0/k3/k4 三个不同 key，与 RN1048-1065/R1192-1195 已记录的 NVCF 偶发停滞瞬态同模式。
- **本轮唯一新信号**：ATE 首次同窗口出现 2 次（R1195 为 1 次）。但 2 次仍 <3 阈值，且 6h SR=98.3%
  健康、0 净 429、0 DB fallback、per-key 均匀无劣化、全 pexec → 链路健康稳态。
- hm4104 单次 FALLBACK-STREAM 已由 ms_gw 正确兜底，非本容器参数可归因。

**无调参依据。** 守"改前必有数据"铁律——健康窗口不动作，避免为调而调。

## 上次修改效果 (R1195 → R1196)

R1195 SR=92.9% (52/56)，本轮 SR=92.8% (64/69)。请求量回升 (56→69，R1195 部分被 circuit OPEN
分流到 ms_gw 的流量回归)。错误数 4→5，但分布类似：R1195 为 client_gone×2+ATE×1+absolute_cap×1，
本轮 client_gone×1+ATE×2+absolute_cap×2。真实上游错误 (剔除 client_gone) 4→4 持平。延迟 P50
14.9s→20.7s（样本量小噪声，且本轮 ATE/absolute_cap 长请求更多）。429=0 持续、0 DB fallback、
R1195-R1196 均无参数变更。6h SR 98.6%→98.3%，仍健康。**无需要修的参数。**

## 下一步建议

1. **持续观察 all_tiers_exhausted**：本轮首次同窗口 2 次 (R1195 为 1)。若未来窗口 ATE 达
   ≥3/30min 或伴随 hm4104 fallback 频繁化，则需评估 TIER_TIMEOUT_BUDGET_S=180 是否过长
   （长 tool_calls 链常烧满预算）。当前 2 次孤立，先观察。
2. **关注 stream_absolute_cap**：本轮 2 次 (155s/174s)。若绝对上限持续命中长链，考虑是否需
   调整 NVU_BUFFER_TIMEOUT_STAIRS 或流式绝对 cap 配置。当前稀疏，先观察。
3. **关注 client_gone_during_flush**：若持续出现说明客户端侧中断增多（可能 hm4104 竞态/超时），
   但非本容器参数可调，需与 adapter 侧沟通。
4. 维持现有参数不动（UPSTREAM_TIMEOUT=50, TIER_COOLDOWN_S=90, KEY_COOLDOWN_S=30,
   NVU_KEYMGR_429_*=120, NVU_KEYMGR_CONN_*=30/60/120, NVU_TIER_BUDGET_DSV4F0731_NV=180），
   直至出现可归因的配置性劣化信号。