# R1204: dsv4f0731_nv40666 NOP — 30min SR=95.9% 越阈值, 2错均为非参数可归因(NVCF外部瞬态+客户端断开), 无容器杠杆, 链路健康

日期: 2026-08-09 00:00 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DeepSeek V4 Pro via NVCF pexec)

## 决策：NOP（不改任何参数）

30min SR=47/49=**95.92%** (达 NOP 阈值 ≥95%), 2 错误均为 **非参数可归因事件**, 无本容器可调杠杆。
与 R1191-R1203 反复判定的同一外部根因模式延续。

**证据链**：
1. **all_tiers_exhausted ×1 (k0, ~180s)** — 与 R1191-R1203 相同的外部全键同质停滞模式; 24h ATE
   仅 63→64 (+1 增量), 非本窗异常。逐 request 键位无关的全 key 同时失败, 属 NVCF 服务端 jitter,
   非任何单 key/单参数可调。
2. **client_gone_during_flush ×1 (k1, ~220s)** — 客户端在 flush 阶段断开, 属 **客户端侧事件**,
   非容器/上游缺陷, 无参数可归因。
3. **净 429 = 0** — key_cycle_429s (k0=18, k1=28, k2=3) 为内部轮转吸收计数, 未产生请求级 429。
4. **hm4104 近 5min 无 fallback 日志** — 当前链路健康, 未降级到 ms_gw。
5. **无 key 级错误聚集** — 2 错误分落 k0/k1 两键, 非某单 key 独立劣化, 无 SOCKS5 代理侧问题。
6. **tier_attempts 空** — 无 key 间切换异常模式。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **95.92%** (47/49, 2 err, 0 timeout) |
| 错误 / DB-fallback | 2 / 0 |
| Avg / P50 / P95 | 46235 / 25378 / 134842 ms |
| 429 / timeout | 0 / 0 |
| upstream_type | nvcf_pexec 49/47 (100%), integrate 0 |
| finish_reason | tool_calls 38, stop 9 |

**错误分类**：
```
all_tiers_exhausted|1|180038   (k0, ≈烧满 180s budget)
client_gone_during_flush|1|220849 (k1, 客户端断开)
```

**Per-key 200 延迟**（分散, 无单 key 错误聚集）:
```
key0|9req|avg37805|max92864
key1|8req|avg35564|max91770
key2|8req|avg22717|max71298
key3|10req|avg59492|max130854
key4|12req|avg38603|max88457
```

**key_cycle_429s**: k0=18, k1=28, k2=3 — 内部轮转吸收, 非请求级失败。

## 趋势

| 窗口 | SR | 备注 |
|---|---|---|
| 6h | **89.29%** (500/560) | 60 err, 受 NVCF 过载振荡拖累 |
| 3h 逐小时 | 15:00 89/93=95.7%, 14:00 81/91=89.0%, 13:00 62/72=86.1%, 12:00 3/3 | 近窗保持 95%+ 健康 |
| 24h | all_tiers_exhausted=64 | NVCF 持续过载, 非本窗异常 |

## 决策推理 (对照 R1191-1204 已确立的判断)

all_tiers_exhausted + client_gone_during_flush 组合均为非参数可归因:
- 缩短预算仅缩短 ATE 时长, 不降 ATE 数, 且牺牲长链成功率。
- 调 KEY_COOLDOWN 不解决 all-5-key 同质停滞。
- client_gone 与任何上游参数无关。
- 当前无 fallback 触发, 链路已恢复, 重创容器为修复已自我解决的问题属本末倒置。

守"改前必有数据"铁律 — 越阈值且无容器可归因杠杆, 危害已自愈。**NOP。**

## 验证
- 容器 env 与脚本采集一致: UPSTREAM_TIMEOUT=50, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=90,
  KEY_COOLDOWN_S=30, NVU_TIER_BUDGET_DSV4F0731_NV=180, NVU_KEYMGR_429_*=120,
  NVU_KEYMGR_CONN_*=30/60/120, NVU_EMPTY_200_FASTBREAK=3, NVU_PEXEC_TIMEOUT_FASTBREAK=3 ✓
- 容器 `dsvf0731_nv40666` Up 22 hours, 未重启 ✓

## 下一步建议
- 若下一窗 ATE/fallback 复现且持续, 再评估是否���短 `NVU_TIER_BUDGET_DSV4F0731_NV` 180→150 以加速
  fallback。当前链路健康, 不动。
- 近窗 (15:00) SR 保持 95.7%, 与 6h 的 89.3% 对比表明 NVCF 过载正在缓解, 保持观察。