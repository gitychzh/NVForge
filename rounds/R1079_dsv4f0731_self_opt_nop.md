# R1079: dsv4f0731_nv self-opt — NOP (NVCF RemoteDisconnected 风暴缓释, 30min 窗口健康且呈恢复趋势)

日期: 2026-08-07 ~08:36 (UTC)

## 1. 数据 (30min 窗口 @08:34 采集 + attempt 级分析)

### 主指标
- **SR = 96.1% (123/128)**, avg=16678ms, p50=9352ms, p95=180038ms
- 30min 错误: all_tiers_exhausted=5 (avg 178993ms)
- **429 计数 = 0** (无 429 冷却杠杆)
- upstream_type: 100% nvcf_pexec, **integrate 0 请求**
- finish_reason: tool_calls=108, stop=15 (正常)

### attempt 级错误分布 (30min, nv_tier_attempts)
| error_type | count | avg_ms |
|---|---|---|
| pexec_success | **134** | **3365** |
| NVCFPexecRemoteDisconnected | 17 | 40465 |
| NVCFPexecTimeout | 3 | 37386 |
| 504_nv_gateway_timeout | 2 | - |
| 529_nv_overloaded | 2 | - |
| empty_200 | 1 | - |
| budget_exhausted_after_connect | 1 | 507 |

**关键洞察**: pexec_success avg=**3.4s** — 链路健康时极快。但 RemoteDisconnected 每次烧 ~40s, 5 key 各烧 ~40s = 200s > 180s budget → 触发 all_tiers_exhausted。

### per-key 错误 (30min) — 均匀跨全 5 key
| key | success | RD | Timeout | 其他 |
|---|---|---|---|---|
| k0 | 27 | 2 | 1 | 529:1, budget:1 |
| k1 | 26 | 3 | 1 | empty_200:1 |
| k2 | 27 | 5 | 0 | - |
| k3 | 27 | 5 | 1 | - |
| k4 | 27 | 2 | 0 | 504:2, 529:1 |

**无单 key 劣化** — RemoteDisconnected 均匀分散 (2-5/key), 排除 key 代理/出口问题。

### per-key 200 延迟 (全部健康)
k0: 23@9271, k1: 26@9874, k2: 26@11522, k3: 25@10454, k4: 23@9082 — 5 key 全部正常出 200, 延迟接近。

### 趋势 (恢复中)
| 时段 | total | ok | err | SR |
|---|---|---|---|---|
| 22:00 | 166 | 139 | 27 | 83.7% |
| 23:00 | 208 | 191 | 17 | 91.8% |
| 00:00 | 173 | 166 | 7 | 96.0% |
| 30min | 128 | 123 | 5 | **96.1%** |
| 6h | 1112 | 1027 | 85 | **92.4%** |

### fallback 日志 (hm4104, 最近 5min)
仅 08:31-08:33 有 PRIMARY-FAIL-STREAM 502 + PRIMARY-BREAKER-SKIP — 与 30min 窗口的 5 次 all_tiers_exhausted 吻合。风暴已从 22:00 的 27 错/时降至当前 ~5 错/30min。

## 2. 根因判定 (改前必有数据)

延续 R1021-R1078 的 **NVCF 模型特异性劣化风暴** (function_id 52e1ddb6):
1. **错误跨全 5 key 均匀分散** (RD 2-5/key), 无单 key 劣化 → 无 key 冷却/轮转/代理 lever 可解。
2. **NVCFPexecRemoteDisconnected avg=40s** — 上游保持连接 ~40s 后主动断开, 本容器 UPSTREAM_TIMEOUT=90 未触发, 非本容器可控。
3. **pexec_success avg=3.4s** — 链路/代理/出口健康; 故障仅在 NVCF function 执行层。
4. **429 = 0**, fast-break 先耗尽 key, 无 429 冷却杠杆空间。
5. **趋势恢复**: 22:00 83.7% → 00:00 96% → 30min 96.1%, 6h 92.4% 且上行。

## 3. 决策: NOP (无参数修改)

无单参数 lever 可修复全 5 key 模型特定上游 RemoteDisconnected。错误为上游主动断开 (40s at RD), 非超时/fast-break/key-cycling 可控。维持 R1067 最佳配置, 等待 NVCF deepseek-v4-flash-0731 function 完全恢复。

## 4. 验证

- [x] `/health` OK, 5 keys, proxy_role=passthrough, port=40666
- [x] 容器 dsvf0731_nv40666 Up 15 hours, 无重启, 无 env 改动
- [x] 15min 窗口 SR=94.4% (72 req, 68 ok), 恢复态势确认
- [x] hm4104 fallback 仅 08:31-08:33 短暂触发, 与 all_tiers_exhausted 吻合

## 5. 下一步建议

若 RD 风暴持续且有统计意义 (6h SR<90%), 可考虑框架级选项: 为 dsv4f0731_nv 启用 integrate.api 路由 (NV_KEY_INTEGRATE_KEYS) 作为 pexec 的失败旁路, 利用 integrate 与 pexec 不同上游路径规避 RD。当前 SR 已恢复, 无需干预。