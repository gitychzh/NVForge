# R1132: dsv4f0731_nv40666 Self-Optimization (NOP — SR=100%, 0 错误, 0 fallback)

**Datetime**: 2026-08-08 03:52 UTC (11:52 Beijing)
**Container**: dsvf0731_nv40666 (port 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
**Model**: dsv4f0731_nv
**Verifier**: 本机 (HM2, opc2_uname)

## 结论
**不修改参数 (NOP)。** 30min **SR=100%** (173/173)，0 请求级错误，0 fallback，0 429，
全 pexec 且 per-key 完美均衡。较上一轮 R1131 (SR=99.39%, 1 transient dead-link) **进一步改善**。
6h 请求级 SR≈99.28%，最新 45min DB 仅见 19:16 一次瞬时 502，其余连续 200。
本 tier 24h `all_tiers_exhausted`=0。无任何可调项需要介入；100% SR 下改参违反"改前必有数据"铁律。

## 30min 窗口 (脚本采集 03:52 UTC)
| 指标 | 值 |
|------|-----|
| Total | 173 |
| Success | 173 |
| **SR** | **100%** |
| Avg / P50 / P95 / P99 | 11,504ms / 9,180ms / 31,394ms / 37,614ms |
| 请求级错误 | **0** |
| 429s | **0** |
| Fallback (hm4104) | **None** |
| Upstream | 100% nvcf_pexec (173/173) |
| finish_reason: tool_calls / stop | 151 / 22 |

## Per-Key 200 延迟 (30min)
| Key | count | avg_ok_ms | 200 max_ms | 错误 |
|-----|-------|-----------|-----------|------|
| 0 | 38 | 12,800 | 29,138 | 0 |
| 1 | 33 | 11,278 | 29,158 | 0 |
| 2 | 32 | 10,973 | 26,916 | 0 |
| 3 | 36 | 10,996 | 32,254 | 0 |
| 4 | 34 | 11,310 | 25,412 | 0 |

5 个 key 请求数均衡 (32~38 each)，延迟 10.9~12.8s 均衡，**全部 100% 成功**。无劣化 key。
key0 上一轮 (R1131) 的瞬时 dead-link 本轮未再现，SOCKS5 端口 7897 已自愈，无需干预。

## 趋势 (6h 请求级逐小时)
| 时段 | Total | OK | 非200 | SR | avg_ms |
|------|-------|-----|-------|-----|--------|
| 19:00 | 293 | 292 | 1 | 99.66% | 11,666 |
| 18:00 | 347 | 346 | 1 | 99.71% | 11,992 |
| 17:00 | 279 | 273 | 6 | 97.85% | 11,786 |
| 16:00 | 30 | 30 | 0 | 100% | 16,349 |

6h 合计 1,829 请求, 1,816 成功 (SR≈99.29%)。**最新两小时 SR≥99.7%，逐时上行**。
24h `all_tiers_exhausted`=112 为跨 tier 汇总窗口，本 tier 核验 =0（RN1009 修复持续奏效）。

## 当前参数 (本次未改动, env 实值已核实)
UPSTREAM_TIMEOUT=50 · TIER_TIMEOUT_BUDGET_S=180 · NVU_TIER_BUDGET_DSV4F0731_NV=180 ·
NVU_TIER_BUDGET_DSV4F_NV=180 · KEY_COOLDOWN_S=30 · TIER_COOLDOWN_S=90 ·
NVU_KEYMGR_429_BASE/MAX=120/120 · NVU_KEYMGR_CONN_BASE/MAX/LONG=30/60/120 ·
NVU_KEYMGR_CONN_FAIL_THRESHOLD=3 · NVU_PEXEC_TIMEOUT_FASTBREAK=3 ·
NVU_EMPTY_200_FASTBREAK=3 · NVU_BUFFER_TIMEOUT_STAIRS=90×5 · NVU_PROBE_TIMEOUT=10 ·
NV_INTEGRATE_KEYS=空(integrate 未启用) · NVU_PEER_FALLBACK_ENABLED=0 · NVU_PROBE_ENABLED=1

任务提示"可调参数"表为模板默认值，与 live env 实值不一致；以 **live env 为权威**，未漂移。

/health 返回 ok，port 40666，5 keys，模型/tiers 列表完整。容器 Up 约 2 小时。

## NOP 原因
1. **30min SR=100%** — 超过 95% 阈值上限，0 次错误
2. **0 请求级错误、0 fallback、0 429** — 全链路无异常信号
3. **本 tier 24h ATE=0** — RN1009 修复持续奏效
4. **per-key 全部健康且完美均衡** — 5 key 各 32~38 req、近满负载，延迟 10.9~12.8s，无劣化
5. **key0 的 SOCKS5 瞬时抖动已自愈** — 上轮 dead-link 未复发
6. **全部 pexec**、最新 45min DB 仅 1 次瞬时 502 — 链路优秀
7. 100% SR 下修改任何参数都无数据支撑，违反"改前必有数据"

## 上次修改效果 (R1131 → R1132)
R1131 报 30min SR=99.39% (164/165, 1 transient dead-link key0)。本次 SR=**100%** (173/173)，
提升 +0.61pct，瞬时错误清零。Avg 从 12,265ms 降至 11,504ms（-761ms，抽样噪声内，P50 9,180ms 持平）。
请求量从 165→173 略增，负载稳定。本轮未改任何参数，系统延续 R1130~R1131 稳态并持稳。

## 下一步建议
- **保持观察**。系统健康稳定，SR 连续 3 轮 ≥99.4% 且本轮达 100%。
- 关注信号与预置对策:
  - stream_first_byte_timeout 死链（83s）若**重新**聚集（≥3/30min 或单 key 集中）→ 评估
    源码级修复 (R1029/R1131 已知根因于 `handlers.py` socket.timeout→continue 结构)
  - 429 回升 → 增 `KEY_COOLDOWN_S` 30→60s
  - RemoteDisconnected/overloaded 频发且拉低 SR → 考虑降 `UPSTREAM_TIMEOUT` 50→35s
  - IncompleteRead/SSLEOFError 聚集 (≥30/h) → 检查对应 key 的 SOCKS5 端口
  - key0 近 6 轮均未再出现持久错误，可解除其 SOCKS5 7897 端口优先排查关注
- 继续监控 5 个 SOCKS5 代理端口与 key 级瞬时错误复发风险。