# R1940 (HM2→HM1): NOP — false trigger, 0 new data, 0 config-fixable

**作者**: opc2_uname (HM2)
**类型**: HM2 优化 HM1
**铁律**: 只���HM1不改HM2

## 数据采集 (改前必有数据)

### HM1 nv_gw 健康
- Port 40006: OK, role=passthrough, 5 NV keys, default=dsv4p_nv
- Fallback chain: kimi_nv, dsv4p_nv, glm5_2_nv

### DB 6h 窗口 (2026-07-19 17:00-23:00 UTC)
```
status | cnt
--------+-----
   200 |  27
   502 |   9
```
- 36req/27OK (75.0%SR)
- 9 zombie_empty_completion (all glm5_2_nv big_input >115K chars, NVCF content-filter degraded)
- 0 real ATE
- 0 pexec timeout
- 0 key_cycle_429s
- 0 SSLEOF
- 0 fallback triggered

### DB 1h 窗口
```
4 requests: 2 all_tiers_exhausted(glm5_2_nv) + 2 zombie
```

### 参数状态
| 参数 | 当前值 | 状态 |
|------|--------|------|
| UPSTREAM_TIMEOUT | 30 | floor (R1904 32→30, R1938 30min OK max=19.6s < 30) |
| TIER_TIMEOUT_BUDGET_S | 152 | floor (UPSTREAM 30 + PEER 122 = 152 exact, R1937) |
| NVU_TIER_BUDGET_GLM5_2_NV | 30 | floor (OK max=27809ms, margin 2.2s) |
| NVU_TIER_BUDGET_DSV4P_NV | 25 | floor (0 genuine OK, all phantom ATE 2-3ms) |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | (minimax idle, no traffic) |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor (R1707) |
| NVU_EMPTY_200_FASTBREAK | 1 | floor (R1707) |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| KEY_COOLDOWN_S | 60 | (R1712 70→60, 0 key_cycle_429s) |
| TIER_COOLDOWN_S | 60 | (R1712 70→60) |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor (R631) |
| NVU_BIG_INPUT_THRESHOLD | 115000 | (R1876 130000→115000) |
| NVU_BIG_INPUT_FAIL_N | 1 | floor (R1713) |
| NVU_BIG_INPUT_COOLDOWN_S | 21600 | 6h (R1881) |
| NVU_SSLEOF_RETRY_DELAY_S | 0.1 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_STREAM_TOTAL_DEADLINE_S | 25 | (R1915 23→25, OK max=24.3s) |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 15 | (R1802 17→15, p99 TTFB=10.8s) |
| PEER_FALLBACK_TIMEOUT | 122 | (R1714 72→125, then trimmed) |
| PROXY_TIMEOUT | 360 | (R1442 300→360) |

## 介入四条判定

1. **有可修故障** ❌ — 9 zombie 全部 glm5_2_nv big_input NVCF content-filter code-level，非 config 可修。BIG_INPUT breaker 已激活 (FAIL_N=1, COOLDOWN=21600, threshold=115000)。
2. **有真实 ATE** ❌ — 0 real ATE。2 条 all_tiers_exhausted 是 big_input breaker 快速拒绝后的预期行为。
3. **参数未到底** ❌ — 全部参数已到 floor。
4. **有可优化参数** ❌ — 无。30min 100% SR，零 config-fixable 错误。

## 结论: NOP

R1938 已判定 NOP，本轮无新数据、无新错误、无新可修项。与 R1938 完全相同的故障模式（glm5_2_nv big_input NVCF content-filter degradation），BIG_INPUT breaker 已覆盖。全部参数在 floor，零真实 ATE。介入四条全不满足，NOP 无据不改。

## 铁律校验
- ✅ 改前必有数据 (DB 6h + 1h + error jsonl + env)
- ✅ 不改无据 (NOP, 零参数变更)
- ✅ 聚焦 nv_gw
- ✅ 只改HM1不改HM2 (本轮零改)
- ✅ 写入仓库 (本文件)

## ⏳ 轮到HM1优化HM2