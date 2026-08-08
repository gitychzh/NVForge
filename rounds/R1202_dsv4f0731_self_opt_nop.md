# R1202: dsv4f0731_nv40666 NOP — 30min SR=95.1% 越阈值但错误全为NVCF外部瞬态(ATE×1+cap×1+IncompleteRead×1), 无容器可归因杠杆, 链路健康

日期: 2026-08-08 22:38 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DeepSeek V4 Pro via NVCF pexec)

## 决策：NOP（不改任何参数）

30min SR=58/61=**95.1%** (达 NOP 阈值 ≥95%), 3 错误均为 **NVCF 外部瞬态**, 无本容器可归因杠杆。
与 R1191-R1201 反复判定的同一外部根因模式完全一致。

**证据链**：
1. **all_tiers_exhausted ×1 (k0, ~180s)** — 此错误 = all-5-key 同质停滞烧满 180s budget 后
   exhaust。逐 request 均为键位无关的全 key 同时失败, 属 **NVCF 服务端全停**, 非任何单 key/单参数可调。
2. **stream_absolute_cap ×1 (k0, ~176s)** — 流达绝对上限, NVCF 流级瞬态。
3. **NVStream_IncompleteRead ×1 (k3)** — 流被上游 NVCF 截断, 单次瞬态, 非配置性。
4. **净 429 = 0** — key_cycle_429s (k0=25, k1=33) 为内部轮转吸收计数, 未产生请求级 429。
5. **hm4104 近 5min 无 fallback 日志** — 当前链路健康, 未降级到 ms_gw。
6. **无 key 级错误聚集** — 错误散布 k0×2/k3×1, 非某单 key 劣化, 无 SOCKS5 代理侧问题可调。
7. **tier_attempts 空** — 无 key 间切换异常模式。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **95.08%** (58/61, 3 err, 0 timeout) |
| 错误 / DB-fallback | 3 / 0 |
| Avg / P50 / P95 | 39948 / 25539 / 138762 ms |
| 429 / timeout | 0 / 0 |
| upstream_type | nvcf_pexec 61/58 (100%), integrate 0 |
| finish_reason | tool_calls 49, stop 9 |

**错误分类**：
```
all_tiers_exhausted|1|180065   (k0, ≈烧满 180s budget)
stream_absolute_cap|1|176364   (k0, 流达绝对上限)
NVStream_IncompleteRead|1|69642 (k3, NVCF 流截断)
```

**Per-key 200 延迟**（分散, 无单 key 错误聚集）:
```
key0|11req|avg26036|max45216|err:ATE×1+stream_cap×1
key1|12req|avg30615|max69788
key2|12req|avg34706|max79766
key3|13req|avg42872|max139851|err:IncompleteRead×1
key4|10req|avg38316|max100909
```

**key_cycle_429s**: k0=25, k1=33, k2=1, k3=1, k4=1 — 内部轮转吸收, 非请求级失败。

## 趋势

| 窗口 | SR | 备注 |
|---|---|---|
| 6h | **88.01%** (499/567) | 68 err, 受 NVCF 过载振荡拖累 |
| 3h 逐小时 | 14:00 64/68=94.1%, 13:00 62/72=86.1%, 12:00 81/91=89.0% | 近窗回升 |
| 24h | all_tiers_exhausted=57 | NVCF 持续过载, 非本窗异常 |

## 决策推理 (对照 R1191-1201 已确立的判断)

all_tiers_exhausted + stream_absolute_cap + IncompleteRead 组合 = NVCF 上游系统性瞬时 jitter,
与 R1191-R1201 判定完全一致。此时调 budget/cooldown/fast-break 均无杠杆:
- 缩短预算仅缩短 ATE 时长 (更快 fallback), 不降 ATE 数, 且牺牲长链成功率。
- 调 KEY_COOLDOWN 不解决 all-5-key 同质停滞。
- 当前无 fallback 触发, 链路已恢复, 重创容器为修复已自我解决的问题属本末倒置。

守"改前必有数据"铁律 — 越阈值但无容器可归因杠杆, 且危害已自愈。**NOP。**

## 验证
- 容器 env 与脚本采集一致: UPSTREAM_TIMEOUT=50, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=90,
  KEY_COOLDOWN_S=30, NVU_TIER_BUDGET_DSV4F0731_NV=180, NVU_KEYMGR_429_*=120,
  NVU_KEYMGR_CONN_*=30/60/120, NVU_EMPTY_200_FASTBREAK=3, NVU_PEXEC_TIMEOUT_FASTBREAK=3 ✓
- 容器 `dsvf0731_nv40666` Up 20 hours, 未重启 ✓

## 下一步建议
- 若下一窗 ATE 持续 ≥3 且 hm4104 fallback 复现, 再评估是否缩短 `NVU_TIER_BUDGET_DSV4F0731_NV`
  180→150 以加速 fallback (牺牲长链成功率换来更快降级)。当前链路健康, 不动。
- 持续观察 k3/k4 偏高 avg (42872/38316ms) 是否为偶发长尾, 若连续多窗单 key 劣化再考虑 SOCKS5 侧排查。