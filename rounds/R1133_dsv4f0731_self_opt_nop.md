# R1133: dsv4f0731_nv40666 Self-Optimization (NOP — SR=100%, 0 错误, 0 fallback, 0 429)

**Datetime**: 2026-08-08 03:56 UTC (11:56 Beijing)
**Container**: dsvf0731_nv40666 (port 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
**Model**: dsv4f0731_nv
**Verifier**: 本机 (HM2, opc2_uname)

## 结论
**不修改参数 (NOP)。** 30min **SR=100%** (181/181)，0 请求级错误，0 429，0 fallback，
全 pexec 且 per-key 完美均衡（38/38/33/36/36，延迟 10.2~11.4s）。较上一轮 R1132 (SR=100%, 173/173)
**稳态延续**。6h 请求级 SR≈99.5% (1818/1828)，3h 窗口 tier 级瞬时错误 (14 次：10 disconnected /
2 empty_200 / 1 timeout / 1 500) 全部被 5-key 循环在 180s budget 内吸收，**未造成任何请求级失败**。
本 tier 24h `all_tiers_exhausted`=0。无任何可调项需要介入；100% SR 下改参违反"改前必有数据"铁律。

## 30min 窗口 (脚本采集 03:56 UTC)
| 指标 | 值 |
|------|-----|
| Total | 181 |
| Success | 181 |
| **SR** | **100%** |
| Avg / P50 / P95 | 10,853ms / 8,799ms / 27,824ms |
| 请求级错误 | **0** |
| 429s | **0** |
| Fallback (hm4104, 5min) | **None** |
| Upstream | 100% nvcf_pexec (181/181) |
| finish_reason: tool_calls / stop | 159 / 22 |

## Per-Key 200 延迟 (30min)
| Key | count | avg_ok_ms | max 200_ms | 错误 |
|-----|-------|-----------|-----------|------|
| 0 | 38 | 11,412 | 26,401 | 0 |
| 1 | 38 | 10,648 | 28,324 | 0 |
| 2 | 33 | 10,524 | 23,243 | 0 |
| 3 | 36 | 10,223 | 27,591 | 0 |
| 4 | 36 | 11,409 | 26,300 | 0 |

5 个 key 请求数均衡 (33~38 each)，延迟 10.2~11.4s 均衡，**全部 100% 成功**。无劣化 key，
无 SOCKS5 代理异常，无需重新分配 integrate/pexec 路由。

## 趋势
- **6h 请求级**: 1828 total / 1818 OK / 10 非200 / 0 → **SR≈99.5%**
- **3h 逐小时**: 19:00→99.7% (315/316), 18:00→99.7% (346/347), 17:00→97.8% (273/279),
  16:00→100% (15/15)。17:00 窗口的 6 次失败为当日早些时候的瞬时扰动，未在 30min 窗口复现。
- **24h 本 tier all_tiers_exhausted**: **0**（已按 tier='dsv4f0731_nv' 在 nv_tier_attempts 核验）
- **tier 级错误分布 (24h)**: pexec_success 5228, RemoteDisconnected 450, Timeout 69,
  empty_200 54, 529 43, 504 8, budget_exhausted 2, 500 1 — 均为 key 循环内吸收，不影响请求级率。

## 修改明细
无。参数保持 R1023 以来的稳态：
UPSTREAM_TIMEOUT=50, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=90, KEY_COOLDOWN_S=30,
NVU_TIER_BUDGET_DSV4F0731_NV=180, NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_EMPTY_200_FASTBREAK=3.

## 验证
- `/health`: status=ok, nv_num_keys=5, port=40666 ✅
- 容器: dsvf0731_nv40666 Up 2 hours ✅

## 下一步建议
维持 NOP。持续监控是否出现某一 key 的 RemoteDisconnected 集中（超过 20% 占比）或 3h 窗口
请求级 SR 跌破 98%，届时优先处理该 key 的 SOCKS5 代理或考虑将问题 key 移出 pexec 循环。
当前 100% SR + 0 fallback 的稳态无需任何参数干预。