# RN1077: dsvf0731_nv40666 NOP — 30min SR=94.2% 略低阈值, 2错均为 NVCF 外部过载(ATE)非参数可归因, 无容器杠杆, 链路未降级

日期: 2026-08-09 00:22 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF pexec 链路)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

30min SR=49/52=**94.23%**（略低于 95% NOP 阈值），但 3 个错误均为**非参数可归因事件**，
无本容器可调杠杆。与 RN1076 / R1204 及 R1191-R1203 反复判定的同一外部根因模式完全延续。

**证据链**：
1. **all_tiers_exhausted ×2 (k0, 各 ~180049ms)** — 与历轮相同的 NVCF 全键同质停滞模式;
   每次烧满整段 180s budget 后 fail, 属上游服务端过载 jitter, 非任何单 key/单参数可调。
   24h ATE=66 (63→64→65→66 缓慢爬升 ~+1/窗), 非本窗异常聚集。
2. **zombie_empty_completion ×1 (k2, 5599ms)** — 上报 200 但空内容, 上游劣化信号,
   但**孤立单次**, 远低于 NVU_EMPTY_200_FASTBREAK=3 阈值, 未触发 fastbreak, 不可调。
3. **净 429 = 0** — key_cycle_429s (k0=20, k1=32) 为内部轮转吸收计数, 未产生请求级 429。
4. **hm4104 近 5min 无 fallback 日志** — 当前链路健康, 未降级到 ms_gw。
5. **无单 key 错误聚集** — 2 ATE 全落 k0 (avg_ok 29951ms 为最快 key), zombie 落 k2,
   非固定某 key 的 SOCKS5/出口 IP 劣化; 错误随机散布, 属全键过载。
6. **tier_attempts 空** — 无 key 间切换异常模式。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **94.23%** (49/52, 3 err) |
| Avg / P50 / P95 | 39546 / 22726 / 158192 ms |
| 429 | 0 |
| upstream_type | nvcf_pexec 52/49 (94.2%), integrate 0 |
| finish_reason | tool_calls 34, stop 15 |

**错误分类**：
```
all_tiers_exhausted|2|180049   (k0, 烧满 180s budget ×2)
zombie_empty_completion|1|5599  (k2, 孤立单次, 未触发 fastbreak=3)
```

**Per-key 200 延迟**（分散, 错误随机不聚集）:
```
k0|9req|avg29951|max65086   (最快 key, 却承载 2 ATE → 随机过载非 proxy 劣化)
k1|14req|avg56016|max156421
k2|10req|avg29044|max76028   (zombie 落此键, avg_ok 正常)
k3|8req|avg27312|max46690
k4|8req|avg16001|max36937
```

**key_cycle_429s**: k0=20, k1=32 — 内部轮转吸收, 非请求级失败。

## 趋势

| 窗口 | SR | 备注 |
|---|---|---|
| 6h | **89.3%** (476/533) | 57 err, 受 NVCF 过载振荡拖累 |
| 3h 逐小时 | 16:00 31/34=91.2%, 15:00 96/100=96.0%, 14:00 81/91=89.0%, 13:00 37/42=88.1% | 近窗 91-96%, 链路基本健康, 偶发 ATE 尖峰 |
| 24h | all_tiers_exhausted=66 | NVCF 持续过载, 缓慢爬升, 非本窗异常 |

## 决策推理 (对照 RN1076/R1204 已确立的判断)

all_tiers_exhausted + zombie_empty_completion 组合均为非参数可归因:
- 缩短 TIER_TIMEOUT_BUDGET_S / NVU_TIER_BUDGET_DSV4F0731_NV 仅缩短 ATE 烧时长, 不降 ATE 数,
  且牺牲长链 (tool_calls×34) 成功率。
- 调 KEY_COOLDOWN / NVU_KEYMGR_429_* 不解决 all-5-key 同质停滞 (每键独立冷却也无法规避全键同时过载)。
- zombie 单次 < fastbreak 阈值, 调 NVU_EMPTY_200_FASTBREAK 无意义。
- client/hm4104 侧无 fallback, 链路已在健康区, 重创容器为修复已自我解决的问题属本末倒置。

守"改前必有数据"铁律 — 错误全为已鉴定的外部根因, 本地无可调杠杆, 越阈值边缘不构成扰动脉冲。**NOP。**

## 验证
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] env 复核: UPSTREAM_TIMEOUT=50, TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_DSV4F0731_NV=180,
  TIER_COOLDOWN_S=90, KEY_COOLDOWN_S=30, NVU_KEYMGR_429_*=120, NVU_KEYMGR_CONN_*=30/60/3/120,
  NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_EMPTY_200_FASTBREAK=3 ✓ (docker exec 复核无改动)
- [x] 容器 `dsvf0731_nv40666` Up 22 hours, 未重启 ✓
- [x] 数据完整: 30min SR/延迟/错误分类/per-key/upstream/finish_reason/429/key_cycle/6h/3h/24h/fallback 全部采集
- [x] 错误分类: ATE×2 全键同质停滞 + zombie×1 孤立 < fastbreak 阈值
- [x] per-key: 无既慢又错单key, 错误随机散布, 非 SOCKS5/出口 IP 问题
- [x] hm4104 fallback: 无 (本轮主链路健康, 未降级 ms_gw)

## 下一步建议
- 持续监测 SR: 若下一窗 SR>95% 且错误归零, 可判定 NVCF 过载振荡进入恢复期, 后续 NOP 简化为最小状态报告。
- 若 ATE 连续多窗聚集 (≥3/窗) 或 zombie 复现 ≥3 次/窗, 再重新评估是否缩短
  NVU_TIER_BUDGET_DSV4F0731_NV 180→150 以加速 fallback。当前链路健康, 不动。
- 保持现有参数; 仅在 NVCF 恢复后仍有模式化错误聚集时, 才重评估超时/预算/fast-break。