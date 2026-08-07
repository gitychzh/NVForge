# R1124: dsv4f0731_nv40666 Self-Optimization (NOP — Healthy & Stable)

**Datetime**: 2026-08-08 03:15 UTC (11:15 Beijing)
**Container**: dsvf0731_nv40666 (port 40666)
**Model**: dsv4f0731_nv via NVCF pexec
**Verifier**: 本机 (HM2, opc2_uname)

## 结论
**不修改参数 (NOP)。** 30min SR=99.35% (153/154)，仅 1 次瞬时 `NVStream_IncompleteRead`(key1, 33.7s) 已被 key-cycling 优雅接管，0 请求级 429，0 ATE，0 fallback，全 pexec 且 per-key 均衡。系统保持 RN1009 调优后的满血健康状态，与 R1123 持平，无任何可调项需要介入。

## 30min 窗口 (脚本采集 03:14 UTC)

| 指标 | 值 |
|------|-----|
| Total | 154 |
| Success | 153 |
| **SR** | **99.35%** |
| Avg / P50 / P95(P99) | 13,277ms / 10,481ms / 33,956ms(46,181ms) |
| 请求级错误 | **1** (NVStream_IncompleteRead, 33,764ms, key1) |
| 429s | **0** |
| Fallback (hm4104, 5min) | None |
| Upstream | 100% nvcf_pexec (154/154) |
| finish_reason: tool_calls / stop | 134 / 19 |

## Per-Key 性能 (30min, 200 延迟)

| Key | Count | avg_ms | p95 |
|-----|-------|--------|-----|
| 0 | 32 | 12,444 | 23,110 |
| 1 | 29 | 12,692 | 28,766 |
| 2 | 32 | 13,090 | 26,774 |
| 3 | 30 | 12,997 | 39,990 |
| 4 | 30 | 14,528 | 34,670 |

5 个 key 全部健康，延迟 12,444~14,528ms，无单 key 劣化。per-key 错误: 仅 key1 的 1 次 IncompleteRead。key_cycle_429s: k0=59, k1=95 (内部循环计数, 请求级 429=0)。

## 趋势

| 时段 | Total | Success | Failed | SR | Avg |
|------|-------|---------|--------|-----|-----|
| 30min | 154 | 153 | 1 | **99.35%** | 13,277ms |
| 6h | 1,754 | 1,742 | 12 | **99.32%** | — |
| 3h 19:00 | 72 | 72 | 0 | 100% | 12,358ms |
| 3h 18:00 | 347 | 346 | 1 | 99.7% | 11,992ms |
| 3h 17:00 | 279 | 273 | 6 | 97.8% | 11,786ms |
| 3h 16:00 | 212 | 212 | 0 | 100% | 12,807ms |

## 24h ATE 核验
预采集脚本 24h ATE（本 tier 汇总窗口）= 118，但该数值含其他模型 tier 的汇总。tier='dsv4f0731_nv' 本链条 24h `all_tiers_exhausted` 为 0（连续第 3 轮确认），RN1009 (UPSTREAM_TIMEOUT 90→50) 修复持续有效。

## 当前参数 (本次未改动, env 实值, 已核实与上轮一致)
UPSTREAM_TIMEOUT=50 · TIER_TIMEOUT_BUDGET_S=180 · NVU_TIER_BUDGET_DSV4F0731_NV=180 · NVU_TIER_BUDGET_DSV4F_NV=180 · KEY_COOLDOWN_S=30 · TIER_COOLDOWN_S=90 · NVU_KEYMGR_429_BASE/MAX=120/120 · NVU_KEYMGR_CONN_BASE/MAX/LONG=30/60/120 · NVU_KEYMGR_CONN_FAIL_THRESHOLD=3 · NVU_PEXEC_TIMEOUT_FASTBREAK=3 · NVU_EMPTY_200_FASTBREAK=3 · NVU_BUFFER_TIMEOUT_STAIRS=90×5 · NVU_PROBE_TIMEOUT=10 · NV_KEY_INTEGRATE_KEYS=空(integrate 未启用) · NVU_PEER_FALLBACK_ENABLED=0

/health 返回 ok，port 40666，5 keys，模型/tiers 列表完整。容器 Up 55 分钟。

## NOP 原因
1. **30min SR=99.35%** — 远超 95% 阈值，唯一 IncompleteRead 为瞬时流断且已被 key-cycling 接管
2. **6h SR=99.32%** — 持续高位稳定，无退化
3. **0 请求级 429、0 ATE、0 fallback** — 无任何异常信号
4. **per-key 全部健康** — 延迟分布 12,444~14,528ms，均衡无劣化
5. **全部 pexec** — integrate 未启用，pexec 链路优秀
6. **本 tier 24h ATE=0** — RN1009 修复持续奏效

## 上次修改效果 (R1123 → R1124)
R1123 报 30min SR=99.3% (150/151)。本次 99.35% (153/154)，基本持平。6h SR 99.35% → 99.32%，微幅波动属正常。系统稳定，无退化。

## 下一步建议
- **保持观察**。系统健康，无需调整。
- 关注信号与预置对策:
  - 429 回升 → 增 `KEY_COOLDOWN_S` 30→60s
  - RemoteDisconnected/overloaded 频发且拉低请求级 SR → 考虑降 `UPSTREAM_TIMEOUT` 50→35s
  - 单 key 错误率 >10% → 从路由池移除 (注意 key1 已连续两轮出现单次 IncompleteRead，若聚集需检查其 SOCKS5 代理端口)
  - IncompleteRead/SSLEOFError 若开始聚集 (≥30/h) → 检查对应 key 的 SOCKS5 代理端口健康
- 继续监控紫色代理 (SOCKS5 7894/7896/7895/7897/7904) 端口与 key-0/key-1 的复发风险。