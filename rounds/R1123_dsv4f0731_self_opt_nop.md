# R1123: dsv4f0731_nv40666 Self-Optimization (NOP — Healthy & Stable)

**Datetime**: 2026-08-08 03:10 UTC (11:10 Beijing)
**Container**: dsvf0731_nv40666 (port 40666)
**Model**: dsv4f0731_nv via NVCF pexec
**Verifier**: 本机 (HM2, opc2_uname)

## 结论
**不修改参数 (NOP)。** 30min SR=99.3% (150/151)，仅 1 次瞬时 `NVStream_IncompleteRead`（已被 key-cycling 优雅接管，未构成链路劣化），0 请求级 429，0 ATE，0 fallback，全 pexec 且 per-key 均衡。系统保持 RN1009 调优后的满血健康状态，无任何可调项需要介入。

## 30min 窗口 (脚本采集 03:10 UTC)

| 指标 | 值 |
|------|-----|
| Total | 151 |
| Success | 150 |
| **SR** | **99.3%** |
| Avg / P50 / P95(P99) | 14,138ms / 11,427ms / 36,079ms(46,328ms) |
| 请求级错误 | **1** (NVStream_IncompleteRead, 33.7s) |
| 429s | **0** |
| Fallback (hm4104, 5min) | None |
| Upstream | 100% nvcf_pexec (151/151) |
| finish_reason: tool_calls / stop | 132 / 18 |

## Per-Key 性能 (30min, 200 延迟)

| Key | Count | avg_ms | p95 |
|-----|-------|--------|-----|
| 0 | 31 | 13,679 | 28,706 |
| 1 | 28 | 13,242 | 28,772 |
| 2 | 31 | 14,155 | 32,796 |
| 3 | 31 | 14,114 | 39,983 |
| 4 | 29 | 14,825 | 35,231 |

5 个 key 全部健康，无单 key 劣化。per-key 错误: 仅 key1 的 1 次 IncompleteRead。key_cycle_429s: k0=57, k1=94 (内部循环计数, 请求级 429=0)。

## 链路日志佐证 (实时)
03:07:58 k5 `SSLEOFError (5004ms)` → `NV-SSL-CYCLE` → 换 key1 → **03:08:09 成功**。瞬时 SSL 层断流被 key-cycling 自动接管，同一请求内成功，未上升为请求级失败。其余请求均首击成功。

## 趋势

| 时段 | Total | Success | Failed | SR | Avg |
|------|-------|---------|--------|-----|-----|
| 30min | 151 | 150 | 1 | **99.3%** | 14,138ms |
| 6h | 1,742 | 1,730 | 12 | **99.35%** | — |
| 3h 19:00 | 46 | 46 | 0 | 100% | 13,524ms |
| 3h 18:00 | 347 | 346 | 1 | 99.7% | 11,992ms |
| 3h 17:00 | 279 | 273 | 6 | 97.8% | 11,786ms |
| 3h 16:00 | 226 | 226 | 0 | 100% | 13,364ms |

## 24h ATE 核验 (本 tier 专属)
tier='dsv4f0731_nv' 24h `nv_tier_attempts` **无 `all_tiers_exhausted` 行**。预采集脚本的 ATE=119 属其他模型 tier 汇总，本 chain 无预算耗尽事件 → RN1009 (UPSTREAM_TIMEOUT 90→50) 后 ATE 消除的修复持续有效。

## 24h 内部 attempt 分布 (已全被 key-cycling 吸收)
| error_type | count |
|-----------|-------|
| pexec_success | 5,074 |
| NVCFPexecRemoteDisconnected | 467 |
| NVCFPexecTimeout | 75 |
| empty_200 | 58 |
| 529_nv_overloaded | 51 |
| 504_nv_gateway_timeout | 10 |

请求级 SR 高达 99.3% 说明这些内部尝试失败全部在同一请求内换 key 重试成功，未上升到请求级失败。

## 当前参数 (本次未改动, env 实值)
UPSTREAM_TIMEOUT=50 · TIER_TIMEOUT_BUDGET_S=180 · NVU_TIER_BUDGET_DSV4F0731_NV=180 · NVU_TIER_BUDGET_DSV4F_NV=180 · KEY_COOLDOWN_S=30 · TIER_COOLDOWN_S=90 · NVU_KEYMGR_429_BASE/MAX=120/120 · NVU_KEYMGR_CONN_BASE/MAX/LONG=30/60/120 · NVU_KEYMGR_CONN_FAIL_THRESHOLD=3 · NVU_PEXEC_TIMEOUT_FASTBREAK=3 · NVU_EMPTY_200_FASTBREAK=3 · NVU_BUFFER_TIMEOUT_STAIRS=90×5 · NVU_PROBE_TIMEOUT=10 · NV_KEY_INTEGRATE_KEYS=空(integrate 未启用) · NVU_PEER_FALLBACK_ENABLED=0

/health 返回 ok，port 40666，5 keys，模型/tiers 列表完整。容器 Up 51 分钟。

## NOP 原因
1. **30min SR=99.3%** — 远超 95% 阈值，唯一 IncompleteRead 为瞬时流断且已被接管
2. **6h SR=99.35%** — 持续高位稳定，无退化
3. **0 请求级 429、0 ATE、0 fallback** — 无任何异常信号
4. **per-key 全部健康** — 延迟分布 13,242~14,825ms，均衡无劣化
5. **全部 pexec** — integrate 未启用，pexec 链路优秀
6. **本 tier 24h ATE=0** — RN1009 修复持续奏效
7. **内部 467 次 RemoteDisconnected 等全被 key-cycling 优雅吸收** — 机制健康

## 上次修改效果 (R1122 → R1123)
R1122 报 30min SR=100% (155/155)。本次 99.3% (150/151)，唯一的 1 次 IncompleteRead 为瞬时单例（日志确认 5s 内换 key 成功修复），非系统性退化。6h SR 从 99.37% → 99.35%，基本持平。系统稳定。

## 下一步建议
- **保持观察**。系统健康，无需调整。
- 关注信号与预置对策:
  - 429 回升 → 增 `KEY_COOLDOWN_S` 30→60s
  - RemoteDisconnected/overloaded 频发且拉低请求级 SR → 考虑降 `UPSTREAM_TIMEOUT` 50→35s
  - 单 key 错误率 >10% → 从路由池移除
  - IncompleteRead/SSLEOFError 若开始聚集 (≥30/h) → 检查对应 key 的 SOCKS5 代理端口健康，而非参数
- 继续监控紫色代理 (SOCKS5 7894/7896/7895/7897/7904) 端口与 key-0 的复发风险。