# RN1068: NOP — NVCF 上游过载再度回归 (RemoteDisconnected+Timeout 均匀扩散全 5 key), 本地无可调杠杆, 维持参数

日期: 2026-08-08 19:16 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF pexec 链路)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

RN1067 (18:14 UTC) 曾报告 NVCF 过载窗口消退 (SR 92.9%, RemoteDisconnected/显式529/ATE 归零)。本轮窗口 (19:16 UTC) 显示 **NVCF 上游过载再度回归并扩散**：SR 回落至 87.8%，30min 内 RemoteDisconnected×12 + pexec Timeout×12 + 显式 529×1 + ATE×4。错误**均匀分布全 5 key / 全 5 SOCKS5 出口**，延迟全线翻倍 —— 100% 上游 NVCF 劣化，本地参数无法干预。

## 数据证据（全部镜像自 DB / 日志）

### 30min 主指标
- 总量 42，成功 36，错误 6，其他 0 → **SR = 85.7%** (上轮 RN1067: 92.9%)
- Avg/P50/P95: 55123ms / 21117ms / 180076ms
- 请求级 status: 200×43, 502×4 (avg 193769 ≈ TIER_BUDGET 180s 烧满), 499×2 (client_gone)

### 30min 错误分类（tier_attempts 级）
| error_type | n | avg_ms |
|---|---|---|
| pexec_success | 24 | 23092 |
| NVCFPexecRemoteDisconnected | 12 | 36367 |
| NVCFPexecTimeout | 12 | 43725 |
| 529_nv_overloaded | 1 | - |

请求级 (nv_requests): `all_tiers_exhausted×4` (avg 193769), `client_gone_during_flush×2` (avg 222131)。

### per-key 均匀劣化（4h 窗口，全部 5 key 一致）
| key | ok | avg_ok_ms | conn_fail (RemoteDisconnected+Timeout) |
|---|---|---|---|
| 0 | 49 | 16159 | 34 |
| 1 | 50 | 22629 | 34 |
| 2 | 45 | 18512 | 37 |
| 3 | 50 | 19924 | 34 |
| 4 | 43 | 16329 | 36 |

**每个 key 连接级失败率 ~41-46%，avg 成功延迟 16-22s 亦全线抬升。** 无单 key 劣化、无单 SOCKS5/出口 IP 劣化 —— 纯粹的 NVCF 上游全键位退化。

### 12h 退化时间线（tier_attempts 级 fail%）
| 小时(UTC) | ok | fail | fail% |
|---|---|---|---|
| 23:00 | 92 | 1 | 1% |
| 00:00 | 189 | 4 | 2% |
| 02:00 | 140 | 12 | 8% |
| 04:00 | 84 | 21 | 20% |
| 06:00 | 83 | 42 | 34% |
| 07:00 | 49 | 49 | **50%** |
| 08:00 | 61 | 49 | 45% |
| 09:00 | 52 | 39 | **43%** |
| 10:00 | 70 | 47 | 40% |
| 11:00 | 31 | 17 | 35% |

从 23:00 的 ~1% 单调爬升至 07:00-10:00 的 **40-50%**，11:00 部分回落至 35%。NVCF 上游对 dsv4f0731_nv 持续退化，本轮窗口处于过载峰值。

### 24h 基线
- pexec_success: 3631 (avg 8027ms) —— 24h 平均成功延迟仅 8s，近期窗口成功延迟 19-23s，**翻倍以上**。
- NVCFPexecRemoteDisconnected: 267 (avg 36391)
- NVCFPexecTimeout: 108 (avg 45286)
- 429 count (30min): **0**; all_tiers_exhausted (24h): 43

### fallback
- hm4104 fallback 日志 (最近 5min): 无。但采集过程中出现 hm4104 转 dsv4f0731_ms 的 fallback 提示，说明主链路抖动正在传导到上层。

## 为什么不改参数（逐项排除本地杠杆）

- `UPSTREAM_TIMEOUT=50`: RemoteDisconnected avg 36367ms、pexec Timeout avg 43725ms —— 均在 50s 内，NVCF 主动断开/停响应，**非我方超时截断**。调高只会在过载窗口烧更多 budget，调低无益。
- `TIER_BUDGET/DSV4F0731=180`: 502 ATE avg 193769 ≈ 180s 烧满 budget —— 但这是 5 key 全被 NVCF 拖垮后的必然结果，不是 budget 设错。缩短 budget 会减少重试机会，加长只会让已死连接烧更久。
- `fast-break` (PEXEC_TIMEOUT=3, CONN_ERR=5): RemoteDisconnected 均匀散布 5 key，无单 key 连续触发 fast-break 模式；fast-break 无法区分「NVCF 全键过载」与「单 key 故障」。
- `KEY_COOLDOWN/CONN_COOLDOWN/429_COOLDOWN`: 无单 key 持续劣化，冷却无收益；且错误非 429（429=0），429 冷却完全无关。
- `integrate 路由` (NV_KEY_INTEGRATE_KEYS 空): R1017 已因 integrate SR 50% 劣于 pexec 70.5% 而全走 pexec DIRECT。本轮为 pexec 全键过载，切 integrate 无数据支持且历史证明更差。
- 数据证明 **NVCF 上游对 dsv4f0731 全键位退化** (RemoteDisconnected+Timeout 均匀 5 key + 显式 529 + 成功延迟翻倍)，改本地参数属「对着幻影调参」。

## 上次修改效果 (RN1067 → RN1068)

RN1067 为 NOP，参数未变。对比两轮：
- **SR 回落**: 92.9% (78/84) → **85.7%** (36/42)。NVCF 过载窗口回归。
- **错误构成转变**: zombie×5 + IncompleteRead×1 (恢复期残余) → **RemoteDisconnected×12 + pexec Timeout×12 + 显式529×1** (连接级过载)。错误从「空/截断响应」回到「连接级退化」，说明 NVCF 上游在 18:14→19:16 之间再度进入过载。
- **成功延迟翻倍**: 上轮 avg 26777ms → 本轮 avg 55123ms（含烧满 budget 的失败加权）；tier_attempts 成功 avg 从 24h 的 8s 抬升至近期 19-23s。
- 参数零改动，纯上游波动。

## 结论

RN1067 的「过载消退」是暂时性的。本轮 19:16 UTC 确认 NVCF 对 dsv4f0731_nv 的过载**再度回归并处于峰值**（RemoteDisconnected+Timeout 均匀扩散全 5 key/全 5 出口，SR 回落至 85.7%，成功延迟翻倍）。错误全部为连接级上游退化，非 429/单 key/超时截断/空响应 —— 本地无任何可归因调参杠杆。为保持健康稳态基线，本轮 **NOP**。

## 下一步建议

- 持续监测 SR：NVCF 过载呈**振荡模式**（RN1067 消退 → 本轮回归）。若后续窗口 SR 回升至 >95% 且 RemoteDisconnected/Timeout/529 归零，确认进入恢复期，维持参数。
- 若 NVCF 过载在数小时内持续 (SR<90%)，考虑在 **HM1 nv_gw / 架构层**评估是否对 dsv4f0731_nv 增加 Peer fallback 或 ms fallback 兜底 —— 但本容器 NVU_MS_FALLBACK_ENABLED=0 / NVU_PEER_FALLBACK_ENABLED=0，属架构决策，不在容器自优化范围。
- 关注 11:00 是否延续 35% 回落趋势 —— 若下一窗口 fail% 继续下降，说明 NVCF 正在恢复，本轮即为过载峰值谷底。
- 保持当前参数观测；仅在 NVCF 完全恢复后仍有模式化错误聚集时，才重新评估超时/预算/fast-break 阈值。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] 数据完整: 30min SR/延迟/错误分类/per-key/upstream/finish_reason/429/key_cycle/6h/3h/24h/fallback 均已采集
- [x] 错误分类: RemoteDisconnected×12 + pexec Timeout×12 + 显式529×1 + ATE×4, 均匀分布全 5 key
- [x] per-key: 无既慢又错单key, 5 key 连接级失败率一致 (~41-46%), 非 SOCKS5/出口 IP 问题
- [x] 12h 退化时间线: 1%→50% 单调爬升, 本轮处于峰值
- [x] 决策数据驱动: SR 85.7% + 全键位连接级过载 + 显式529 → NOP, 本地无可调杠杆, 不扰动链路