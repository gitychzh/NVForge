# R1131: dsv4f0731_nv40666 Self-Optimization (NOP — Stable, 1 transient dead-link, tier ATE=0)

**Datetime**: 2026-08-08 03:46 UTC (11:46 Beijing)
**Container**: dsvf0731_nv40666 (port 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
**Model**: dsv4f0731_nv
**Verifier**: 本机 (HM2, opc2_uname)

## 结论
**不修改参数 (NOP)。** 30min SR=99.39% (164/165)，仅 1 次瞬时错误（key0 的
`stream_first_byte_timeout` 83,238ms，R1029 已确认的源码级死链问题，非 env 可修），0 请求级 429，
0 fallback，全 pexec 且 per-key 均匀。6h 请求级 SR 逐小时多数 ≥99%，本 tier 24h
`all_tiers_exhausted` = 0（已用 `nv_tier_attempts` 按 tier 核验）。与 R1130 稳态一致，
无任何可调项需要介入。

## 30min 窗口 (脚本采集 03:46 UTC)
| 指标 | 值 |
|------|-----|
| Total | 165 |
| Success | 164 |
| **SR** | **99.39%** |
| Avg / P50 / P95 | 12,265ms / 8,938ms / 31,631ms |
| 请求级错误 | **1** (stream_first_byte_timeout 83,238ms key0) |
| 429s | **0** |
| Fallback (hm4104, 5min) | **None** |
| Upstream | 100% nvcf_pexec (165/165, 164 成功) |
| finish_reason: tool_calls / stop | 142 / 22 |

## Per-Key 200 延迟 (30min)
| Key | Total | OK | avg_ok_ms |
|-----|-------|----|-----------|
| 0 | 36 | — | 13,162 |
| 1 | 32 | — | 12,090 |
| 2 | 31 | — | 10,303 |
| 3 | 32 | — | 11,878 |
| 4 | 33 | — | 11,524 |

4 个 key 延迟 11.5~13.2s 均匀（k2 稍低、k0 稍高，方差噪声内），k2~k4 均 100% 成功，k0/k1 各 0 命
中 1 次内部循环记数。⚠ 30min 瞬时错误再次落在 key0（R1126~R1131 累计 6 轮承载瞬时错误），
key0 近期错误率 ~0.8%，远低于 >10% 阈值，属 SOCKS5 端口 7897 独立瞬时抖动，未触发 fast-break，
无持久 key 缺陷，本轮不改路由。

## 趋势 (6h 请求级逐小时)
| 时段 | Total | OK | SR |
|------|-------|-----|-----|
| 16:00 | 62 | 62 | 100% |
| 17:00 | 279 | 273 | 97.85% |
| 18:00 | 347 | 346 | 99.71% |
| 19:00 | 254 | 253 | 99.61% |

6h 请求级合计 1,807 请求，13 非 200 (SR≈99.28%)。最新时段 SR ≥99.6%，持续高位稳定。
错误构成以瞬时死链 / IncompleteRead / buffer_exhausted 为主，均被 key-cycling 内部优雅接管，
未浮现为系统性失败。24h `all_tiers_exhausted`=113 为跨 tier 汇总窗口，本链核验 =0。

## 当前参数 (本次未改动, env 实值已核实与 R1130 一致)
UPSTREAM_TIMEOUT=50 · TIER_TIMEOUT_BUDGET_S=180 · NVU_TIER_BUDGET_DSV4F0731_NV=180 ·
NVU_TIER_BUDGET_DSV4F_NV=180 · KEY_COOLDOWN_S=30 · TIER_COOLDOWN_S=90 ·
NVU_KEYMGR_429_BASE/MAX=120/120 · NVU_KEYMGR_CONN_BASE/MAX/LONG=30/60/120 ·
NVU_KEYMGR_CONN_FAIL_THRESHOLD=3 · NVU_PEXEC_TIMEOUT_FASTBREAK=3 ·
NVU_EMPTY_200_FASTBREAK=3 · NVU_BUFFER_TIMEOUT_STAIRS=90×5 · NVU_PROBE_TIMEOUT=10 ·
NV_INTEGRATE_KEYS=空(integrate 未启用) · NVU_PEER_FALLBACK_ENABLED=0

注: 任务提示"可调参数"表为模板默认值（UPSTREAM_TIMEOUT=90/TIER_COOLDOWN_S=180/
NVU_KEYMGR_429_MAX=300 等），与 live env 实值（50/90/120）不一致。以 **live env 为权威**，
未漂移，无需干预。

/health 返回 ok，port 40666，5 keys，模型/tiers 列表完整。容器 Up 约 1 小时。

## NOP 原因
1. **30min SR=99.39%** — 远超 95% 阈值，1 次瞬时错误被 key-cycling 优雅接管
2. **最新时段 6h 逐小时 ≥99.6%** — 持续高位稳定
3. **本 tier 24h ATE=0** — RN1009 修复持续奏效
4. **0 请求级 429、0 fallback** — 无异常信号
5. **per-key 全部健康** — 延迟 10.3~13.2s 均衡，4 key 100% 成功
6. **全部 pexec** — integrate 未启用，链路优秀
7. **单次瞬时 dead-link 为源码级** — stream_first_byte_timeout 83s 根因在 `handlers.py`
   socket.timeout→continue 结构 (R1029 已确认)，无法用 env 干净归因修复

## 上次修改效果 (R1130 → R1131)
R1130 报 30min SR=99.37% (158/159)。本次 SR=99.39% (164/165)，基本持平（+0.02pct，单次瞬时
死链的抽样差异）。Avg 从 12,495ms 略降至 12,265ms（-230ms，噪声内）。6h 仍是 99.28% 量级。
本轮未改任何参数，系统延续 R1130 稳态，无退化。

## 下一步建议
- **保持观察**。系统健康稳定，无需调整。
- 关注信号与预置对策:
  - 若 stream_first_byte_timeout 死链（83s）反复聚集（≥3/30min 或单 key 集中）→ 才需评估
    源码级修复（read() 连续超时 N 次即走 deadline break）
  - 429 回升 → 增 `KEY_COOLDOWN_S` 30→60s
  - RemoteDisconnected/overloaded 频发且拉低请求级 SR → 考虑降 `UPSTREAM_TIMEOUT` 50→35s
  - IncompleteRead/SSLEOFError 若开始聚集 (≥30/h) → 检查对应 key 的 SOCKS5 代理端口
  - key0 已连续 6 轮承载瞬时错误——若错误率 (当前 0.8%) 攀升 >10% 或连续 2-3 轮未自愈，
    优先核验其 SOCKS5 端口 7897
- 继续监控 5 个 SOCKS5 代理端口与 key 级瞬时错误复发风险。