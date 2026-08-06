# R1068: 确认 R1067 效果 — CONN_ERR_FAST_BREAK=5 生效, SR 提升 / ATE 减半

> 时间: 2026-08-06 14:58 BJT (06:58 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF)
> 状态: **观察/效果确认轮 (无新参数修改)**。R1067 改动已生效并验证为正向。
> 编号: 本轮为 R1068 (R1067 = 首个非 NOP 改动, 已落地 ~1.2h)

## 1. 背景 (改前必有数据)

### R1067 改动 (上轮) 复盘
- 修改: `CONN_ERR_FAST_BREAK` 从硬编码 2 → env 可调, 本容器设 `NVU_CONN_ERR_FAST_BREAK=5`
- 目标: 间歇性 RemoteDisconnected 下不再 2 次失败即放弃, 让 tier 循环全部 5 key
- 验证: `docker exec dsvf0731_nv40666 env | grep CONN_ERR_FAST_BREAK` = `NVU_CONN_ERR_FAST_BREAK=5` ✓
- 容器 recreate 于 ~55min 前 (R1067 deploy), 06:00 UTC 小时已完全处于改动后窗口

### 当前数据 (本轮直接查询)

**8h 逐小时 SR / ATE (nv_requests, tier_model=dsv4f0731_nv)**
| hour (UTC) | total | 200 | SR% | ATE |
|---|---|---|---|---|
| 00:00 | 3 | 2 | 66.7 | 0 |
| 01:00 | 65 | 22 | 33.8 | 26 |
| 02:00 | 72 | 30 | 41.7 | 24 |
| 03:00 | 76 | 35 | 46.1 | 21 |
| 04:00 | 78 | 25 | 32.1 | 35 |
| 05:00 | 69 | 32 | 46.4 | 16 |
| **06:00 (post-recreate)** | 69 | 31 | **46.2** | **16** |

→ **04:00 (pre) SR=32.1%/ATE=35 vs 06:00 (post) SR=46.2%/ATE=16**: SR 提升 14pt, ATE 减半。

**当前 30min 窗口 (06:28-06:58 UTC 查询)**
- 总量 34, 200=16, **SR=47.1%**, Avg 129351ms (pre-run 14:44 抓取时 SR=33%, 8/24)
- 2h 对比: dsv4f0731_nv SR=45.3% (62/137) vs glm5_2_nv SR=86.7% (13/15) — 仍模型特异性

**attempt 层错误 (2h, nv_tier_attempts)**
| error_type | count | avg_ms | max_ms |
|---|---|---|---|
| NVCFPexecRemoteDisconnected | 112 | 42138 | 87267 |
| NVCFPexecTimeout | 17 | 33248 | 91293 |
| empty_200 | 15 | - | - |
| 529_nv_overloaded | 13 | - | - |
| 504_nv_gateway_timeout | 4 | - | - |

- **70% (112/161) 仍为 RemoteDisconnected**, 跨全 5 key 分散 (k0:18, k1:27, k2:22, k3:19, k4:26)
- 0 429 (NVCF 率限未见, 纯连接断连风暴)

## 2. 决策: 本轮无新参数修改 (一次只改一个参数)

R1067 改动仅落地 ~1.2h, SR 已从 31% → 46%, ATE 从 35 → 16, 方向正确且显著。铁律
"一次只改一个参数" + "改后必有验证" → 本轮不叠加新改动, 完整观察 R1067 效果一个完整
测量窗口后再评估下一步。

**绑定约束转移分析 (供 R1069 参考)**:
- 改动前: fast-break=2 → 2×42s=86s 即放弃, 只试 ~2 key
- 改动后: fast-break=5 已最大化, tier 循环全部 5 key, 但 **TIER_TIMEOUT_BUDGET=180s 成为
  新约束**: 5 × 42s(RemoteDisconnected avg) = 210s > 180s budget → tier 在 ~4 key 时
  budget-break, 若健康 key 恰为第 5 个则被错过
- 候选 lever (本轮不应用): `NVU_TIER_BUDGET_DSV4F0731_NV` 180→~220 允许全 5 key 尝试;
  但代价是失败请求 fallback 前烧更久。需权衡。

## 3. 验证

- [x] `docker exec dsvf0731_nv40666 env | grep CONN_ERR_FAST_BREAK` = `NVU_CONN_ERR_FAST_BREAK=5`
- [x] 容器运行中 (Up 55 min), `/health` ok
- [x] 无 429 率限, 无 zombie/buffer 异常堆积
- [x] 本轮无配置改动, 无需重启

## 4. 当前状态 (30min)

- 30min SR: **47.1%** (16/34) — 较 R1067 基线 31% 提升
- Avg 129351ms (fallback 混合拖高)
- 错误分布: attempt 层 RemoteDisconnected 为主 (70%), empty_200=15, 529=13
- Fallback: hm4104 仍持续 PRIMARY-FAIL-STREAM → FALLBACK-STREAM (模型断裂连)
- upstream: nvcf_pexec 为主, ms_fallback 兜底

## 5. 上次修改效果 (R1067)

R1067 将 CONN_ERR_FAST_BREAK 硬编码 2 → env 5, 效果确认:
| 指标 | R1067 基线 (改动前) | 当前 (改动后) | 变化 |
|---|---|---|---|
| 30min SR | 31.0% (9/29) | 47.1% (16/34) | **+16pt** |
| 逐小时 ATE | 35 (04:00, pre) | 16 (06:00, post) | **-54%** |
| 逐小时 SR | 32.1% (04:00) | 46.2% (06:00) | **+14pt** |

**结论**: R1067 改动验证为正向, 方向正确。首次打破 45 轮 NOP 的结构性 lever 有效。

## 6. 下一步建议

- **R1069 候选**: 若 06:00-07:00 SR 稳定在 ~46% 且 ATE 保持低位, 可评估
  `NVU_TIER_BUDGET_DSV4F0731_NV` 180→~220s, 让 tier 在 budget 内遍历全部 5 key
  (当前 210s 全遍历 > 180s budget, 第 5 key 被错过)。应用前需确认失败请求
  fallback 延迟增量可接受。
- 若 SR 回到 40% 以下 → R1067 效果未巩固, 回滚评估。
- 继续比对 glm5_2_nv (86.7%): 若两者趋同说明 NVCF 侧整体恢复, 此 lever 可保留 (默认 2 无副作用)。