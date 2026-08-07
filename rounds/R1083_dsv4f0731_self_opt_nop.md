# R1083: dsv4f0731_nv self-opt — NOP (NVCF 风暴缓释持续, 30min SR 97.1% 健康稳定)

日期: 2026-08-07 ~10:22 (BJT) = ~02:22 UTC

## 1. 数据 (30min 窗口 采集 + attempt 级分析)

### 主指标
- **SR = 97.1% (134/138)**, avg=17087ms, p50=9551ms, **p95=62412ms**
- 30min 错误: **all_tiers_exhausted=3** (avg 180048), **zombie_empty_completion=1** (avg 7822)
- **429 计数 = 0** (无 429 冷却杠杆)
- upstream_type: 100% nvcf_pexec (138/138), **integrate 0 请求**
- finish_reason: tool_calls=112, stop=22 (正常)
- tier_attempts: 窗口内无 attempt 行 (请求直接命中成功)

### per-key 200 延迟 (5 key 全部健康)
| key | total | ok | avg_ok_ms | max_ms |
|---|---|---|---|---|
| k0 | 28 | 28 | 14883 | 42517 |
| k1 | 27 | 27 | 10293 | 16943 |
| k2 | 26 | 26 | 10933 | 18396 |
| k3 | 24 | 24 | 12642 | 15689 |
| k4 | 29 | 29 | 18196 | 73357 |

**无单 key 劣化** — 5 key 全部 100% 出 200, 延迟接近 (10.3-18.2s), max 均 <74s。

### per-key 错误 (30min)
| key | error_type | count | avg_ms |
|---|---|---|---|
| k0 | all_tiers_exhausted | 3 | 180048 |
| k3 | zombie_empty_completion | 1 | 7822 |

all_tiers_exhausted 为 terminal 错误 (整 tier 5 key 循环耗尽 180s budget 后归因于 k0), 非 k0 单点故障 — k0 本窗 28/28 全成功验证。zombie_empty_completion 为 k3 单次空 200 缓冲帽, k3 本窗 24×200 全成功 → 偶发意义。

### key_cycle_429s 分布
0=13, 1=122, 2=3

**k1=122 为轮转伪影** (与 R1080/R1081/R1082 一致, 连续 4 轮): k1 为轮转首 key, 每次请求先 429-probe 后 fast-break 切走; k1 本窗 0 错误 + 27×200 全成功 → 非真实劣化。

### 趋势 (持续上行, 恢复稳定)
| 时段 | total | ok | err | SR |
|---|---|---|---|---|
| 23:00 | 138 | 129 | 9 | 93.5% |
| 00:00 | 291 | 282 | 9 | 96.9% |
| 01:00 | 263 | 253 | 10 | 96.2% |
| 02:00 | 101 | 99 | 2 | 98.0% |
| 30min | 138 | 134 | 4 | **97.1%** |
| 6h | 1434 | 1353 | 81 | **94.4%** |

24h all_tiers_exhausted=446 (历史累计, 非当前风暴)。

### fallback 日志 (hm4104, 最近 5min)
**(无 fallback 日志)** — 30min 窗口内 hm4104 无 fallback 触发, 本容器错误全部由自身消化。

## 2. 根因判定 (改前必有数据)

延续 R1021-R1082 的 **NVCF 模型特异性劣化风暴** (function_id 52e1ddb6) 缓释期:
1. **SR 97.1%, 6h 94.4% 且逐小时上行** (93.5%→96.9%→96.2%→98.0%) — 上游持续恢复、稳定。
2. **错误仅 4 次/30min** (all_tiers_exhausted=3 预算烧尽 + zombie_empty_completion=1 空 200), 归因 k0/k3 但两 key 均 100% 出 200 → 非 key 单点, 为整 tier 偶发远方长 hold。
3. **429 = 0**, fast-break 先耗尽 key, 无 429 冷却杠杆空间。
4. **k1 key_cycle_429s=122 为轮转伪影** (连续 4 轮确认), k1 0 错误 27×200 → 非真实劣化。
5. **pexec_success 链路健康** (avg 延迟 10.3-18.2s), 故障仅在 NVCF function 远端偶发长 hold。

## 3. 决策: NOP (无参数修改)

30min SR 97.1% > 95% NOP 阈值, 延迟稳定 (p50 9.5s), 无单 key 劣化, 趋势上行, 且本窗口 **hm4104 fallback=0**。无单参数 lever 有数据支撑需调整。

维持 R1067 最佳配置 (UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET=180, NVU_TIER_BUDGET_DSV4F0731_NV=180,
KEY_COOLDOWN=30, TIER_COOLDOWN=90, CONN fast-break=5, 429 base/max=120, EMPTY_200 fast-break=3),
等待 NVCF deepseek-v4-flash-0731 function 完全恢复。

**不采取整合预算调整**: NVU_TIER_BUDGET_DSV4F0731_NV=180 与 TIER_TIMEOUT_BUDGET_S=180 已对齐。
3 次 all_tiers_exhausted 均为上游远方长 hold 烧尽 budget, 提高 budget 只会让 502 更晚出现而不增
成功率; 降低 budget 会提前剪断本可成功的慢请求。当前 97.1% SR 下无收益。

**不采取 k1 429 冷却调整**: key_cycle_429s=122 为轮转伪影已 4 轮确认, k1 0 错误全成功, 无动作。

## 4. 验证

- [x] `/health` OK, 5 keys, proxy_role=passthrough, port=40666
- [x] 容器 dsvf0731_nv40666 Up 17 hours, 无重启, 无 env 改动
- [x] 30min SR=97.1%, 6h SR=94.4%, 延迟稳定 (p50 9.5s)
- [x] hm4104 fallback=0 (本窗口无 fallback 日志, 错误全由自身消化)

## 5. 下一步建议

- 上游持续恢复中, 保持 NOP 观察。若 6h SR 稳定 >95% 连续 2-3 轮, 可延长 NOP 轮间隔。
- 若 all_tiers_exhausted 单轮 >10 次 (SR<92%) 回归, 再评估 integrate.api 旁路
  (NV_KEY_INTEGRATE_KEYS) — 当前无需干预。
- 关注 zombie_empty_completion 是否累积: 若单轮 >3 次, 需评估 EMPTY_200_FASTBREAK=3 是否应
  下调 (当前 1 次, 偶发意义, 无动作)。