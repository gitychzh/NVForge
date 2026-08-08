# R1197: dsv4f0731_nv40666 NOP — 30min SR=90.2% 但4错全孤立瞬态(各<3), 0净429, 0 DB fallback, 6h SR=97.8% 健康

日期: 2026-08-08 14:48 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF 链路)

## 决策：NOP（不改任何参数）

30min SR=90.2% (37/41) 表面低于 95% 阈值，但细看 4 个错误:
- **`all_tiers_exhausted` ×2** (k0 178250ms) — 180s tier 预算烧满仍无成功，同
  RN1048-1065/R1192-1196 已反复记录的 NVCF 全 5 key 偶发停滞瞬态。**连续第 2 个窗口同为 2 次**
  (R1196 也是 2)，但单错误类型 count=2 仍 <3，未触动作阈值。
- **`client_gone_during_flush` ×1** (k0 181201ms) — 客户端在流 flush 前断开，**属客户端侧行为，
  非 gateway/NVCF 上游失败**。剔除后真实上游 SR=37/40=**92.5%**。
- **`stream_absolute_cap` ×1** (k3 174947ms) — 流式绝对上限命中，孤立长 tool_calls 链。

三类错误各 count<3，**均未触及"同种 ≥3/30min 才动作"阈值**；0 净 429、tier_attempts 空、0 DB
fallback、无 integrate。守"改前必有数据"铁律——孤立瞬态错误不构成调参凭据，健康稳态不动作。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **90.24%** (37/41, 4 err, 0 timeout) |
| 错误 / DB-fallback | 4 / 0 |
| Avg / P50 / P95 / Max | 56518 / 27347 / 179891 / 252691 ms |
| 429 / timeout | 0 / 0 |
| upstream_type | nvcf_pexec 41/41 (100%) — 无 integrate |
| finish_reason | tool_calls 27, stop 10 |

**错误分类**（各 <3，孤立）:
```
all_tiers_exhausted|2    (k0 178250ms)      ← 已知 NVCF 偶发停滞瞬态 (连续第2窗口=2)
client_gone_during_flush|1 (k0 181201ms)    ← 客户端断开，非上游失败
stream_absolute_cap|1     (k3 174947ms)     ← 流式绝对上限命中
```

**Per-key 200 延迟**（高方差但无错误集中劣化 key）:
```
key0|5req|avg8134|max15786    ← 承载 2 次 ATE (178250ms) 但 200 延迟最低
key1|7req|avg25311|max48063
key2|7req|avg49794|max113939
key3|8req|avg37395|max90927   ← 承载 stream_absolute_cap 但 200 延迟正常
key4|10req|avg73903|max208631 ← 负载最高、延迟最高，但 0 错误
```
key 间负载 (5-10 req)、延迟方差大 (8k-74k ms) 但 **错误仅集中在 k0/k3，且 k4 最高延迟对应 0 错误**
——高延迟来自长 tool_calls 链 (73% finish_reason=tool_calls) 落在对应 key，非 key 级劣化。

**key_cycle_429s**: 0|7, 1|32, 2|1, 4|1 — 30min **净 429=0**，key1 的 32 次 key_cycle 429 全部被
轮转吸收到下一 key 成功，rotation 机制正常。tier_attempts 空。

## hm4104 fallback 日志（近 5min）

```
{"tag": "PRIMARY-FAIL-STREAM", "msg": "nv_gw 流式 server_5xx status=502 after 176616ms, 切 fallback: upstream 502"}
{"tag": "FALLBACK-FAIL-STREAM", "msg": "ms_gw 流式 timeout status=0 after 246689ms: header/ttfb timeout after 70.0s"}
```
2 次 sporadic 事件 (非读取窗口内的 DB fallback，是 hm4104 adapter 自身 CC 链):
- 第 1 次 PRIMARY-FAIL-STREAM 502 after 176s ≈ TIER_TIMEOUT_BUDGET_S=180s —— 与窗口内
  `all_tiers_exhausted`(180s 预算耗尽) 相互印证，单请求烧满预算后被 502，adapter 切 ms_gw 兜底。
- 第 2 次 FALLBACK-FAIL-STREAM 为 ms_gw 侧 70s ttfb 超时，属 ms_gw 兜底失败，非本容器 (nv_gw) 归因。
事件稀疏 (R1196 为 1 次，本轮 2 次)，仍为 adapter CC 链的间歇触发，非本容器参数可归因问题。

## 趋势

| 窗口 | SR | 备注 |
|---|---|---|
| 6h | **97.80%** (1022/1045) | 23 error, 0 timeout |
| 3h 逐小时 | 06:00 79/85=92.9%, 05:00 128/137=93.4%, 04:00 142/145=97.9%, 03:00 40/41=97.6% | 高流量下健康 |
| 24h | all_tiers_exhausted=24（滚动陈旧口径，正被甩走） | 本 6h 无 ATE 聚集 |

## 关键判断

- 30min 表面 SR=90.2% 偏低，但 **1/4 错误为 client_gone_during_flush（客户端断开，非上游失败）**，
  剔除后真实上游 SR=92.5%。
- 剩余 ATE×2 + absolute_cap×1 均为孤立瞬态，单错误类型 count=2 <3 未触动作阈值，分布在
  k0/k3 两个 key，与 RN1048-1065/R1192-1196 已记录的 NVCF 偶发停滞瞬态同模式。
- **连续第 2 个窗口 ATE=2**（R1195=1 → R1196=2 → R1197=2），信号在累积但未达 ≥3 动作阈值，
  6h SR=97.8% 健康、0 净 429、0 DB fallback、per-key 无错误集中、全 pexec → 链路健康稳态。
- hm4104 2 次 sporadic fallback 事件 (PRIMARY 502 后 ms_gw 兜底也超时) 为 adapter CC 链间歇触发，
  与 ATE 预算耗尽模式印证，非本容器参数可归因。

**无调参依据。** 守"改前必有数据"铁律——健康窗口不动作，避免为调而调。

## 上次修改效果 (R1196 → R1197)

R1196 SR=92.8% (64/69)，本轮 SR=90.2% (37/41)。请求量回落 (69→41，流量波动)。错误数 5→4，分布
类似：R1196 为 client_gone×1+ATE×2+absolute_cap×2，本轮 client_gone×1+ATE×2+absolute_cap×1。
真实上游错误 (剔除 client_gone) 4→3 略降。延迟 P50 20.7s→27.3s（样本量小噪声，且本轮 k4 长
tool_calls 链多）。429=0 持续、0 DB fallback、R1196-R1197 均无参数变更。6h SR 98.3%→97.8%，仍健康。
**无需要修的参数。**

## 下一步建议

1. **持续观察 all_tiers_exhausted**：连续 2 窗口 ATE=2 (R1196/R1197)，R1195=1。若未来窗口 ATE 达
   **≥3/30min** 或伴随 hm4104 fallback 频繁化，则需评估 TIER_TIMEOUT_BUDGET_S=180 是否过长
   （长 tool_calls 链常烧满预算）。当前 2 次孤立，先观察。
2. **关注 k4 高延迟**：k4 avg 73.9s/max 208s 但 0 错误。若后续 k4 开始出现错误聚集，需检查其
   SOCKS5 代理 (7904) 或考虑冷却标记。当前无错误，仅观察。
3. **hm4104 ms_gw 兜底失败**：FALLBACK-FAIL-STREAM 为 ms_gw 70s ttfb 超时，属 ms_gw 侧问题，
   非本容器 (nv_gw) 可调。若频繁出现需与 ms_gw 侧沟通。
4. 维持现有参数不动（UPSTREAM_TIMEOUT=50, TIER_COOLDOWN_S=90, KEY_COOLDOWN_S=30,
   NVU_KEYMGR_429_*=120, NVU_KEYMGR_CONN_*=30/60/120, NVU_TIER_BUDGET_DSV4F0731_NV=180），
   直至出现可归因的配置性劣化信号。