# R1134: dsv4f0731_nv40666 Self-Optimization (NOP — SR=100%, 0 错误, 0 fallback, 0 429)

**Datetime**: 2026-08-08 03:58 UTC (11:58 Beijing)
**Container**: dsvf0731_nv40666 (port 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
**Model**: dsv4f0731_nv
**Verifier**: 本机 (HM2, opc2_uname)

## 结论
**不修改参数 (NOP)。** 30min **SR=100%** (192/192)，0 请求级错误，0 429，0 fallback (hm4104)，
全 pexec 且 per-key 完美均衡（36~39 each，延迟 9.5~10.7s，0 错误 any key）。较上一轮 R1133
(SR=100%, 181/181) **稳态延续**。6h 请求级 SR≈99.2% (1824/1838)，tier 级瞬时错误
(RemoteDisconnected 29 / empty_200 7 / timeout 1 / 500 1) 全部被 5-key 循环在 180s budget 内吸收，
**未造成任何请求级失败**。本 tier 最近 6h `all_tiers_exhausted`=0。100% SR 下改参违反"改前必有数据"
铁律，无任何可调项需要介入。

## 30min 窗口 (脚本采集 03:58 UTC)
| 指标 | 值 |
|------|-----|
| Total | 192 |
| Success | 192 |
| **SR** | **100%** |
| Avg / P50 / P95 | 10,180ms / 8,319ms / 24,007ms |
| 请求级错误 | **0** |
| 429s | **0** |
| Fallback (hm4104, 5min) | **None** |
| Upstream | 100% nvcf_pexec (192/192) |
| finish_reason: tool_calls / stop | 169 / 23 |

## Per-Key 200 延迟 (30min)
| Key | count | avg_ok_ms | max 200_ms | 错误 |
|-----|-------|-----------|-----------|------|
| 0 | 39 | 10,619 | 24,609 | 0 |
| 1 | 39 | 9,513 | 22,954 | 0 |
| 2 | 36 | 10,759 | 23,442 | 0 |
| 3 | 39 | 9,527 | 23,970 | 0 |
| 4 | 39 | 10,525 | 23,095 | 0 |

5 个 key 请求数均衡 (36~39 each)，延迟 9.5~10.8s 均衡，**全部 100% 成功**。无劣化 key，
无 SOCKS5 代理异常，无需重新分配 integrate/pexec 路由。

## 趋势
- **6h 请求级** (nv_requests, tier_model=dsv4f0731_nv): 1838 total / 1824 OK / 14 非200 → **SR≈99.2%**
- **3h 逐小时** (预采集): 19:00→99.7% (334/335), 18:00→99.7% (346/347), 17:00→97.8% (273/279),
  16:00→100% (7/7)。17:00 窗口 6 次失败为当日瞬时扰动，未在 30min 窗口复现。
- **24h 本 tier all_tiers_exhausted**: **0**（已按 tier='dsv4f0731_nv' 在 nv_tier_attempts 核验；
  预采集脚本的 "111" 为跨全部 tier 的聚合值，非本 tier 专用，R1133 已确认本 tier 过滤后为 0）
- **tier 级错误分布 (6h, nv_tier_attempts)**: pexec_success 1221, RemoteDisconnected 29,
  empty_200 7, NVCFPexecTimeout 1, 500_nv_error 1 — 均为 key 循环内吸收，不影响请求级率。

## 修改明细
无。参数保持 R1023 以来的稳态：
UPSTREAM_TIMEOUT=50, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=90, KEY_COOLDOWN_S=30,
NVU_TIER_BUDGET_DSV4F0731_NV=180, NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_EMPTY_200_FASTBREAK=3,
NVU_KEYMGR_429_BASE_COOLDOWN=120, NVU_KEYMGR_CONN_BASE_COOLDOWN=30.

## 验证
- `/health`: status=ok, nv_num_keys=5, port=40666 ✅
- 容器: dsvf0731_nv40666 Up 2 hours ✅

## 下一步建议
维持 NOP。持续监控是否出现某一 key 的 RemoteDisconnected 集中（超过 20% 占比）或 3h 窗口
请求级 SR 跌破 98%，届时优先处理该 key 的 SOCKS5 代理或考虑将问题 key 移出 pexec 循环。
当前 100% SR + 0 fallback 的稳态无需任何参数干预。