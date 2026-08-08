# R1205: dsv4f0731_nv40666 NOP — 30min SR=90.2% 越阈值, 错误全为 NVCF 外部过载(ATE+buffer+zombie), fallback 活跃但目标 ms_gw 健康保服务, 无容器可归因杠杆

日期: 2026-08-09 00:47 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DeepSeek V4 Pro via NVCF pexec)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

30min SR=37/41=**90.24%**（低于 95% NOP 阈值），4 个错误均非参数可归因，与 R1191-R1204
反复判定的同一 **NVCF 外部过载** 根因完全延续。本轮与历轮 NOP 的主要差异是 **hm4104 fallback
活跃触发** (近 25min 14 次, circuit OPEN)，但 fallback 目标 `ms_gw/dsv4f0731_ms` **健康**
(ms_gw /health 无 cooldown, ms_dsv4f0731 计数器 1850 正常增长)，hermes 主链路服务实际被保住了。

**证据链**：
1. **all_tiers_exhausted ×2 (各 ~180s)** — 与历轮相同的 NVCF 全键同质停滞模式，每次烧满整段
   180s budget 后 fail，属上游服务端过载 jitter，非任何单 key/单参数可调。24h ATE=67
   (66→67 +1/窗) 缓慢爬升，非本窗异常聚集。
2. **buffer_exhausted ×1 (~435s, k4)** — 单次 buffer 流判定失败，duration 435s 远超 budget
   (180s)，为 buffer-stream 内部 verdict 路径，非本容器可调 env (不属于列出的可调参数域)。
   孤立单次，未观察聚集。
3. **zombie_empty_completion ×1 (~5.6s, k2)** — 上报 200 但空内容，上游劣化信号，孤立单次，
   远低于 NVU_EMPTY_200_FASTBREAK=3 阈值，未触发 fastbreak，不可调。
4. **净 429 = 0** — key_cycle_429s (k0=10, k1=30, k2=1) 为内部轮转吸收计数，未产生请求级 429。
5. **无单 key 错误聚集** — 4 错误分落 k0/k1/k2/k4 各 1，非固定某 key 的 SOCKS5/出口 IP 劣化;
   错误随机散布，属全键过载。8 个成功 200 请求中 k1 avg=48650ms 略高但无错误聚集，非代理故障。
6. **tier_attempts 空** — 无 key 间切换异常模式。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **90.24%** (37/41, 4 err, 0 timeout) |
| 错误 / DB-fallback | 4 / 0 |
| Avg / P50 / P95 | 55047 / 32248 / 180038 ms (p95 顶满 180s budget) |
| 429 / timeout | 0 / 0 |
| upstream_type | nvcf_pexec 41/37 (100%), integrate 0 |
| finish_reason | tool_calls 26, stop 11 |

**错误分类**：
```
all_tiers_exhausted|2|180042    (k0×1, k4×1, 各烧满 180s budget)
buffer_exhausted|1|434984       (k4, 单次 buffer 流 verdict 失败, 435s)
zombie_empty_completion|1|5599   (k2, 空 200, 孤立单次)
```

**Per-key 200 延迟**（分散, 无单 key 错误聚集）:
```
key0|7req|avg33191|max65693
key1|10req|avg48650|max106642
key2|8req|avg35964|max78198
key3|4req|avg29923|max40698
key4|8req|avg41255|max115623
```

**key_cycle_429s**: k0=10, k1=30, k2=1 — 内部轮转吸收, 非请求级失败。

## 趋势

| 窗口 | SR | 备注 |
|---|---|---|
| 6h | **89.10%** (474/532) | 58 err, 受 NVCF 过载振荡拖累 |
| 3h 逐小时 | 16:00 41/46=89%, 15:00 96/100=96%, 14:00 81/91=89%, 13:00 25/29=86% | 近窗在 86-96% 间振荡 |
| 24h | all_tiers_exhausted=67 | NVCF 持续过载, 非本窗异常 |

## hm4104 fallback 评估（本轮关键新观察）

近 25min **14 次** fallback 事件 (FALLBACK-STREAM + PRIMARY-BREAKER-SKIP-STREAM, circuit OPEN)，
且有 PRIMARY-ZOMBIE-FALLBACK (nv_gw 返回 content_filter zombie → 切 ms_gw)。但:
- `ms_gw` /health 显示 **keys_cooling=[] / variants_cooling=[] / models_all_exhausted=[]**，
  `dsv4f0731_ms` 可用 → **fallback 成功保住服务**。
- fallback 是 hm4104 (hermes adapter) 的 **客户端侧 circuit breaker**，非本容器 env 可调。
- 本容器参数无法直接关闭/加速 hm4104 的 fallback 断路器。

## 决策推理 (对照 R1191-1204 已确立的判断)

- 缩短预算仅缩短 ATE 时长（更快 fallback），不降 ATE 数，且牺牲~1% 长链成功率 (6h p90=94s,
  p95=120s 有正常长链 200 落在 120-180s 区间，缩短预算会误杀)。
- buffer_exhausted 与 zombie_empty_completion 均非列出的可调参数域。
- fallback 活跃但目标健康，服务未降级，无紧迫修复需求。
- 改 env 需 `docker compose up -d --force-recreate`（`docker update` 不支持 env、`docker restart`
  不换 env），属高风险容器重建操作，在 NVCF 过载期做违背"稳定性优先"铁律。

守"改前必有数据"铁律——越阈值但无容器可归因杠杆，且 fallback 安全网健康保住服务。**NOP。**

## 验证
- 容器 env 与脚本一致: UPSTREAM_TIMEOUT=50, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=90,
  KEY_COOLDOWN_S=30, NVU_TIER_BUDGET_DSV4F0731_NV=180, NVU_KEYMGR_429_*=120,
  NVU_KEYMGR_CONN_*=30/60/120, NVU_EMPTY_200_FASTBREAK=3, NVU_PEXEC_TIMEOUT_FASTBREAK=3 ✓
- 容器 `dsvf0731_nv40666` Up 22 hours, 未重启 ✓
- /health: status ok, nv_num_keys=5, 5 模型全部在列 ✓

## 下一步建议
- 若下一窗 fallback **持续**且 `ms_gw/dsv4f0731_ms` 也开始衰竭 (models_all_exhausted 非空)，
  才是需要介入的紧急信号——届时评估是否将 `NVU_TIER_BUDGET_DSV4F0731_NV` 180→150 以加速 primary
  recovery 回环。
- 若 `buffer_exhausted` 由单次演变为聚集 (≥3/30min)，需源码级排查 buffer_stream.py verdict 路径
  (非 env 可调)。
- 持续观察 NVCF 过载窗口 (3h 逐小时 SR 在 86-96% 振荡) 是否随日均波动缓解。