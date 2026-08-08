# RN1067: NOP — NVCF 过载窗口已消退, SR回升 82.9%→92.9%, 残余错误(empty-200/IncompleteRead)为上游侧不可调, 不改参数

日期: 2026-08-08 18:14 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF pexec 链路)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

RN1066 报告 NVCF 侧持续 overload (RemoteDisconnected 均匀分布全 5 key/5 出口 IP + 显式 529 + all_tiers_exhausted×3, SR 82.9%)。本轮窗口显示 **NVCF 过载已明显消退**：SR 回升至 92.9%，30min 内 **0 all_tiers_exhausted / 0 RemoteDisconnected / 0 显式 529**。残余 6 个错误全部为**上游侧空/截断响应**，本地无可归因调参杠杆。

## 数据证据（全部镜像自 DB / 日志）

### 30min 主指标
- 总量 84，成功 78，错误 6，其他 0 → **SR = 92.9%** (RN1066: 82.9%)
- Avg/P50/P95/Max: 26777ms / 19791ms / 70202ms / 112889ms

### 30min 错误分类（全部上游侧，非超时/非预算）
| error_type | n | avg_ms |
|---|---|---|
| zombie_empty_completion | 5 | 21979 |
| NVStream_IncompleteRead | 1 | 35689 |

`zombie_empty_completion` avg 21979ms —— 这些请求**正常完成**(未超时), NVCF 返回 200 但无实际内容, 是上游劣化信号, 与超时无关。`NVStream_IncompleteRead` 35689ms < UPSTREAM_TIMEOUT=50s, 为 NVCF 主动截断流, 非我方超时。两者均非本地参数可干预。

### 429 / key 轮转
- 30min 请求级 429 = **0**; all_tiers_exhausted = **0**
- `key_cycle_429s` per-key: 0|24, 1|59, 2|1 —— 窗口内共 ~84 次中间态 429 但**全部被 key 轮转吸收**, 无请求以 429 失败。key 轮转机制健康。

### per-key 200 延迟 (key|count|avg|p95)
| key | n | avg_ms | p95_ms | 错误 |
|---|---|---|---|---|
| 0 | 19 | 25846 | 75560 | zombie×1 |
| 1 | 15 | 22151 | 58545 | zombie×1 |
| 2 | 13 | 16184 | 38728 | zombie×2 + IncompleteRead×1 |
| 3 | 16 | 35898 | 90153 | zombie×1 |
| 4 | 15 | 33039 | 66423 | 0 |

无**既慢又错**的单 key：key2 错误最多(3)但延迟最低(16.2s)；key3 延迟最高(35.9s)但 0 错误。zombie 均匀散布于 key0-3，非单 key/SOCKS5 代理劣化。

### upstream / finish_reason
- upstream: nvcf_pexec 84/84 (100%), integrate 0
- finish_reason: tool_calls 56 / stop 22 (正常 tool 负载)

### 趋势
| 窗口 | SR | 备注 |
|---|---|---|
| 30min | 92.9% (78/84) | 6 错误, 全上游空/截断 |
| 3h 逐小时 | 10:00=92.5%, 09:00=86%, 08:00=92.3%, 07:00=90.1% | 逐小时恢复中 |
| 6h | 92.5% (637/689) | |
| 24h | all_tiers_exhausted=34 | 滚动口径, 与 RN1066 的 31 持平, 但 30min 内已为 0 |

### fallback
- hm4104 近 5min 采集时点无 fallback 日志 (FALLBACK-STREAM / PRIMARY-BREAKER-SKIP-STREAM 均未见)
- 容器 `dsvf0731_nv40666` Up 16h, /health ok, 5 keys, port 40666

## 为何不改参数（逐项排除）

- `UPSTREAM_TIMEOUT=50`: zombie 21979ms 正常完成、IncompleteRead 35689ms<50s —— 都不是超时截断, 调高/调低均无效。
- `TIER_BUDGET=180`: 30min 内 0 ATE, budget 未烧, 无需调整。
- `NVU_EMPTY_200_FASTBREAK=3`: 5 次 zombie 均匀分 4 个 key, 无单 key 连续 3 次, fast-break 不(也不应)触发; 空响应非本容器可控。
- `KEY_COOLDOWN/CONN_COOLDOWN/429_COOLDOWN`: 无单 key 持续劣化, key 轮转已高效吸收 429, 冷却无收益。
- 数据证明 **NVCF 过载在消退** (ATE/RemoteDisconnected/529 归零, SR 回升), 残余空响应为上游残余 flakiness, 改本地参数属「对着幻影调参」。

## 上次修改效果 (RN1066 → RN1067)

- **SR 回升**: 82.9% (34/41) → **92.9%** (78/84)。NVCF 过载窗口消退。
- **错误构成转变**: RemoteDisconnected/显式529/ATE×3 → **zombie_empty_completion×5 + IncompleteRead×1**。错误类型从「连接级过载」转为「上游空/截断响应」, 属恢复期残余, 非系统性劣化。
- **429 归零**: RN1066 未见明确 429 统计, 本轮请求级 429=0, 中间态 429 全被轮转吸收。
- **fallback**: 无 (RN1066 有 hm4104 fallback)。端到端主链路恢复。

## 结论

RN1048-1066 的 NVCF 侧持续 overload 在本窗口确认消退：SR 82.9%→92.9%，ATE/RemoteDisconnected/529 归零，fallback 停止。残余 6 个错误 (empty-200×5 + IncompleteRead×1) 均匀分布、无单 key 劣化、且均为上游空/截断响应 —— 本地参数无法干预。为保持 RN1048-1066 健康稳态基线，本轮 **NOP**。

## 下一步建议

- 持续监测：若 SR 回到 >95% 且空响应回落到 0，确认 NVCF 完全恢复，维持当前参数。
- 若 zombie_empty_completion 在 SR>95% 下仍持续 >3/30min，可考虑在 **HM1 nv_gw 层面**评估是否对空响应做重试兜底 —— 这是架构层决策，不在本容器自优化范围。
- 关注 key2：虽延迟最低但错误最多(3)，若后续错误持续集中于 key2 而延迟也恶化，才检查其 SOCKS5 出口 (NVCF 侧)。
- 保持当前参数观测；仅在 NVCF 完全恢复后仍有模式化错误聚集时，才重新评估超时/预算/fast-break 阈值。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] 数据完整: 30min SR/延迟/错误分类/per-key/upstream/finish_reason/429/key_cycle/6h/3h/24h/fallback 均已采集
- [x] 错误分类: zombie×5 + IncompleteRead×1, 全上游侧, 无 ATE/RemoteDisconnected/529/请求级429
- [x] per-key: 无既慢又错单key, zombie 均匀分布, key 轮转健康 (84 次中间态429全吸收)
- [x] 决策数据驱动: SR 92.9% 回升趋势 + 0 ATE + 0 请求级429 + 0 fallback → NOP, 不扰动恢复中链路