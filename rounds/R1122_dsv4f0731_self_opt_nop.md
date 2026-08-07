# R1122: dsv4f0731_nv40666 Self-Optimization (NOP — Healthy & Stable)

**Datetime**: 2026-08-08 02:55 UTC (10:55 Beijing)
**Container**: dsvf0731_nv40666 (port 40666)
**Model**: dsv4f0731_nv via NVCF pexec
**Verifier**: 本机 (HM2, opc2_uname)

## 结论
**不修改参数 (NOP)。** 30min SR=100%，0 请求级错误，0 429，0 fallback，全 pexec 且 per-key 均衡。系统处于高度健康稳定状态，无任何可调项需要介入。

## 30min 窗口 (脚本采集 02:52 UTC)

| 指标 | 值 |
|------|-----|
| Total | 155 |
| Success | 155 |
| **SR** | **100%** |
| Avg / P50 / P95 / P99 | 12,897ms / 9,884ms / 27,581ms / 62,816ms |
| 请求级错误 | **0** (错误分类为空) |
| 429s | **0** |
| Fallback (hm4104, 5min) | **None** |
| Upstream | 100% nvcf_pexec (155/155) |
| finish_reason: tool_calls / stop | 135 / 20 |

## Per-Key 性能 (30min, 200 延迟)

| Key | Count | avg_ms(p50/p95) |
|-----|-------|-----------------|
| 0 | 31 | 12,673 (25,633) |
| 1 | 30 | 13,479 (23,168) |
| 2 | 31 | 12,061 (28,210) |
| 3 | 33 | 14,327 (29,044) |
| 4 | 30 | 11,836 (25,383) |

5 个 key 全部健康，无单 key 劣化。per-key 错误: 无。key_cycle_429s: k0=69, k1=86 (内部循环计数，非错误，实际请求级 429=0)。

## 趋势

| 时段 | Total | Success | Failed | SR | Avg |
|------|-------|---------|--------|-----|-----|
| 30min | 155 | 155 | 0 | **100%** | 12,897ms |
| 6h | 1,750 | 1,739 | 11 | **99.37%** | — |
| 3h 18:00 | 299 | 299 | 0 | 100% | 11,610ms |
| 3h 17:00 | 279 | 273 | 6 | 97.8% | 11,786ms |
| 3h 16:00 | 273 | 273 | 0 | 100% | 13,430ms |
| 3h 15:00 | 35 | 35 | 0 | 100% | 10,702ms |

### 24h dsv4f0731_nv ATE (新鲜查询)
`all_tiers_exhausted` for tier='dsv4f0731_nv' in last 24h: **0 rows**. 预采集脚本报的 24h ATE=121 属其他模型 tier 的汇总，本 tier 无耗尽事件。

### 2h tier-attempts 内部循环 (2026-08-08 00:55~02:55 UTC)
| error_type | count | avg_ms |
|-----------|-------|--------|
| pexec_success | 361 | 5,680 |
| NVCFPexecRemoteDisconnected | 12 | 41,783 |
| empty_200 | 2 | — |
| 500_nv_error | 1 | — |
| NVCFPexecTimeout | 1 | 50,812 |

请求级 SR=100% 表明这些内部尝试失败已全部被 key-cycling 机制优雅接管（同一请求内换 key 重试成功），未上升到请求级失败。

## 当前参数 (本次未改动, env 实值)

| 参数 | 当前值 |
|------|--------|
| UPSTREAM_TIMEOUT | 50 |
| TIER_TIMEOUT_BUDGET_S | 180 |
| NVU_TIER_BUDGET_DSV4F0731_NV | 180 |
| NVU_TIER_BUDGET_DSV4F_NV | 180 |
| KEY_COOLDOWN_S | 30 |
| TIER_COOLDOWN_S | 90 |
| NVU_KEYMGR_429_BASE_COOLDOWN | 120 |
| NVU_KEYMGR_429_MAX_COOLDOWN | 120 |
| NVU_KEYMGR_CONN_BASE/MAX/LONG | 30 / 60 / 120 |
| NVU_KEYMGR_CONN_FAIL_THRESHOLD | 3 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 3 |
| NVU_EMPTY_200_FASTBREAK | 3 |
| NVU_BUFFER_TIMEOUT_STAIRS | 90,90,90,90,90 |
| NVU_PROBE_TIMEOUT | 10 |
| NV_KEY_INTEGRATE_KEYS | (空 — integrate 未启用) |

/health 返回 ok，port 40666，5 keys，模型/ti 列表完整。容器 Up 33 分钟 (此前经历过一次重启/重建，当前 env 已确认生效)。

## NOP 原因

1. **30min SR=100%** — 远超 95% 阈值
2. **6h SR=99.37%** — 持续高位稳定，无退化
3. **0 请求级错误、0 429、0 fallback** — 无任何异常信号
4. **per-key 全部健康** — 延迟分布在 11,836~14,327ms，均衡无劣化
5. **全部 pexec** — integrate 未启用，pexec 链路质量优秀
6. **本 tier 24h ATE=0** — 无 key 耗尽事件
7. **内部 RemoteDisconnected 被 key-cycling 全部优雅接管** — 未上升为请求级失败

## 上次修改效果 (R1121 → R1122)

R1121 报 30min SR=99.2% (127/128)。本次升至 **100% (155/155)**。2h 内 pexec_success 内部尝试 361 次，正常水平。系统在上一轮 key-0 代理故障自愈后继续保持满血运行。

## 下一步建议

- **保持观察**。系统健康，无需调整。
- 关注信号与预置对策:
  - 429 回升 → 增 `KEY_COOLDOWN_S` 30→60s
  - RemoteDisconnected/overloaded 频发 (≥30/h 且拉低请求级 SR) → 考虑降 `UPSTREAM_TIMEOUT` 50→35s 以加速 key 循环
  - 某 key 错误率 >10% → 从路由池移除
- 继续监控 key-0 代理 (SOCKS5 7897) 是否复发昨夜的故障，若复发优先考虑轮换其代理端口，而非参数改动。