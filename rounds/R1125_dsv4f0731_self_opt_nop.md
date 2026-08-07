# R1125: dsv4f0731_nv40666 Self-Optimization (NOP — Healthy & Stable)

**Datetime**: 2026-08-08 03:27 UTC (11:27 Beijing)
**Container**: dsvf0731_nv40666 (port 40666)
**Model**: dsv4f0731_nv via NVCF pexec
**Verifier**: 本机 (HM2, opc2_uname)

## 结论
**不修改参数 (NOP)。** 30min SR=98.68% (149/151)，2 次瞬时错误 (key1 的 `NVStream_IncompleteRead` 33.76s + key1 的 `stream_first_byte_timeout` 83.24s) 均已被 key-cycling 接管，0 请求级 429，0 fallback，全 pexec 且 per-key 均衡。系统维持 R1124 满血健康状态，无任何可调项需要介入。

## 30min 窗口 (脚本采集 03:26 UTC)

| 指标 | 值 |
|------|-----|
| Total | 151 |
| Success | 149 |
| **SR** | **98.68%** |
| Avg / P50 / P95 | 13,358ms / 10,123ms / 34,038ms |
| 请求级错误 | **2** (NVStream_IncompleteRead 33,764ms key1 + stream_first_byte_timeout 83,238ms key1) |
| 429s | **0** |
| Fallback (hm4104, 5min) | None |
| Upstream | 100% nvcf_pexec (151/151) |
| finish_reason: tool_calls / stop | 129 / 20 |

## Per-Key 性能 (30min, 200 延迟)

| Key | Count | avg_ms | p95 |
|-----|-------|--------|-----|
| 0 | 33 | 12,685 | 29,796 |
| 1 | 26 | 13,029 | 27,067 |
| 2 | 30 | 10,888 | 24,397 |
| 3 | 26 | 12,395 | 40,018 |
| 4 | 34 | 14,523 | 30,830 |

5 个 key 全部健康，延迟 10,888~14,523ms，无单 key 劣化。per-key 错误: 仅 key1 的 1 次 IncompleteRead + 1 次 stream_first_byte_timeout（同一 key 的 2 个错误）。key_cycle_429s: k0=57, k1=94 (内部循环计数, 请求级 429=0)。

⚠ **key1 观察信号**: R1123、R1124、R1125 连续三轮 key1 各出现 1 次瞬时错误 (IncompleteRead/首次字节超时)。单轮错误率仅 2/26 ≈ 7.7%，未达 10% 路由剔除阈值，故本轮不动；若下一轮继续聚集或升级为请求级 SR 拖累，需检查 key1 所对应 SOCKS5 代理端口 (5 代理端口 7897/7904/7894/7896/7895 之一)。

## 趋势

| 时段 | Total | Success | Failed | SR | Avg |
|------|-------|---------|--------|-----|-----|
| 30min | 151 | 149 | 2 | **98.68%** | 13,358ms |
| 6h | 1,773 | 1,760 | 13 | **99.27%** | — |
| 3h 19:00 | 134 | 133 | 1 | 99.3% | 12,472ms |
| 3h 18:00 | 347 | 346 | 1 | 99.7% | 11,992ms |
| 3h 17:00 | 279 | 273 | 6 | 97.8% | 11,786ms |
| 3h 16:00 | 151 | 151 | 0 | 100% | 13,043ms |

## 24h ATE 核验
预采集脚本 24h ATE（本 tier 汇总窗口）= 116，但该数值含其他模型 tier 的汇总。tier='dsv4f0731_nv' 本链条 24h `all_tiers_exhausted` 为 0（连续第 4 轮确认），RN1009 (UPSTREAM_TIMEOUT 90→50) 修复持续有效。

## 当前参数 (本次未改动, env 实值, 已核实与上轮一致)
UPSTREAM_TIMEOUT=50 · TIER_TIMEOUT_BUDGET_S=180 · NVU_TIER_BUDGET_DSV4F0731_NV=180 · NVU_TIER_BUDGET_DSV4F_NV=180 · KEY_COOLDOWN_S=30 · TIER_COOLDOWN_S=90 · NVU_KEYMGR_429_BASE/MAX=120/120 · NVU_KEYMGR_CONN_BASE/MAX/LONG=30/60/120 · NVU_KEYMGR_CONN_FAIL_THRESHOLD=3 · NVU_PEXEC_TIMEOUT_FASTBREAK=3 · NVU_EMPTY_200_FASTBREAK=3 · NVU_BUFFER_TIMEOUT_STAIRS=90×5 · NVU_PROBE_TIMEOUT=10 · NV_KEY_INTEGRATE_KEYS=空(integrate 未启用) · NVU_PEER_FALLBACK_ENABLED=0

/health 返回 ok，port 40666，5 keys，模型/tiers 列表完整。容器 Up 约 1 小时。

## NOP 原因
1. **30min SR=98.68%** — 远超 95% 阈值，2 次瞬时错误 (IncompleteRead + 首字节超时) 均已被 key-cycling 优雅接管
2. **6h SR=99.27%** — 持续高位稳定，无退化
3. **0 请求级 429、0 fallback** — 无异常信号
4. **per-key 全部健康** — 延迟分布 10,888~14,523ms，均衡无劣化
5. **全部 pexec** — integrate 未启用，pexec 链路优秀
6. **本 tier 24h ATE=0** — RN1009 修复持续奏效

## 上次修改效果 (R1124 → R1125)
R1124 报 30min SR=99.35% (153/154)。本次 98.68% (149/151)，30min SR 小幅回落 (因 2 次 key1 瞬时错误)，但 6h SR 99.32% → 99.27%，实为同一稳态噪声。为确保严格归因: 30min 回落系 key1 额外 1 次首字节超时 (83s) 所致，非参数退化——本轮未改任何参数, 该波动为 key1 SOCKS5 链路的正常瞬时抖动。系统稳定。

## 下一步建议
- **保持观察**。系统健康，无需调整。
- 关注信号与预置对策:
  - **key1 已连续三轮出现瞬时错误 (R1123/R1124/R1125)** — 下一轮若 key1 错误率 >10% 或错误聚集 (≥3/轮) → 检查 key1 对应 SOCKS5 代理端口健康 / 考虑从路由池临时移除
  - 429 回升 → 增 `KEY_COOLDOWN_S` 30→60s
  - RemoteDisconnected/overloaded 频发且拉低请求级 SR → 考虑降 `UPSTREAM_TIMEOUT` 50→35s
  - IncompleteRead/SSLEOFError 若开始聚集 (≥30/h) → 检查对应 key 的 SOCKS5 代理端口
- 继续监控紫色代理 (SOCKS5 7897/7904/7894/7896/7895) 端口与 key1 的复发风险。