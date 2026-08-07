# R1080: dsv4f0731_nv self-opt — NOP (NVCF 风暴缓释, 30min 窗口健康且延迟显著改善)

日期: 2026-08-07 ~01:15 (UTC)

## 1. 数据 (30min 窗口 @01:15 采集 + attempt 级分析)

### 主指标
- **SR = 96.8% (152/157)**, avg=11254ms, p50=9750ms, **p95=17760ms**
- 30min 错误: all_tiers_exhausted=4 (avg 178883ms), stream_absolute_cap=1 (177533ms)
- **429 极低**: key_cycle_429s 分布 0=20, 1=137, 2=3, 3=2 (fast-break 正常消化)
- upstream_type: 100% nvcf_pexec, **integrate 0 请求**
- finish_reason: tool_calls=140, stop=19 (正常)

**对照 R1079 (08:34)**: avg 16678ms → **11254ms**, p95 180038ms → **17760ms**。延迟显著回落，
风暴期特征 (p95=180s 全烧 budget) 已消除。

### attempt 级错误分布 (30min, nv_tier_attempts)
| error_type | count | avg_ms |
|---|---|---|
| pexec_success | **132** | **3197** |
| NVCFPexecRemoteDisconnected | 18-22 | 36021 |
| empty_200 | 3 | - |
| 529_nv_overloaded | 1-2 | - |
| NVCFPexecTimeout | 1 | 15732 |
| budget_exhausted_after_connect | 1 | 507 |

**关键洞察**: pexec_success avg=**3.2s** — 链路极健康。RD 每次烧 ~36s, 5 key 各 1 次 = ~180s
恰耗满 TIER_TIMEOUT_BUDGET=180, 触发 all_tiers_exhausted (4 次)。

### per-key 200 延迟 (全部健康)
| key | total | ok | avg_ok_ms |
|---|---|---|---|
| k0 | 29 | 28 | 10757 |
| k1 | 36 | 36 | 16164 |
| k2 | 30 | 29 | 14983 |
| k3 | 29 | 28 | 9918 |
| k4 | 30 | 30 | 10291 |

**无单 key 劣化** — 5 key 全部正常出 200, 延迟接近, 错误均匀 (0-1/key)。

### 趋势 (恢复且稳定)
| 时段 | total | ok | err | SR |
|---|---|---|---|---|
| 22:00 | 170 | 139 | 31 | 81.8% |
| 23:00 | 209 | 191 | 18 | 91.4% |
| 00:00 | 291 | 282 | 9 | 96.9% |
| 30min | 157 | 152 | 5 | **96.8%** |
| 6h | 1235 | 1146 | 89 | **92.8%** |

RD 逐小时 (attempt 级): 21:00=31, 22:00=21, 23:00=36, 00:00=35, 01:00(partial)=9 — 仍高位但
稳定, 未再爆发式增长。24h all_tiers_exhausted=467 (历史累计, 非当前风暴)。

### fallback 日志 (近 5min)
01:10-01:15 见 2 次 all_tiers_exhausted (502, 180s) + 1 次 stream_absolute_cap — 触发 hm4104
fallback 到 dsv4f0731_ms (与窗口内 4+1 次错误吻合)。间歇性, 非持续风暴。

## 2. 根因判定 (改前必有数据)

延续 R1021-R1079 的 **NVCF 模型特异性劣化风暴** (function_id 52e1ddb6):
1. **错误跨全 5 key 均匀分散** (RD 18-22 次跨 5 key, 0-1 错/key 于请求级) — 无单 key 劣化,
   无 key 冷却/轮转/代理 lever 可解。
2. **NVCFPexecRemoteDisconnected avg=36s** — 上游保持连接 ~36s 后主动断开, 本容器
   UPSTREAM_TIMEOUT=90 未触发, 非本容器可控。
3. **pexec_success avg=3.2s** — 链路/代理/出口健康; 故障��在 NVCF function 执行层。
4. **429 极低** (key_cycle 1 为主 = fast-break 正常消化), 无 429 冷却杠杆空间。
5. **趋势稳定**: 22:00 81.8% → 00:00 96.9% → 30min 96.8%, 6h 92.8% 且上行。
6. **p95 从 180s 剧降至 17.8s** — 表明风暴期"每请求烧满 budget"的特征已消失, 上游显著恢复。

## 3. 决策: NOP (无参数修改)

无单参数 lever 可修复全 5 key 模型特定上游 RemoteDisconnected。错误为上游主动断开
(36s at RD), 非超时/fast-break/key-cycling 可控。维持 R1067 最佳配置
(UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET=180, CONN fast-break=3, KEY_COOLDOWN=30,
TIER_COOLDOWN=90, 429 base/max=120, EMPTY_200 fast-break=3), 等待 NVCF
deepseek-v4-flash-0731 function 完全恢复。

## 4. 验证

- [x] `/health` OK, 5 keys, proxy_role=passthrough, port=40666
- [x] 容器 dsvf0731_nv40666 Up 16 hours, 无重启, 无 env 改动
- [x] 6h SR=92.8%, 30min SR=96.8%, 延迟显著改善 (p95 17.8s)
- [x] hm4104 fallback 仅间歇触发 (01:10-01:15 2 次), 与 all_tiers_exhausted 吻合

## 5. 下一步建议

- 若 RD 风暴持续且有统计意义 (6h SR<90%), 可考虑框架级选项: 为 dsv4f0731_nv 启用
  integrate.api 路由 (NV_KEY_INTEGRATE_KEYS) 作为 pexec 的失败旁路。当前 SR 已恢复稳定,
  无需干预。
- 持续监控 RD 6h 趋势: 若回落 <10/h 则上游彻底恢复, 可减少 NOP 轮频率。
- 关注 hm4104 fallback 频率: 若间歇 fallback 持续, 可评估 ms_gw dsv4f0731_ms 作为
  双活旁路 (但不作为主动变更, 需数据支撑)。