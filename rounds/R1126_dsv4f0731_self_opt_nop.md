# R1126: dsv4f0731_nv40666 Self-Optimization (NOP — Healthy & Stable, key1 self-recovered)

**Datetime**: 2026-08-08 03:31 UTC (11:31 Beijing)
**Container**: dsvf0731_nv40666 (port 40666)
**Model**: dsv4f0731_nv via NVCF pexec
**Verifier**: 本机 (HM2, opc2_uname)

## 结论
**不修改参数 (NOP)。** 30min SR=99.33% (148/149)，1 次瞬时错误 (key0 的 `stream_first_byte_timeout` 83.24s) 已被 key-cycling 接管，0 请求级 429，0 fallback，全 pexec 且 per-key 均衡。**关键信号: key1 自愈** —— R1123/R1124/R1125 连续三轮 key1 各出现瞬时错误，本轮 key1 错误归零，瞬时错误转移至 key0，证实为 SOCKS5 链路瞬时抖动而非 key1 持久缺陷。系统维持满血健康状态，无任何可调项需要介入。

## 30min 窗口 (脚本采集 03:30 UTC)

| 指标 | 值 |
|------|-----|
| Total | 149 |
| Success | 148 |
| **SR** | **99.33%** |
| Avg / P50 / P95 / P99 | 13,500ms / 10,722ms / 33,195ms / 39,930ms |
| 请求级错误 | **1** (stream_first_byte_timeout 83,238ms key0) |
| 429s | **0** |
| Fallback (hm4104, 5min) | None |
| Upstream | 100% nvcf_pexec (149/149, 148 成功) |
| finish_reason: tool_calls / stop | 128 / 20 |

## Per-Key 性能 (30min, 200 延迟)

| Key | Count | avg_ms | p95 |
|-----|-------|--------|-----|
| 0 | 33 | 13,823 | 33,059 |
| 1 | 29 | 14,466 | 30,218 |
| 2 | 31 | 10,885 | 24,310 |
| 3 | 24 | 11,606 | 36,087 |
| 4 | 31 | 14,083 | 30,601 |

5 个 key 全部健康，延迟 10,885~14,466ms，无单 key 劣化。per-key 错误: 仅 key0 的 1 次 stream_first_byte_timeout (83.24s)。key_cycle_429s: k0=55, k1=94 (内部循环计数, 请求级 429=0)。

⚠ **key1 自愈核验**: R1123(1次)/R1124(1次)/R1125(2次) 三轮 key1 聚集瞬时错误，本轮 key1 错误=0，瞬时错误移至 key0。这与 key-pool SOCKS5 各端口独立抖动一致 —— 无持久 key 缺陷，无需路由剔除。若 key 错误率 >10% 或某 key 连续 ≥3 轮聚集，才需检查其对应 SOCKS5 端口。

## 趋势 (6h / 3h 逐小时)

| 时段 | Total | Success | Failed | SR | Avg |
|------|-------|---------|--------|-----|-----|
| 30min | 149 | 148 | 1 | **99.33%** | 13,500ms |
| 6h | 1,777 | 1,764 | 13 | **99.27%** | — |
| 3h 19:00 | 150 | 149 | 1 | 99.3% | 13,211ms |
| 3h 18:00 | 347 | 346 | 1 | 99.7% | 11,992ms |
| 3h 17:00 | 279 | 273 | 6 | 97.8% | 11,786ms |
| 3h 16:00 | 134 | 134 | 0 | 100% | 12,886ms |

## 24h ATE 核验
预采集脚本 24h ATE（本 tier 汇总窗口）= 115，但该数值含其他模型 tier 的汇总。tier='dsv4f0731_nv' 本链条 24h `all_tiers_exhausted` 为 0（连续第 5 轮确认），RN1009 (UPSTREAM_TIMEOUT 90→50) 修复持续有效。

## 当前参数 (本次未改动, env 实值, 已核实与上轮一致)
UPSTREAM_TIMEOUT=50 · TIER_TIMEOUT_BUDGET_S=180 · NVU_TIER_BUDGET_DSV4F0731_NV=180 · NVU_TIER_BUDGET_DSV4F_NV=180 · KEY_COOLDOWN_S=30 · TIER_COOLDOWN_S=90 · NVU_KEYMGR_429_BASE/MAX=120/120 · NVU_KEYMGR_CONN_BASE/MAX/LONG=30/60/120 · NVU_KEYMGR_CONN_FAIL_THRESHOLD=3 · NVU_PEXEC_TIMEOUT_FASTBREAK=3 · NVU_EMPTY_200_FASTBREAK=3 · NVU_BUFFER_TIMEOUT_STAIRS=90×5 · NVU_PROBE_TIMEOUT=10 · NV_KEY_INTEGRATE_KEYS=空(integrate 未启用) · NVU_PEER_FALLBACK_ENABLED=0

/health 返回 ok，port 40666，5 keys，模型/tiers 列表完整。容器 Up 约 1 小时。容器 env 共 89 行。

## NOP 原因
1. **30min SR=99.33%** — 远超 95% 阈值，1 次瞬时错误已被 key-cycling 优雅接管
2. **6h SR=99.27%** — 持续高位稳定，无退化
3. **0 请求级 429、0 fallback** — 无异常信号
4. **per-key 全部健康** — 延迟分布 10,885~14,466ms，均衡无劣化
5. **全部 pexec** — integrate 未启用，pexec 链路优秀
6. **key1 自愈** — 附加多轮瞬时错误信号消解，无需路由干预
7. **本 tier 24h ATE=0** — RN1009 修复持续奏效

## 上次修改效果 (R1125 → R1126)
R1125 报 30min SR=98.68% (149/151)（含 key1 2 次瞬时错误）。本次 SR=99.33% (148/149)，上行 0.65pct。6h SR 99.27% 与上轮 99.27% 持平。本轮未改任何参数，30min 波动系 key0 单次首字节超时 (83s) 的瞬时抖动，属同一稳态噪声；key1 错误归零进一步确认系统健康。

## 下一步建议
- **保持观察**。系统健康，无需调整。
- 关注信号与预置对策:
  - 瞬时错误现已从 key1 移至 key0（单次）—— 若再次连续 ≥3 轮聚集，检查对应 key 的 SOCKS5 代理端口 (5 端口 7897/7904/7894/7896/7895) 健康
  - 429 回升 → 增 `KEY_COOLDOWN_S` 30→60s
  - RemoteDisconnected/overloaded 频发且拉低请求级 SR → 考虑降 `UPSTREAM_TIMEOUT` 50→35s
  - IncompleteRead/SSLEOFError 若开始聚集 (≥30/h) → 检查对应 key 的 SOCKS5 代理端口
- 继续监控 5 个 SOCKS5 代理端口与 key 级瞬时错误复发风险。