# R1082: dsv4f0731_nv self-opt — NOP (NVCF 风暴缓释持续, 30min SR 95.9% 健康稳定)

日期: 2026-08-07 ~09:54 (BJT) = ~01:54 UTC

## 1. 数据 (30min 窗口 采集 + attempt 级分析)

### 主指标
- **SR = 95.9% (117/122)**, avg=16528ms, p50=9477ms, p95=35323ms
- 30min 错误: **all_tiers_exhausted=5** (avg 179756ms — 全 180s budget 烧尽)
- **429 计数 = 0** (无 429 冷却杠杆)
- upstream_type: 100% nvcf_pexec, **integrate 0 请求**
- finish_reason: tool_calls=99, stop=18 (正常)
- tier_attempts: 窗口内无 attempt 行 (无 key 级失败, 请求直接命中成功)

### per-key 200 延迟 (5 key 全部健康)
| key | total | ok | avg_ok_ms | max_ms |
|---|---|---|---|---|
| k0 | 23 | 23 | 9849 | 13273 |
| k1 | 22 | 22 | 7814 | 12065 |
| k2 | 25 | 25 | 10798 | 31332 |
| k3 | 24 | 24 | 8994 | 13451 |
| k4 | 23 | 23 | 10149 | 13328 |

**无单 key 劣化** — 5 key 全部 100% 出 200, 延迟接近 (7.8-10.8s), max 均 <32s。

### per-key 错误 (30min)
| key | error_type | count | avg_ms |
|---|---|---|---|
| k0 | all_tiers_exhausted | 5 | 179756 |

all_tiers_exhausted 为 terminal 错误 (整 tier 5 key 循环耗尽 180s budget 后归因于 k0), 非 k0 单点故障 — k0 本窗 23/23 全成功验证。

### key_cycle_429s 分布
0=7, 1=115

**k1=115 为轮转伪影** (与 R1080/R1081 一致): k1 为轮转首 key, 每次请求先 429-probe 后 fast-break 切走; k1 本窗 0 错误 + 22×200 全成功 → 非真实劣化。

### 趋势 (持续上行, 恢复稳定)
| 时段 | total | ok | err | SR |
|---|---|---|---|---|
| 22:00 | 25 | 24 | 1 | 96.0% |
| 23:00 | 208 | 191 | 17 | 91.8% |
| 00:00 | 291 | 282 | 9 | 96.9% |
| 01:00 | 235 | 227 | 8 | 96.6% |
| 30min | 122 | 117 | 5 | **95.9%** |
| 6h | 1422 | 1340 | 82 | **94.2%** |

24h all_tiers_exhausted=449 (历史累计, 非当前风暴)。

### fallback 日志 (hm4104, 最近 5min)
09:51-09:52 见 `PRIMARY-FAIL-STREAM nv_gw 流式 server_5xx status=502 after 180064ms` + 多次
`FALLBACK-STREAM` 切到 ms_gw + `PRIMARY-BREAKER-SKIP`。

**502 after 180064ms = 本容器 180s TIER_TIMEOUT_BUDGET 烧尽** (对应 5 次 all_tiers_exhausted)。
即 hm4104 侧 5 次请求因本容器 upstream 风暴耗尽 budget 而上游 502, 正确 fallback 到 ms_gw —
这是本容器错误的直接下游成本, 缺口已由 adapter fallback 消化 (非漏损)。

## 2. 根因判定 (改前必有数据)

延续 R1021-R1081 的 **NVCF 模型特异性劣化风暴** (function_id 52e1ddb6) 缓释期:
1. **SR 95.9%, 6h 94.2% 且逐小时上行** (91.8%→96.9%→96.6%) — 上游持续恢复、稳定。
2. **错误仅 5 次/30min** (全 all_tiers_exhausted, 180s budget 烧尽), 归因 k0 但 k0 23×200 全成功
   → 非 key 单点, 为整 tier 偶发远方长 hold。
3. **429 = 0**, fast-break 先耗尽 key, 无 429 冷却杠杆空间。
4. **k1 key_cycle_429s=115 为轮转伪影** (R1080/R1081 同款), k1 0 错误 22×200 → 非真实劣化。
5. **pexec_success 链路健康** (avg 延迟 7.8-10.8s), 故障仅在 NVCF function 远端偶发长 hold。

## 3. 决策: NOP (无参数修改)

30min SR 95.9% > 95% NOP 阈值, 延迟稳定 (p50 9.5s, p95 35s), 无单 key 劣化, 趋势上行。
无单参数 lever 有数据支撑需调整。

维持 R1067 最佳配置 (UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET=180, CONN fast-break=5,
KEY_COOLDOWN=30, TIER_COOLDOWN=90, 429 base/max=120, EMPTY_200 fast-break=3), 等待 NVCF
deepseek-v4-flash-0731 function 完全恢复。

**不采取整合预算调整**: NVU_TIER_BUDGET_DSV4F0731_NV=180 与 TIER_TIMEOUT_BUDGET_S=180 已对齐。
5 次 all_tiers_exhausted 均为上游远方长 hold 烧尽 budget, 提高 budget 只会让 502 更晚出现而不增
成功率; 降低 budget 会提前剪断本可成功的慢请求。当前 95.9% SR 下无收益。

**不采取 k1 429 冷却调整**: key_cycle_429s=115 为轮转伪影已 3 轮确认, k1 0 错误全成功, 无动作。

## 4. 验证

- [x] `/health` OK, 5 keys, proxy_role=passthrough, port=40666
- [x] 容器 dsvf0731_nv40666 Up 16 hours, 无重启, 无 env 改动
- [x] 30min SR=95.9%, 6h SR=94.2%, 延迟稳定 (p50 9.5s)
- [x] hm4104 fallback 502 对应本容器 5 次 all_tiers_exhausted, 已正确 digest 到 ms_gw

## 5. 下一步建议

- 上游持续恢复中, 保持 NOP 观察。若 6h SR 稳定 >95% 连续 2-3 轮, 可延长 NOP 轮间隔。
- 若 all_tiers_exhausted 单轮 >10 次 (SR<92%) 回归, 再评估 integrate.api 旁路
  (NV_KEY_INTEGRATE_KEYS) — 当前无需干预。
- 关注 hm4104 PRIMARY-BREAKER-SKIP 是否在 502 后持续 OPEN — 若 breaker 长时间不恢复导致
  大量直走 fallback, 属 adapter breaker 配置, 不在本容器 env 范围。