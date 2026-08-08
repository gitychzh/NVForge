# R1203: dsv4f0731_nv40666 NOP — 30min SR=95.7% 越阈值, 2错均为NVCF外部瞬态(all_tiers_exhausted), 无容器可归因杠杆, 链路健康

日期: 2026-08-08 23:34 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DeepSeek V4 Pro via NVCF pexec)

## 决策：NOP（不改任何参数）

30min SR=44/46=**95.65%** (达 NOP 阈值 ≥95%), 2 错误均为 **NVCF 外部瞬态**, 无本容器可归因杠杆。
与 R1191-R1202 反复判定的同一外部根因模式完全一致。

**证据链**：
1. **all_tiers_exhausted ×2 (k0, ~180s)** — 此错误 = all-5-key 同质停滞烧满 180s budget 后
   exhaust。逐 request 均为键位无关的全 key 同时失败, 属 **NVCF 服务端全停**, 非任何单 key/单参数可调。
2. **净 429 = 0** — key_cycle_429s (k0=10, k1=31, k2=5) 为内部轮转吸收计数, 未产生请求级 429。
3. **hm4104 近 5min 无 fallback 日志** — 当前链路健康, 未降级到 ms_gw。
4. **无 key 级错误聚集** — 错误仅落在 k0 (ATE 全键同质), 非某单 key 独立劣化, 无 SOCKS5 代理侧问题可调。
5. **tier_attempts 空** — 无 key 间切换异常模式。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **95.65%** (44/46, 2 err, 0 timeout) |
| 错误 / DB-fallback | 2 / 0 |
| Avg / P50 / P95 | 48605 / 32184 / 130955 ms |
| 429 / timeout | 0 / 0 |
| upstream_type | nvcf_pexec 46/44 (100%), integrate 0 |
| finish_reason | tool_calls 35, stop 9 |

**错误分类**：
```
all_tiers_exhausted|2|180053   (k0×2, ≈烧满 180s budget)
```

**Per-key 200 延迟**（分散, 无单 key 非 ATE 错误聚集）:
```
key0|9req|avg51003|max102191|err:ATE×2
key1|9req|avg33088|max71117
key2|7req|avg43365|max102258
key3|11req|avg46315|max112189
key4|8req|avg38238|max88616
```

**key_cycle_429s**: k0=10, k1=31, k2=5 — 内部轮转吸收, 非请求级失败。

## 趋势

| 窗口 | SR | 备注 |
|---|---|---|
| 6h | **88.43%** (497/562) | 65 err, 受 NVCF 过载振荡拖累 |
| 3h 逐小时 | 15:00 47/49=95.9%, 14:00 81/91=89.0%, 13:00 62/72=86.1%, 12:00 31/36=86.1% | 近窗明显回升 |
| 24h | all_tiers_exhausted=63 | NVCF 持续过载, 非本窗异常 |

## 决策推理 (对照 R1191-1202 已确立的判断)

all_tiers_exhausted 组合 = NVCF 上游系统性瞬时 jitter, 与 R1191-R1202 判定完全一致。
此时调 budget/cooldown/fast-break 均无杠杆:
- 缩短预算仅缩短 ATE 时长 (更快 fallback), 不降 ATE 数, 且牺牲长链成功率。
- 调 KEY_COOLDOWN 不解决 all-5-key 同质停滞。
- 当前无 fallback 触发, 链路已恢复, 重创容器为修复已自我解决的问题属本末倒置。

守"改前必有数据"铁律 — 越阈值且无容器可归因杠杆, 危害已自愈。**NOP。**

## 验证
- 容器 env 与脚本采集一致: UPSTREAM_TIMEOUT=50, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=90,
  KEY_COOLDOWN_S=30, NVU_TIER_BUDGET_DSV4F0731_NV=180, NVU_KEYMGR_429_*=120,
  NVU_KEYMGR_CONN_*=30/60/120, NVU_EMPTY_200_FASTBREAK=3, NVU_PEXEC_TIMEOUT_FASTBREAK=3 ✓
- 容器 `dsvf0731_nv40666` Up 21 hours, 未重启 ✓

## 下一步建议
- 若下一窗 ATE 持续回升且 hm4104 fallback 复现, 再评估是否缩短 `NVU_TIER_BUDGET_DSV4F0731_NV`
  180→150 以加速 fallback (牺牲长链成功率换来更快降级)。当前链路健康, 不动。
- 近窗 (15:00) SR 已回升至 95.9%, 与 6h 的 88.4% 形成对比, 表明 NVCF 过载正在缓解, 保持观察即可。