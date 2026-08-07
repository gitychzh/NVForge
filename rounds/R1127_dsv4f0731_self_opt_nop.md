# R1127: dsv4f0731_nv40666 Self-Optimization (NOP — Stable, 1 transient dead-link, tier ATE=0)

**Datetime**: 2026-08-08 03:34 UTC (11:34 Beijing)
**Container**: dsvf0731_nv40666 (port 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
**Model**: dsv4f0731_nv
**Verifier**: 本机 (HM2, opc2_uname)

## 结论
**不修改参数 (NOP)。** 30min SR=99.34% (151/152)，仅 1 次瞬时错误（key0 的
`stream_first_byte_timeout` 83.2s，R1029 已确认的源码级死链问题，非 env 可修），0 请求级 429，
0 fallback，全 pexec 且 per-key 均匀。6h SR=99.27% 持续高位。系统健康稳定，无任何可调项需要介入。

## 30min 窗口 (脚本采集 03:34 UTC)

| 指标 | 值 |
|------|-----|
| Total | 152 |
| Success | 151 |
| **SR** | **99.34%** |
| Avg / P50 / P95 / P99 | 13,582ms / 10,093ms / 33,803ms / 39,922ms |
| 请求级错误 | **1** (stream_first_byte_timeout 83,238ms key0) |
| 429s | **0** |
| Fallback (hm4104, 5min) | **None** |
| Upstream | 100% nvcf_pexec (152/152, 151 成功) |
| finish_reason: tool_calls / stop | 130 / 21 |

## Per-Key 性能 (30min, 200 延迟)

| Key | Count | avg_ms | max_ms |
|-----|-------|--------|--------|
| 0 | 34 | 13,768 | 32,954 |
| 1 | 28 | 13,622 | 29,991 |
| 2 | 29 | 11,543 | 24,484 |
| 3 | 28 | 12,741 | 35,773 |
| 4 | 32 | 13,758 | 30,145 |

5 个 key 全部健康，延迟 11,543~13,768ms 高度均匀，无单 key 劣化。per-key 错误: 仅 key0 的 1 次
stream_first_byte_timeout (83.24s)。key_cycle_429s: k0=52, k1=100 (内部循环记数, 请求级 429=0)。

⚠ 瞬时错误本轮落在 key0（上一轮 R1126 也在 key0）。R1123~R1125 曾连续三轮聚集在 key1，后 key1 自愈。
这与 key-pool SOCKS5 各端口独立抖动一致——无持久 key 缺陷，无需路由剔除。若某 key 错误率 >10% 或
连续 ≥3 轮聚集，才需检查其对应 SOCKS5 端口。

## 趋势 (6h / 3h 逐小时)

| 时段 | Total | Success | Failed | SR | Avg |
|------|-------|---------|--------|-----|-----|
| 30min | 152 | 151 | 1 | **99.34%** | 13,582ms |
| 6h | 1,777 | 1,764 | 13 | **99.27%** | — |
| 3h 19:00 | 174 | 173 | 1 | 99.4% | 12,960ms |
| 3h 18:00 | 347 | 346 | 1 | 99.7% | 11,992ms |
| 3h 17:00 | 279 | 273 | 6 | 97.8% | 11,786ms |
| 3h 16:00 | 116 | 116 | 0 | 100% | 13,028ms |

## 24h ATE 核验
预采集脚本 24h ATE（本 tier 汇总窗口）= 115，但该数值含其他模型 tier 汇总。tier='dsv4f0731_nv'
本链条 24h `all_tiers_exhausted` 为 0（连续第 6 轮确认），RN1009 (UPSTREAM_TIMEOUT 90→50)
修复持续有效。

## 当前参数 (本次未改动, env 实值已核实与 R1126 一致)
UPSTREAM_TIMEOUT=50 · TIER_TIMEOUT_BUDGET_S=180 · NVU_TIER_BUDGET_DSV4F0731_NV=180 ·
NVU_TIER_BUDGET_DSV4F_NV=180 · KEY_COOLDOWN_S=30 · TIER_COOLDOWN_S=90 · NVU_KEYMGR_429_BASE/MAX=120/120 ·
NVU_KEYMGR_CONN_BASE/MAX/LONG=30/60/120 · NVU_KEYMGR_CONN_FAIL_THRESHOLD=3 ·
NVU_PEXEC_TIMEOUT_FASTBREAK=3 · NVU_EMPTY_200_FASTBREAK=3 · NVU_BUFFER_TIMEOUT_STAIRS=90×5 ·
NVU_PROBE_TIMEOUT=10 · NV_KEY_INTEGRATE_KEYS=空(integrate 未启用) · NVU_PEER_FALLBACK_ENABLED=0

/health 返回 ok，port 40666，5 keys，模型/tiers 列表完整。容器 Up 约 1 小时。

## NOP 原因
1. **30min SR=99.34%** — 远超 95% 阈值，1 次瞬时错误已被 key-cycling 优雅接管
2. **6h SR=99.27%** — 持续高位稳定，无退化
3. **0 请求级 429、0 fallback** — 无异常信号
4. **per-key 全部健康** — 延迟分布 11.5~13.8s，均衡无劣化
5. **全部 pexec** — integrate 未启用，pexec 链路优秀
6. **单次瞬时 dead-link 为源码级** — stream_first_byte_timeout 83s 根因在 `handlers.py` R1411
   注释的 socket.timeout→continue 结构 (R1029 已确认)，无法用 env 干净归因修复，本轮不改
7. **本 tier 24h ATE=0** — RN1009 修复持续奏效

## 上次修改效果 (R1126 → R1127)
R1126 报 30min SR=99.33% (148/149)。本次 SR=99.34% (151/152)，基本持平（+0.01pct）。
6h SR 99.27% 与上轮持平。本轮未改任何参数，30min 波动系 key0 单次首字节超时 (83s) 的瞬时抖动，
属同一稳态噪声。请求量从 149/30min 略升至 152/30min，负载正常。

## 下一步建议
- **保持观察**。系统健康稳定，无需调整。
- 关注信号与预置对策:
  - 若 stream_first_byte_timeout 死链（83s）反复出现且聚集（≥3/30min 或单 key 集中）→ 才需
    评估源码级修复（让 read() 连续超时 N 次即走 deadline break，替代 continue 到底层 ~66s timeout）
  - 429 回升 → 增 `KEY_COOLDOWN_S` 30→60s
  - RemoteDisconnected/overloaded 频发且拉低请求级 SR → 考虑降 `UPSTREAM_TIMEOUT` 50→35s
  - IncompleteRead/SSLEOFError 若开始聚集 (≥30/h) → 检查对应 key 的 SOCKS5 代理端口
- 继续监控 5 个 SOCKS5 代理端口与 key 级瞬时错误复发风险。