# R1201: dsv4f0731_nv40666 NOP — 30min SR=92.5% ATE×2+IncompleteRead×1+stream_cap×1, 均为NVCF外部瞬态, 无容器杠杆

日期: 2026-08-08 22:24 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DeepSeek V4 Pro via NVCF pexec)

## 决策：NOP（不改任何参数）

30min SR=49/53=**92.5%** (<95% NOP 阈值), 4 错误均为 **NVCF 外部瞬态**, 无本容器可归因杠杆。
与 R1041/R1042/R1043/R1191-R1200 反复判定的同一外部根因模式一致。

**证据链**：
1. **all_tiers_exhausted ×2 (k0, ~166s avg)** — 此错误 = all-5-key 同质停滞烧满 180s budget 后
   exhaust。逐 request 均为键位无关的全 key 同时失败, 属 **NVCF 服务端全停**, 非任何单 key/单参数可调。
   预算 180 或 150 都改变不了 ATE 计数 (all keys 都失败)。
2. **NVStream_IncompleteRead ×1 (k3)** — 流被上游 NVCF 截断, 单次瞬态, 非配置性。
3. **stream_absolute_cap ×1 (k0)** — 流达绝对上限, 瞬态。
4. **429 request count = 0** — key_cycle_429s (k0=20, k1=31) 为内部轮转吸收计数, 未产生请求级 429。
5. **hm4104 近 5min 无 fallback 日志** — 当前链路健康, 未降级到 ms_gw。
6. **无 key 级错误聚集** — 错误散布 k0/k3, 非某单 key 劣化, 无 SOCKS5 代理侧问题可调。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **92.45%** (49/53, 4 err, 0 timeout) |
| 错误 / DB-fallback | 4 / 0 |
| Avg / P50 / p95 | 40991 / 24942 / 178141 ms |
| 429 / timeout | 0 / 0 |
| upstream_type | nvcf_pexec 53/53 (100%), integrate 0 |
| finish_reason | tool_calls 41, stop 8 |

**错误分类**：
```
all_tiers_exhausted|2|166621    (k0×2, ~166s ≈ 烧满 180s budget)
NVStream_IncompleteRead|1|69642  (k3, NVCF 流截断)
stream_absolute_cap|1|176364     (k0, 流达绝对上限)
```

**Per-key 200 延迟**（分散, 无单 key 错误聚集）:
```
key0|11req|avg30401|max68869|err:ATE×2+stream_cap×1
key1|12req|avg39422|max107555
key2|10req|avg32621|max72327
key3|11req|avg25212|max46104|err:IncompleteRead×1
key4|5req|avg36449|max74121
```

**key_cycle_429s**: k0=20, k1=31, k2=1, k4=1 — 内部轮转吸收, 非请求级失败。

## 决策推理 (对照 R1041-1043 已确立的判断)

all_tiers_exhausted + IncompleteRead + stream_absolute_cap 组合 = NVCF 上游系统性瞬时 jitter,
与 R1041-R1043 判定完全一致。此时调 budget/cooldown/fast-break 均无杠杆:
- 缩短预算仅缩短 ATE 时长 (更快 fallback), 不降 ATE 数, 且牺牲长链成功率。
- 调 KEY_COOLDOWN 不解决 all-5-key 同质停滞。
- 当前无 fallback 触发, 链路已基本恢复, 重创容器为修复已自我解决的问题属本末倒置。

守"改前必有数据"铁律 — 越阈值但无容器可归因杠杆, 且危害已自愈。**NOP。**

## 验证
- /health: `status: ok`, proxy_role passthrough, num_keys=5, port 40666 ✓
- 容器 `dsvf0731_nv40666` Up 20 hours, 未重启 ✓

## 下一步建议
- 若下一窗 ATE 持续 ≥3 且 hm4104 fallback 复现, 再评估是否缩短 `NVU_TIER_BUDGET_DSV4F0731_NV`
  180→150 以加速 fallback (牺牲长链成功率换来更快降级)。当前链路健康, 不动。
- 持续观察 key1 高 avg 延迟 (107555ms) 是否为偶发长尾, 若连续多窗单 key 劣化再考虑 SOCKS5 侧排查。