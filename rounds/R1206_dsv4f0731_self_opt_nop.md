# R1206: dsv4f0731_nv40666 NOP — 30min SR=93.18%, 3 错全为 NVCF 外部过载(ATE×2+cap×1 孤立), fallback=0 健康, 无容器可归因杠杆

日期: 2026-08-09 01:00 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DeepSeek V4 Pro via NVCF pexec)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

30min SR=41/44=**93.18%**（较 R1205 的 90.24% 回升，仍略低于 95% NOP 阈值），3 个错误
均非参数可归因，与 R1191-R1205 反复判定的同一 **NVCF 外部过载** 根因完全延续。本轮与
R1205 的关键差异是 **hm4104 fallback = 0**（R1205 近窗 14 次 → 本轮 0 次），hermes 主链路
服务健康，无任何降级信号。

**证据链**：
1. **all_tiers_exhausted ×2 (各 ~178s, k0)** — 与历轮相同的 NVCF 全键同质停滞模式，每次
   烧满整段 180s budget 后 fail，属上游服务端过载 jitter，非任何单 key/单参数可调。24h
   ATE=69 (67→69 +2/窗) 缓慢爬升，非本窗异常聚集。
2. **stream_absolute_cap ×1 (~150s, k1)** — 单次 NVCF 流式绝对上限判定失败，孤立单次，
   未观察聚集，非本容器可调 env。
3. **净 429 = 0** — key_cycle_429s (k0=11, k1=31, k2=1, k3=1) 为内部轮转吸收计数，未产生
   请求级 429。
4. **无单 key 错误聚集** — 3 错误分落 k0×2/k1×1，非固定某 key 的 SOCKS5/出口 IP 劣化;
   错误随机散布，属全键过载。per-key 200 延迟均衡 (k0 43.7s, k1 46.9s, k2 29.6s, k3 29.2s,
   k4 42.9s)，无单 key 异常。
5. **tier_attempts 空** — 无 key 间切换异常模式。
6. **fallback = 0** — hm4104 无 fallback 日志，PRIMARY 主链路成功交付，无服务降级。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **93.18%** (41/44, 3 err, 0 timeout) |
| 错误 / DB-fallback | 3 / 0 |
| Avg / P50 / P95 | 48101 / 24818 / 178059 ms (p95 顶满 180s budget) |
| 429 / timeout | 0 / 0 |
| upstream_type | nvcf_pexec 44/41 (100%), integrate 0 |
| finish_reason | tool_calls 29, stop 12 |

**错误分类**：
```
all_tiers_exhausted|2|177735    (k0×2, 各烧满 180s budget)
stream_absolute_cap|1|150143    (k1, 孤立单次)
```

**Per-key 200 延迟**（均衡, 无单 key 错误聚集）:
```
key0|9req|avg43752|max111723
key1|8req|avg46966|max96418
key2|9req|avg29587|max70805
key3|5req|avg29227|max62842
key4|10req|avg42890|max125066
```

**key_cycle_429s**: k0=11, k1=31, k2=1, k3=1 — 内部轮转吸收, 非请求级失败。

## 趋势

| 窗口 | SR | 备注 |
|---|---|---|
| 6h | **90.28%** (483/535) | 52 err, 受 NVCF 过载振荡拖累 |
| 3h 逐小时 | 16:00 89/100=89%, 15:00 96%, 14:00 91% | 近窗在 86-96% 间振荡 (established window) |
| 24h | all_tiers_exhausted=69 | NVCF 持续过载, 非本窗异常 |

## 决策推理 (对照 R1191-1205 已确立的判断)

- 缩短预算仅缩短 ATE 时长（更快 fallback），不降 ATE 数，且牺牲 ~1% 长链成功率 (p95 顶满
  180s 有正常长链 200 落在 120-180s 区间，缩短会误杀)。
- stream_absolute_cap 与 all_tiers_exhausted 均非列出的可调参数域。
- fallback = 0，服务健康无降级，无紧迫修复需求。
- 改 env 需 `docker compose up -d --force-recreate`（`docker update` 不支持 env、`docker
  restart` 不换 env），属高风险容器重建操作，在 NVCF 过载期做违背"稳定性优先"铁律。

守"改前必有数据"铁律——略低于阈值但无容器可归因杠杆，且 fallback 已归零、服务完全健康。
**NOP。**

## 验证
- 容器 env 与脚本一致: UPSTREAM_TIMEOUT=50, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=90,
  KEY_COOLDOWN_S=30, NVU_TIER_BUDGET_DSV4F0731_NV=180, NVU_KEYMGR_429_*=120,
  NVU_EMPTY_200_FASTBREAK=3, NVU_PEXEC_TIMEOUT_FASTBREAK=3 ✓
- 容器 `dsvf0731_nv40666` Up 23 hours, 未重启 ✓
- /health: status ok, nv_num_keys=5, 5 模型全部在列 ✓

## 下一步建议
- 若下一窗 fallback **持续**且 `ms_gw/dsv4f0731_ms` 也开始衰竭 (models_all_exhausted 非空),
  才是需要介入的紧急信号——届时评估是否将 `NVU_TIER_BUDGET_DSV4F0731_NV` 180→150 以加速
  primary recovery 回环。
- 若 `stream_absolute_cap` 由单次演变为聚集 (≥3/30min)，需源码级排查 NVCF 流式上限 (非 env
  可调)。
- 持续观察 NVCF 过载窗口 (3h 逐小时 SR 在 86-96% 振荡) 是否随日均波动缓解。