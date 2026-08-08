# R1198: dsv4f0731_nv40666 NOP — 30min SR=96.4% 2错全孤立瞬态(各=1), 0净429, 0 DB fallback, 6h SR=96.7% 健康

日期: 2026-08-08 15:48 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF 链路)

## 决策：NOP（不改任何参数）

30min SR=54/56=**96.4%**（>95% 阈值），2 个错误全为孤立瞬态（各 count=1 <3）:
- **`all_tiers_exhausted` ×1** (k0 180031ms) — 180s tier 预算烧满仍无成功，与 RN1048-1065/
  R1192-1197 已反复记录的 NVCF 全 5 key 偶发停滞瞬态同模式。**本窗 count=1，较 R1197 的 2 下降**。
- **`stream_absolute_cap` ×1** (k1 154359ms) — 流式绝对上限命中，孤立长 tool_calls 链。
- 0 净 429、tier_attempts 空、0 DB fallback、无 integrate、per-key 200 延迟无错误集中。

各类错误 count=1 <3，**未触及"同种 ≥3/30min 才动作"阈值**。守"改前必有数据"铁律——健康稳态
不动作。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **96.43%** (54/56, 2 err, 0 timeout) |
| 错误 / DB-fallback | 2 / 0 |
| Avg / P50 / P95 / Max | 47115 / 30719 / 137162 / 165911 ms |
| 429 / timeout | 0 / 0 |
| upstream_type | nvcf_pexec 56/56 (100%) — 无 integrate |
| finish_reason | tool_calls 41, stop 13 |

**错误分类**（各=1，孤立瞬态）:
```
all_tiers_exhausted|1|180031    (k0 180031ms)  ← 已知 NVCF 偶发停滞瞬态 (本窗 count=1, 较 R1197=2 降)
stream_absolute_cap|1|154359    (k1 154359ms)  ← 流式绝对上限命中
```

**Per-key 200 延迟**（高方差但无错误集中劣化）:
```
key0|9req|avg27418|max82230   ← 承载 ATE (180031ms) 但 200 延迟最低
key1|10req|avg47076|max115253 ← 承载 absolute_cap 但 200 延迟正常
key2|13req|avg49293|max135254
key3|13req|avg50660|max112110
key4|9req|avg31904|max65358
```
key 间负载 (9-13 req) 均衡、延迟方差大 (27k-51k ms) 但 **错误仅 k0/k1 各 1 次，无 key 级劣化**。
高延迟来自长 tool_calls 链 (73% finish_reason=tool_calls) 落在对应 key。

**key_cycle_429s**: 0|9, 1|41, 2|3, 3|3, 4|0 — 30min **净 429=0**，key1 的 41 次 key_cycle 429
全部被轮转吸收到下一 key 成功，rotation 机制正常。tier_attempts 空。

## hm4104 fallback 日志（近 5min）

```
{"tag": "PRIMARY-FAIL-STREAM", "msg": "nv_gw 流式 server_5xx status=502 after 180039ms, 切 fallback: upstream 502"}
{"tag": "FALLBACK-FAIL-STREAM", "msg": "ms_gw 流式 timeout status=0 after 250113ms: header/ttfb timeout after 70.0s"}
```
2 次 sporadic 事件 (非读取窗口内的 DB fallback，是 hm4104 adapter 自身 CC 链):
- 第 1 次 PRIMARY-FAIL-STREAM 502 after 180039ms ≈ TIER_TIMEOUT_BUDGET_S=180s —— 与窗口内
  `all_tiers_exhausted`(180s 预算耗尽) 相互印证，单请求烧满预算后被 502，adapter 切 ms_gw 兜底。
- 第 2 次 FALLBACK-FAIL-STREAM 为 ms_gw 侧 70s ttfb 超时，属 ms_gw 兜底失败，非本容器 (nv_gw) 归因。
事件稀疏 (R1197 为 2 次，本轮仍 2 次)，仍为 adapter CC 链间歇触发，非本容器参数可归因问题。

## 趋势

| 窗口 | SR | 备注 |
|---|---|---|
| 6h | **96.74%** (891/921) | 30 error, 0 timeout |
| 3h 逐小时 | 07:00 79/84=94.0%, 06:00 103/111=92.8%, 05:00 128/137=93.4%, 04:00 19/20=95.0% | 高流量下健康 |
| 24h | all_tiers_exhausted=25 (滚动陈旧口径) | 本窗 ATE=1，无聚集 |

## 关键判断

- 30min SR=96.4% **>95% 阈值**，链路健康稳态。
- 2 个错误 (ATE×1 + absolute_cap×1) 均为孤立瞬态，count=1 <3 未触动作阈值，分布在 k0/k1 两个
  key，与 RN1048-1065/R1192-1197 已记录的 NVCF 偶发停滞瞬态同模式。
- **ATE 信号回落**：R1195=1 → R1196=2 → R1197=2 → **R1198=1**，未演化成连续聚集，不构成调参凭据。
- 0 净 429、0 DB fallback、per-key 无错误集中、全 pexec → 链路健康稳态。
- hm4104 2 次 sporadic fallback 事件 (PRIMARY 502 后 ms_gw 兜底也超时) 为 adapter CC 链间歇触发，
  与 ATE 预算耗尽模式印证，非本容器参数可归因。

**无调参依据。** 守"改前必有数据"铁律——健康窗口不动作，避免为调而调。

## 上次修改效果 (R1197 → R1198)

R1197 SR=90.2% (37/41)，本轮 SR=96.4% (54/56)。请求量回升 (41→56)。错误数 4→2，分布收敛：
R1197 为 client_gone×1+ATE×2+absolute_cap×1，本轮 ATE×1+absolute_cap×1（client_gone 消失）。
真实上游错误 4→2 明显下降。延迟 P50 27.3s→30.7s（样本噪声，长 tool_calls 链占比高）。429=0
持续、0 DB fallback、R1197-R1198 均无参数变更。6h SR 97.8%→96.7%，仍健康。
**无需要修的参数。**

## 下一步建议

1. **持续观察 all_tiers_exhausted**：本窗回落至 1 (R1195=1→R1196=2→R1197=2→R1198=1)，未成聚集。
   仅当未来窗口 ATE 达 **≥3/30min** 或伴随 hm4104 fallback 频繁化，才评估 TIER_TIMEOUT_BUDGET_S=180
   是否过长（长 tool_calls 链常烧满预算）。当前 1 次孤立，继续观察。
2. **hm4104 ms_gw 兜底失败**：FALLBACK-FAIL-STREAM 为 ms_gw 70s ttfb 超时，属 ms_gw 侧问题，
   非本容器 (nv_gw) 可调。若频繁出现需与 ms_gw 侧沟通。
3. 维持现有参数不动（UPSTREAM_TIMEOUT=50, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=90,
   KEY_COOLDOWN_S=30, NVU_KEYMGR_429_*=120, NVU_KEYMGR_CONN_*=30/60/120,
   NVU_TIER_BUDGET_DSV4F0731_NV=180），直至出现可归因的配置性劣化信号。