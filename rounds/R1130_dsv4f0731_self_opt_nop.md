# R1130: dsv4f0731_nv40666 Self-Optimization (NOP — Stable, 1 transient dead-link, tier ATE=0)

**Datetime**: 2026-08-08 03:45 UTC (11:45 Beijing)
**Container**: dsvf0731_nv40666 (port 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
**Model**: dsv4f0731_nv
**Verifier**: 本机 (HM2, opc2_uname)

## 结论
**不修改参数 (NOP)。** 30min SR=99.37% (158/159)，仅 1 次瞬时错误（key0 的
`stream_first_byte_timeout` 83,238ms，R1029 已确认的源码级死链问题，非 env 可修），0 请求级 429，
0 fallback，全 pexec 且 per-key 均匀。6h 请求级 SR 逐小时 96.3%~99.66%（多数 ≥99%），持续高位。
本 tier 24h `all_tiers_exhausted` = 0。与 R1129 稳态一致，无任何可调项需要介入。

## 30min 窗口 (脚本采集 03:42 UTC)
| 指标 | 值 |
|------|-----|
| Total | 159 |
| Success | 158 |
| **SR** | **99.37%** |
| Avg / P50 / P95 / P99 | 12,495ms / 9,221ms / 31,796ms / 39,667ms |
| 请求级错误 | **1** (stream_first_byte_timeout 83,238ms key0) |
| 429s | **0** |
| Fallback (hm4104, 5min) | **None** |
| Upstream | 100% nvcf_pexec (159/159, 158 成功) |
| finish_reason: tool_calls / stop | 136 / 22 |

## Per-Key 性能 (近 2h 请求级, 已验证均健全)
| Key | Total | OK | SR | avg_ok_ms |
|-----|-------|----|-----|-----------|
| 0 | 132 | 131 | 99.2% | 11,377 |
| 1 | 128 | 127 | 99.2% | 11,636 |
| 2 | 129 | 129 | 100% | 11,299 |
| 3 | 132 | 132 | 100% | 12,186 |
| 4 | 123 | 123 | 100% | 11,395 |

5 个 key 全部健康，SR ≥99.2%，延迟 11.3~12.2s 高度均匀，无单 key 劣化。30min per-key 200 延迟
(0-4): 12,676 / 12,381 / 10,893 / 11,530 / 12,584ms。key_cycle_429s: k0=59, k1=100 (内部循环记数,
请求级 429=0)。

⚠ 30min 瞬时错误再次落在 key0（R1126~R1129 连续 5 轮均在 key0，6h 内 RemoteDisconnected 亦分散于
5 个 key 8/6/3/4/8）。key0 近期错误率为 ~0.8% (1/132)，远低于 >10% 阈值，属 SOCKS5 端口 7897 的
独立瞬时抖动，未触发 fast-break，无持久 key 缺陷，本轮不改路由。

## 趋势 (6h 请求级逐小时)
| 时段 | Total | OK | SR |
|------|-------|-----|-----|
| 13:00 | 81 | 78 | 96.30% |
| 14:00 | 294 | 293 | 99.66% |
| 15:00 | 292 | 291 | 99.66% |
| 16:00 | 274 | 273 | 99.64% |
| 17:00 | 280 | 273 | 97.50% |
| 18:00 | 349 | 346 | 99.14% |
| 19:00 | 237 | 236 | 99.58% |

6h 请求级合计 1,792 请求，13 非 200 (SR≈99.27%)。错误构成（tier_attempts 层另有 RemoteDisconnected
29 次但被 key-cycling 内部接管，未全部浮现为请求失败）：请求级非 200 主要为
`all_tiers_exhausted=5`、`zombie_empty_completion=5`、`buffer_exhausted=4`、`NVStream_IncompleteRead=2`、
`stream_first_byte_timeout=1`。最新 90min 请求级错误仅 buffer_exhausted=2 / IncompleteRead=1 /
stream_first_byte_timeout=1——近端已显著收敛，13:00 的 96.3% 为早期噪声。

## 24h ATE 核验
预采集脚本 24h ATE=113 为本 tier 汇总窗口（含其他模型 tier 汇总）。已用 `nv_tier_attempts` 按
`tier='dsv4f0731_nv'` 核验：**本链条 24h `all_tiers_exhausted` = 0**（RN1009 UPSTREAM_TIMEOUT 90→50
修复持续奏效）。

## 当前参数 (本次未改动, env 实值已核实与 R1129 一致)
UPSTREAM_TIMEOUT=50 · TIER_TIMEOUT_BUDGET_S=180 · NVU_TIER_BUDGET_DSV4F0731_NV=180 ·
NVU_TIER_BUDGET_DSV4F_NV=180 · KEY_COOLDOWN_S=30 · TIER_COOLDOWN_S=90 · NVU_KEYMGR_429_BASE/MAX=120/120 ·
NVU_KEYMGR_CONN_BASE/MAX/LONG=30/60/120 · NVU_KEYMGR_CONN_FAIL_THRESHOLD=3 ·
NVU_PEXEC_TIMEOUT_FASTBREAK=3 · NVU_EMPTY_200_FASTBREAK=3 · NVU_BUFFER_TIMEOUT_STAIRS=90×5 ·
NVU_PROBE_TIMEOUT=10 · NV_INTEGRATE_KEYS=空(integrate 未启用) · NVU_PEER_FALLBACK_ENABLED=0

注: 任务提示中的"可调参数"表列为模板默认值（UPSTREAM_TIMEOUT=90 / TIER_COOLDOWN_S=180 /
NVU_KEYMGR_429_MAX=300 / NV_KEY_INTEGRATE_KEYS=dsv4f0731_nv:3），与容器 live env 实值不一致
（实为 50 / 90 / 120 / 空）。以 **live env 为权威**，已核实 R1129 设定未漂移，无需干预。

/health 返回 ok，port 40666，5 keys，模型/tiers 列表完整。容器 Up 约 1 小时。

## NOP 原因
1. **30min SR=99.37%** — 远超 95% 阈值，1 次瞬时错误已被 key-cycling 优雅接管
2. **6h 请求级逐小时多数 ≥99%** — 持续高位稳定，最新 90min 仅有 4 次轻微错误
3. **本 tier 24h ATE=0** — RN1009 修复持续奏效
4. **0 请求级 429、0 fallback** — 无异常信号
5. **per-key 全部健康** — 5 key 近 2h SR ≥99.2%，延迟 11.3~12.2s 均衡无劣化
6. **全部 pexec** — integrate 未启用，pexec 链路优秀
7. **单次瞬时 dead-link 为源码级** — stream_first_byte_timeout 83s 根因在 `handlers.py`
   注释的 socket.timeout→continue 结构 (R1029 已确认)，无法用 env 干净归因修复，本轮不改

## 上次修改效果 (R1129 → R1130)
R1129 报 30min SR=99.40% (167/168)。本次 SR=99.37% (158/159)，基本持平（-0.03pct，仅 1 次瞬时
死链的抽样差异）。Avg 从 12,472ms 微升至 12,495ms（+23ms，噪声内）。6h 仍是 99.27% 量级。本轮未改
任何参数，系统延续 R1129 稳态，无退化。

## 下一步建议
- **保持观察**。系统健康稳定，无需调整。
- 关注信号与预置对策:
  - 若 stream_first_byte_timeout 死链（83s）反复出现且聚集（≥3/30min 或单 key 集中）→ 才需
    评估源码级修复（让 read() 连续超时 N 次即走 deadline break，替代 continue 到底层 ~66s timeout）
  - 429 回升 → 增 `KEY_COOLDOWN_S` 30→60s
  - RemoteDisconnected/overloaded 频发且拉低请求级 SR → 考虑降 `UPSTREAM_TIMEOUT` 50→35s
  - IncompleteRead/SSLEOFError 若开始聚集 (≥30/h) → 检查对应 key 的 SOCKS5 代理端口
  - key0 已连续 5 轮承载瞬时错误——若错误率 (当前 0.8%) 攀升 >10% 或连续 2-3 轮未自愈，
    优先核验其 SOCKS5 端口 7897
- 继续监控 5 个 SOCKS5 代理端口与 key 级瞬时错误复发风险。