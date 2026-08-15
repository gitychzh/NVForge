# R1207: dsv4f0731_nv40666 NOP — 30min SR=92.0%, 4错全为 NVCF 外部过载(ATE×4), fallback 回升活跃但 ms_gw 目标健康保服务, 无容器可归因杠杆

日期: 2026-08-09 01:22 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DeepSeek V4 Pro via NVCF pexec)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

30min SR=46/50=**92.0%**（略低于 95% NOP 阈值），4 个错误全为 `all_tiers_exhausted`
（单 key k0），与 R1191-R1206 反复判定的同一 **NVCF 外部过载** 根因完全延续。本轮与
R1206 的关键差异是 **hm4104 fallback 回升活跃**（近 1h 7 次 PRIMARY-FAIL），但 fallback
目标 `ms_gw/dsv4f0731_ms` **健康**（`models_all_exhausted=[]`，无 key/variant 冷却，
计数器 1862 正常增长），hermes 主链路服务实际被 fallback 保住，无服务降级风险。

**证据链**：
1. **all_tiers_exhausted ×4 (各 ~172s, 全落 k0)** — 与历轮相同的 NVCF 全键同质停滞模式，
   每次烧满整段 180s budget 后 fail，属上游服务端过载 jitter，非任何单 key/单参数可调。
   **24h ATE=73**（R1204=63 → R1205=67 → R1206=69 → 本轮 73，+4/窗，加速爬升），
   确证 NVCF 过载持续加深，非本窗异常聚集。
2. **净 429 = 0** — key_cycle_429s (k0=14, k1=35, k2=1) 为内部轮转吸收计数，未产生请求级 429。
3. **无单 key 错误聚集** — 4 ATE 全落 k0，但 k0 avg_ok=32.9s 非最差（k1=47.5s 最慢），
   证明 k0 proxy/出口健康，ATE 归属 k0 仅因它是轮转起始/末次尝试位，非 key 劣化。
   per-key 200 延迟均衡 (k0 32.9s, k1 47.5s, k2 11.3s, k3 30.5s, k4 20.3s)，无单 key 异常。
4. **fallback 回升活跃但目标健康** — 近 1h 7 次 PRIMARY-FAIL-STREAM (502 after ~175-180s，
   均烧满 budget) + 1 次 FALLBACK-FAIL-STREAM (ms_gw timeout 245s)。但 ms_gw /health 显示
   `models_all_exhausted=[]`、无冷却，fallback 目标 `dsv4f0731_ms` 计数器正常增长 →
   hermes 服务经 fallback 保住，非紧急降级。此模式与 R1205 (14次) → R1206 (0次) →
   本轮 (7次) 的 fallback 振荡，均为 NVCF primary 过载窗口的同步镜像。
5. **tier_attempts 空** — 无 key 间切换异常模式。
6. **integrate = 0** — 本轮全程 pexec，无 integrate/pexec 失衡问题。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **92.0%** (46/50, 4 err, 0 timeout) |
| 错误 / DB-fallback | 4 / 0 |
| Avg / P50 / P95 | 40801 / 19028 / 165262 ms (p95 贴近 180s budget) |
| 429 / timeout | 0 / 0 |
| upstream_type | nvcf_pexec 50/46 (100%), integrate 0 |
| finish_reason | tool_calls 30, stop 16 |

**错误分类**：
```
all_tiers_exhausted|4|172099    (k0×4, 各烧满 ~172s budget)
```

**Per-key 200 延迟**（均衡, 无单 key 错误聚集; k0 承载 4 ATE 但 avg_ok 非最差）:
```
key0|6req|avg32991|max88871
key1|11req|avg47564|max111561
key2|8req|avg11354|max15490
key3|11req|avg30530|max72665
key4|10req|avg20385|max52326
```

**key_cycle_429s**: k0=14, k1=35, k2=1 — 内部轮转吸收, 非请求级失败。

## 趋势

| 窗口 | SR | 备注 |
|---|---|---|
| 6h | **89.8%** (478/532) | 54 err, 受 NVCF 过载振荡拖累 |
| 3h 逐小时 | 17:00 34/38=89.5%, 16:00 81/89=91.0%, 15:00 96/100=96%, 14:00 41/48=85.4% | 近窗在 85-96% 间振荡 (NVCF 过载窗口同步) |
| 24h | all_tiers_exhausted=73 | NVCF 持续过载加深 (63→67→69→73), 非本窗异常 |

## 决策推理 (对照 R1191-1206 已确立的判断)

- 缩短预算仅缩短 ATE 时长（更快 fallback），不降 ATE 数，且牺牲 ~1% 长链成功率 (p95 顶满
  180s 有正常长链 200 落在 120-180s 区间，缩短会误杀)。NVU_TIER_BUDGET_DSV4F0731_NV=180
  保持不变。
- all_tiers_exhausted 非列出的可调参数域；fallback 目标 `ms_gw/dsv4f0731_ms` 健康，
  服务经 fallback 保住，无紧迫修复需求。
- 改 env 需 `docker compose up -d --force-recreate`（`docker update` 不支持 env、`docker
  restart` 不换 env），属高风险容器重建操作，在 NVCF 过载期做违背"稳定性优先"铁律。
- 净 429=0、无单 key 劣化、无新错误类型，无源自本容器的可调杠杆。

守"改前必有数据"铁律——略低于阈值但 4 错全为外部 ATE，fallback 目标健康保服务，无容器
可归因杠杆。**NOP。**

## 验证
- 容器 env 与脚本一致: UPSTREAM_TIMEOUT=50, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=90,
  KEY_COOLDOWN_S=30, NVU_TIER_BUDGET_DSV4F0731_NV=180, NVU_TIER_BUDGET_DSV4F_NV=180,
  NVU_KEYMGR_429_*=120, NVU_EMPTY_200_FASTBREAK=3, NVU_PEXEC_TIMEOUT_FASTBREAK=3 ✓
- 容器 `dsvf0731_nv40666` Up 23 hours, 未重启 ✓
- /health: status ok, nv_num_keys=5, 5 模型全部在列 ✓
- ms_gw /health: `models_all_exhausted=[]`, 无冷却, fallback 目标健康 ✓

## 下一步建议
- 监控 24h ATE 爬升速率 (本轮 73)。若 ATE 持续加速且 fallback 目标 `ms_gw/dsv4f0731_ms`
  也开始衰竭 (`models_all_exhausted` 非空)，才是需要介入的紧急信号——届时评估是否将
  `NVU_TIER_BUDGET_DSV4F0731_NV` 180→150 以加速 primary recovery 回环，减少对 ms_gw 的
  fallback 依赖。
- 持续观察 NVCF 过载窗口 (3h 逐小时 SR 振荡) 是否随日均波动缓解。
- 若 fallback 频率持续攀升且 ms_gw 目标稳定，可考虑在过载期是否为 hermes 优化 fallback
  冷却策略（但���属 hm4104/ms_gw 侧，非本容器 dsvf0731_nv40666 可调域）。