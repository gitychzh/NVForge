# R1244: dsvf0731_nv40666 self-opt NOP — SR 78.2% 回落, 17错全为 NVCF 过载烧满 budget (ATE×14+stream_cap×3), 24h ATE 破 140 阈值但属上游过载非容器杠杆

> 时间: 2026-08-09 19:16 UTC (R1243 后 ~7min, 采集窗口 ~11:16 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
> 状态: **NOP (无参数修改)** — 30min SR **78.2%** (61/78), 较 R1243 (92.5%) 回落 14.3pt;
> 17 错误: **14× all_tiers_exhausted** (tier 级 5-key 全烧满 180s budget = NVCF 过载)
> + **3× stream_absolute_cap** (NVU_STREAM_ABSOLUTE_CAP_S≈150s 安全帽兜底, 长流 tool_calls);
> 无净 429, 无 key 劣化 (k0 负载最重但 200 延迟最低 35s), upstream 100% pexec 正常, tier_attempts 空;
> **当前小时 (11:00) 为活跃过载 burst**: 37 req / 26 ok / 70% SR — 24h ATE 从 139 破 140 升至 147,
> 触发 R1243 设定阈值, 但该阈值明确指向 **上游/调度层治理, 非本容器参数**。

## 结论: NOP (不改任何参数)

## 依据 (30min 窗口, ~11:16 UTC)

| 指标 | 值 |
|---|---|
| 总量/成功/失败 | 78 / 61 / 17 (SR=78.2%) |
| Avg / P50 / P95 | 87871 / 67817 / 180993 ms |
| 净429 | 0 |
| upstream_type | nvcf_pexec 77 req, 61 SR=79.2% (100% pexec, integrate 0) |
| finish_reason | tool_calls 51, stop 3, null 7 |

### 错误分类 (17错: 全为 budget 烧满 = NVCF 过载)
| error_type | n | avg_ms | 判定 |
|---|---|---|---|
| all_tiers_exhausted | 14 | 169194 | tier 级, 5 key 全烧满 TIER_TIMEOUT_BUDGET=180s → NVCF 过载残余 |
| stream_absolute_cap | 3 | 155016 | NVU_STREAM_ABSOLUTE_CAP_S≈150s 安全帽兜底, 长流工具调用, 非参数失误 |

### per-key 200 延迟 (count/avg/p95)
- k0: 11 / 35202 / 64262 | k1: 17 / 82893 / 176988 | k2: 17 / 75033 / 145048 | k3: 11 / 50731 / 79787 | k4: 5 / 78031 / 166600
- **k0 负载不轻 (11 req) 但 avg 35s 最低** → k0 非劣化; k1/k2 avg 75-83s 偏慢但无净错误, 属过载延迟带。

### per-key 错误细分
- k0: all_tiers_exhausted 13 | k2: stream_absolute_cap 2 | k1: stream_absolute_cap 1 | null: all_tiers_exhausted 1
- **k0 ATE×13 为轮转起始位伪象** (tier 级 5-key 全失败归属 k0), 而 k0 200 延迟最低 → 铁证非 k0 代理故障。

### key_cycle_429s (内部循环计数, 非净错误)
- k0=27, k1=45, k2=5, k4=1
- k1 持续偏高(45)但 net 429=0, key manager 已吸收 → cooldown 工作正常, 无需调 KEY_COOLDOWN/NVU_KEYMGR_*。

### 6h/3h/24h 趋势
- 6h: 723 req, 627 SR=86.7%
- 3h 逐小时: 11h=37/26 **SR70%** (当前活跃过载 burst) | 10h=166/149 SR90% | 09h=140/125 SR89% | 08h=87/72 SR83%
- 24h all_tiers_exhausted = **147** (从 R1243 的 139 破 140, 升 8; 突破 R1243 设定阈值 140)

### hm4104 fallback (近 5min: 6 事件) — 过载震荡下游
- 19:12 502@180031ms + 切 fallback; 19:13×2 (breaker-SKIP + FALLBACK-STREAM); 19:14×3 (breaker-SKIP + FALLBACK-STREAM)
- 与 R1243 同型: NVCF 过载 → 烧满 180s budget → nv_gw 502 → 适配器切 ms_gw, breaker 短暂直走 fallback。传播链下游, 非本容器参数失误。

## 判定逻辑 (为什么 NOP)
1. **17 错误全部为 tier 级 budget 烧满** (ATE×14 + stream_cap×3): 无净 429、无真实 key 劣化 (k0 200 延迟最低却最多 ATE 归属 = 轮转起始位伪象)、无流截断/空响应, 容器层无杠杆可动。
2. **R1233/R1234 已论证收缩 NVU_TIER_BUDGET_DSV4F0731_NV 非正解**: 只让 primary 更快放弃并切 fallback, 不改善 NVCF 过载本身; 180s budget 是合理重试窗口, 保持不动。
3. **stream_absolute_cap 是安全帽而非故障**: 长流工具调用在 150s 安全帽兜底触发, 属正确保护行为, 非需要调大的失误。
4. **24h ATE 破 140 阈值 (147) 但属当前活跃过载 burst (11h SR70%)**: R1243 明确该阈值指向**上游/调度层治理** (并发/请求节流), **非本容器参数**。容器无并发/节流控制权。
5. **hm4104 fallback 活跃是 NVCF 过载震荡下游**: 6h SR 86.7%、24h ATE=147 为过载背景下波动, 传播链下游瞬态, 非本容器可持续调节的问题。

## 验证
- [x] `docker exec dsvf0731_nv40666 env` 参数未变 (TIER_COOLDOWN=90, NVU_TIER_BUDGET_DSV4F0731_NV=180, KEY_COOLDOWN=30, UPSTREAM_TIMEOUT=45)
- [x] /health = ok (dsvf0731_nv40666 Up 11 hours) — 容器健康, 无非健康参数
- [x] 容器未重启 (保持 11h uptime)

## 下一步建议
- **本容器已无可调杠杆**: ATE 破阈值 + 当前小时活跃过载, 印证需从**上游/调度层**治理 (NVCF 并发/请求节流、或 NVCF 侧过载消峰), 由基础设施侧而非本容器处理。
- 若下轮 30min SR 回升 ≥85% 且当前过载 burst 退去 (11h 后回归 89-90%), 确认是 NVCF 过载瞬态, 容器保持 NOP。
- 若 SR 持续 <85% 且 24h ATE 继续 >150 (持续累积), 上报基础设施层介入 NVCF 过载治理 — 本容器不擅自改 budget/冷却伪装修复。