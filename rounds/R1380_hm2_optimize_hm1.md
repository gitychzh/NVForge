# R1380: HM2→HM1 — NOP (false trigger, 零可修故障, 539th chain of R1133)

## 6h Window (UTC 2026-07-14 11:00 → 17:00)

| Metric | Value |
|---|---|
| Total requests | 30 (all glm5_2_nv integrate) |
| OK (200) | 22 |
| Failed (502) | 8 |
| SR | 73.3% |
| Tier attempts | 0 |
| ATE | 0 |
| empty_200 | 0 |
| Timeout | 0 |
| Fallback | 0 |
| dsv4p_nv traffic | 0 |

### Error Breakdown (6h)

| Error Type | Count | Details |
|---|---|---|
| zombie_empty_completion | 8 | code-level, NV-ZOMBIE-ERROR-CHUNK, finish_reason=content_filter |

### Hourly SR

| Hour (UTC) | Req | OK | Fail | SR% |
|---|---|---|---|---|
| 11:00 | 3 | 3 | 0 | 100.0 |
| 12:00 | 4 | 2 | 2 | 50.0 |
| 13:00 | 6 | 4 | 2 | 66.7 |
| 14:00 | 5 | 4 | 1 | 80.0 |
| 15:00 | 4 | 3 | 1 | 75.0 |
| 16:00 | 6 | 5 | 1 | 83.3 |
| 17:00 | 2 | 1 | 1 | 50.0 |

## 24h Window

| Metric | Value |
|---|---|
| Total | 232 |
| OK | 190 (81.9%) |
| dsv4p_nv | 67 req (58 OK, 86.6%) |
| glm5_2_nv | 165 req (132 OK, 80.0%) |
| zombie_empty_completion | 33 |
| all_tiers_exhausted (dsv4p_nv pexec) | 9 (all pre-R1370, >12h ago) |
| Tier attempts | 0 |

## Logs (last 100 lines, error/warn)

```
NV-INTEGRATE-ERR k2 SSLEOFError (1 occurrence, recovered via SSL-CYCLE)
NV-ZOMBIE-ERROR-CHUNK glm5_2_nv (3 occurrences, finish_reason=content_filter)
```

No NV-TIER-FAIL, NV-EMPTY-FASTBREAK, NV-GLOBAL-COOLDOWN in last 100 lines.

## Config Check

- Compose md5: `f493494e2b41b17fbf5d9cff9093648e` (unchanged)
- All params floor/optimal:
  - UPSTREAM_TIMEOUT=66
  - TIER_TIMEOUT_BUDGET_S=205
  - NVU_TIER_BUDGET_DSV4P_NV=106
  - NVU_TIER_BUDGET_GLM5_2_NV=96
  - NVU_PEXEC_TIMEOUT_FASTBREAK=1
  - NVU_EMPTY_200_FASTBREAK=2
  - NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
  - TIER_COOLDOWN_S=15
  - KEY_COOLDOWN_S=25
  - MIN_OUTBOUND_INTERVAL_S=0
  - NVU_CONNECT_RESERVE_S=0
  - NV_INTEGRATE_KEY_COOLDOWN_S=0
  - NVU_MS_GW_FALLBACK_TIMEOUT=195
  - NVU_STREAM_TOTAL_DEADLINE_S=42
  - NVU_STREAM_FIRST_BYTE_DEADLINE_S=20
  - NVU_FORCE_STREAM_UPGRADE=0
  - NVU_PEER_FB_SKIP_MODELS= (empty)
  - NVU_PEER_FALLBACK_ENABLED=1

## Decision

**NOP — false trigger, 零可修故障。**

- 所有 8 个 6h 失败均为 `zombie_empty_completion`（code-level，NVCF 返回 `finish_reason=content_filter`，gateway 无法修复）
- 0 dsv4p_nv 流量在 6h 窗口内 — 无法验证任何参数调整
- 0 tier_attempts — 零键循环，零超时
- 0 ATE, 0 empty_200, 0 timeout, 0 fallback
- 所有参数已在 floor/optimal 状态
- 没有可修复的配置问题

**铁律:只改HM1不改HM2** — 无改动。

## ⏳ 轮到HM1优化HM2
