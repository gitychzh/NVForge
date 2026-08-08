# R1194: dsv4f0731_nv40666 NOP — 30min SR=96.2%, 3 孤立错误 + 首现 content_filter zombie fallback (0 429, 0 DB fallback)

日期: 2026-08-08 13:33 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF 链路)

## 决策：NOP（不改任何参数）

SR=96.2% (>95% 阈值)、0 429、0 DB 级 fallback、per-key 均衡无劣化 key、6h SR=99.2%。
3 个错误均为**孤立单事件**（NVStream_IncompleteRead×2 分布 k1/k2、zombie_empty_completion×1 在 k0），
各类型 count<3 未触 ≥3/30min 动作阈值，被 key 循环正常兜住。本轮新增 **content_filter zombie
fallback 信号**（hm4104 检测到 primary 流 content_filter zombie 切 ms_gw），属 NVCF 侧内容过滤
质量问题、已被 adapter 的 R840 zombie 检测正确兜住（fallback 成功、无用户可见失败），**无法通过
gateway 超时/冷却类参数缓解**——非调参凭据。守"改前必有数据"铁律，健康窗口不动作。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **96.2%** (75/78, 3 error) |
| 错误 / DB-fallback | 3 / 0 |
| Avg / P50 / P95 / Max | 26541 / 14864 / 91626 / 107599 ms |
| 429 | 0 |
| upstream_type | nvcf_pexec 78/78 (100%) — 全 pexec，无 integrate |
| finish_reason | tool_calls 57, stop 18 |

**错误分类**（各 <3，孤立无聚集）:
```
NVStream_IncompleteRead|2   (key1 avg35655ms, key2 avg66546ms)
zombie_empty_completion|1   (key0 avg39780ms)
```

**Per-key 200 延迟**（全 5 key 负载均匀 10-18 req，延迟同量级 11.5-36.4s）:
```
key0|18req|avg24525
key1|11req|avg32526
key2|19req|avg36350
key3|17req|avg19002
key4|10req|avg11529
```

**Per-key 错误**: key0 zombie×1, key1 IncompleteRead×1, key2 IncompleteRead×1 — 无 key 劣化
（各 key 单事件，不构成 fast-break 触发）。

**tier_attempts**: 空（30min 内无 key 切换失败）。
**key_cycle_429s**: 0|23, 1|55 — 30min 429=0，验明无 429/循环压力。

## ◀ 新增信号：content_filter zombie fallback（hm4104 近 5min 日志）

```
CONTENT_FILTER_ZOMBIE: primary 流中检测到 content_filter (R840 zombie), 切 ms_gw fallback
PRIMARY-ZOMBIE-FALLBACK: nv_gw 返回 content_filter zombie, 切 ms_gw fallback 流式
FALLBACK-STREAM: 从 primary 切到 ms_gw 流式, 提醒插入首 delta 前  (×2)
PRIMARY-BREAKER-SKIP-STREAM: primary 流式跳过 (circuit OPEN 或 fallback 冷却), 直走 fallback
```

**解读**: 本轮首次出现 hm4104 adapter 级 content_filter zombie 检测并切换 fallback。
这是**端到端降级事件**（primary 流返回 content_filter zombie → 切 ms_gw 兜住），但:
1. 已被 hm4104 的 R840 zombie 检测机制**正确兜住**（fallback 成功 → ms_gw，无用户可见失败）。
2. 与 30min 窗口的 `zombie_empty_completion`(k0) 相互印证 —— NVCF 上游近期偶发 content_filter zombie。
3. 根因在 **NVCF 侧内容过滤**，非 gateway 参数（超时/冷却/fastbreak 均无法减少 content_filter 事件）。
   唯一可调点 NVU_EMPTY_200_FASTBREAK=3 针对的是"空 200"，非"content_filter 200"。
4. 事件稀疏（2 次/5min、窗口 zombie_empty_completion 仅 1）——尚不构成频发，先观察。

## 趋势

- **6h**: 1320/1309 → **SR=99.2%**，11 失败, 0 fallback
- **3h 逐小时**: 05:00 85(96.5%,3err), 04:00 145(97.9%,3err), 03:00 168(98.2%,3err),
  02:00 102(99.0%,1err) — 高流量下 SR 稳定 ≥96.5%
- **24h all_tiers_exhausted**: 26（较 R1193 的 27 **下降 3.7%**，均被 fallback 兜住，非本窗口信号）

## 关键判断

- 30min SR=96.2%，3 个错误均为孤立单事件（IncompleteRead×2 + zombie×1），分布在 k0/k1/k2
  三个不同 key，无 fast-break 聚集（阈值均未触及）。按"同种 ≥3/30min 才动作"预置对策，
  单事件被 key 循环兜住，不足为凭。
- 429=0、0 DB fallback、per-key 负载均匀 (10-19/key)、延迟同量级 (11.5-36.4s)——无劣化 key、
  无 integrate、全 pexec。
- **content_filter zombie fallback 首次出现**是本窗口唯一值得关注的新信号，但根因在 NVCF 侧、
  已被 adapter 正确兜住、事件稀疏 —— 记录为观察项，不调参（无 gateway 参数可缓解）。
- 6h SR=99.2% + 高流量时段逐小时 SR ≥96.5% → 整体链路健康稳态。

**无任何调参依据。** 守"改前必有数据"铁律——健康窗口不动作，避免为调而调。

## 上次修改效果 (R1193 → R1194)

R1193 SR=97.3%、2 孤立 IncompleteRead。本轮 SR=96.2%（78 请求，3 孤立错误），为正常噪声
（窗口请求量 75→78，错误类型中新增 zombie×1 与 hm4104 content_filter fallback 相互印证）。
延迟 P50 14.8s→14.9s，各 key 均在 pexec 正常量级。429=0、0 DB fallback、R1193-R1194 均无参数变更。
6h SR 99.3%→99.2%，仍健康。**无需要修的参数。**

## 下一步建议

1. **持续观察 content_filter zombie 信号**：若未来窗口 `zombie_empty_completion` 或 hm4104
   content_filter fallback 在 30min 内 ≥3 次，则需评估——但注意根因在 NVCF 侧内容过滤，
   gateway 侧无直接参数可调（NVU_EMPTY_200_FASTBREAK 针对空 200 而非 content_filter）。
2. 若 zombie 持续频发导致 hm4104 频繁 fallback 到 ms_gw（影响端到端质量），可考虑与 hm4104
   adapter 侧沟通其 zombie 重试策略，而非修改本容器参数。
3. 维持现有参数不动（UPSTREAM_TIMEOUT=50, TIER_COOLDOWN_S=90, KEY_COOLDOWN_S=30,
   NVU_KEYMGR_429_*=120, NVU_KEYMGR_CONN_*=30/60, NVU_TIER_BUDGET_DSV4F0731_NV=180），
   直至出现可归因的配置性劣化信号。