# R1176: HM2→HM1 — NOP (false trigger, 44th chain of R1133, zombie-only, all params floor/optimal, NVCF content-filter not config-fixable)

## TL;DR
6h: 29req/10OK(34.5%)/19zombie. All failures zombie_empty_completion (glm5_2_nv integrate, NVCF content-filter stop+12chars, 166K-170K input). Gateway detection+error-chunk correct. dsv4p_nv 0 traffic 6h. ms_gw 0 nv-initiated traffic. compose md5 unchanged (7975939c245761e451a8813852dcb9bf). All params at floor/optimal. Zero param. 铁律:只改HM1不改HM2.

---

## 一、触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = opc2_uname (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (44th chain of R1133)
- R1175 已是最新回合，symlink 已指向 R1175

## 二、数据收集（改前必有数据 — 6h 窗口）

### 2.1 容器信息
- nv_gw started: 2026-07-11 03:03 CST (up ~10h)
- compose md5: 7975939c245761e451a8813852dcb9bf (unchanged)

### 2.2 6h 总体
- 29 req / 10 OK (34.5%) / 19 zombie
- All upstream: nv_integrate (glm5_2_nv only)
- dsv4p_nv: 0 traffic 6h
- All errors: zombie_empty_completion (19)
- 0 ms_gw fallback, 0 tier-fail

### 2.3 每小时 SR 趋势
| Hour (UTC) | Total | OK | Fail | SR% |
|---|---|---|---|---|
| 23:00 | 4 | 0 | 4 | 0.0 |
| 00:00 | 7 | 1 | 6 | 14.3 |
| 01:00 | 4 | 2 | 2 | 50.0 |
| 02:00 | 4 | 2 | 2 | 50.0 |
| 03:00 | 4 | 2 | 2 | 50.0 |
| 04:00 | 4 | 2 | 2 | 50.0 |
| 05:00 | 2 | 1 | 1 | 50.0 |

### 2.4 最近 10 条请求
All glm5_2_nv integrate, zombie cycle: 30s interval between zombie detect and next request (openclaw retry), zombie detection at 3-8s. Gateway detection+error-chunk correct. Perfect alternating OK↔zombie pattern every 30 min. 10 OK all succeed on 1st key (3-8s).

### 2.5 Tier Attempts
- 3× 429_integrate_rate_limit (minor, no elapsed_ms)

### 2.6 ms_gw
- 0 nv-initiated traffic (no ms_gw fallback triggered)
- ms_gw serving direct requests independently

### 2.7 24h 全景
- glm5_2_nv: 207/164(79.2%), avg_ok_dur=17.1s, max_ok=125.9s
- dsv4p_nv: 33/26(78.8%), avg_ok_dur=14.5s, max_ok=48.0s
- minimax_m3_nv: 9/9(100%), kimi_nv: 7/7(100%)

### 2.8 Logs pattern
```
[NV-ZOMBIE-EMPTY] (glm5_2_nv) passthrough zombie empty completion: finish_reason=stop but content_chars=12 < 50, input_chars=166K-170K >= 5000, no tool_calls — aborting stream to trigger openclaw fallback
[NV-ZOMBIE-ERROR-CHUNK] (glm5_2_nv) sent finish_reason=content_filter error SSE chunk to openclaw
```
Input chars growing: 166K→170K (openclaw conversation accumulating).

## 三、参数检查清单

| # | 参数 | 值 | 可调? | 理由 |
|---|------|-----|-------|------|
| 1 | UPSTREAM_TIMEOUT | 66 | ❌ | Floor for integrate (NVCF content-filter, not timeout) |
| 2 | TIER_TIMEOUT_BUDGET_S | 198 | ❌ | Headroom for openclaw retry cycle, not binding |
| 3 | MIN_OUTBOUND_INTERVAL_S | 0 | ❌ | Floor |
| 4 | NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | ❌ | Floor |
| 5 | TIER_COOLDOWN_S | 15 | ❌ | R1103 verified optimal |
| 6 | NVU_PEER_FALLBACK_TIMEOUT | 66 | ❌ | Aligned with UPSTREAM_TIMEOUT |
| 7 | NVU_CONNECT_RESERVE_S | 0 | ❌ | Floor |
| 8 | NVU_SSLEOF_RETRY_DELAY_S | 1.0 | ❌ | Floor |
| 9 | NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | ❌ | Aligned, not active (FORCE_STREAM_UPGRADE=0) |
| 10 | NVU_FORCE_STREAM_UPGRADE | 0 | ❌ | Disabled, stable |
| 11 | NVU_EMPTY_200_FASTBREAK | 2 | ❌ | R1031 verified, but no empty_200 occurring |
| 12 | NV_INTEGRATE_ENABLED | (via MODELS) | ❌ | Needed for glm5_2_nv |
| 13 | NV_INTEGRATE_MODELS | glm5_2_nv | ❌ | Correct |
| 14 | NV_INTEGRATE_KEY_COOLDOWN_S | 0 | ❌ | Floor |
| 15 | KEY_COOLDOWN_S | 25 | ❌ | Stable, long history |
| 16 | NVU_TIER_BUDGET_DSV4P_NV | 72 | ❌ | R1116 verified, dsv4p_nv 0 traffic |
| 17 | NVU_TIER_BUDGET_GLM5_2_NV | 96 | ❌ | Stable |
| 18 | NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | ❌ | R923 defensive, zombie not peer-fb-fixable |

## 四、变更

**Zero param change; zero compose edit; zero restart.**

All failures are NVCF content-filter stop+12chars (zombie_empty_completion) — a code-level NVCF behavior, not config-fixable. Gateway detection is already optimal (abort in 3-8s, return 502 error-chunk to openclaw). dsv4p_nv has 0 traffic — openclaw likely using ms_gw dsv4p_ms directly. All floor params at minimum. No tier-attempt errors beyond minor 429_integrate_rate_limit (3×, no elapsed_ms). Input chars growing 166K→170K across 6h indicates openclaw accumulating conversation context, not a gateway issue.

**No optimization space. NOP.**

## 五、铁律确认
- ✅ 改前必有数据 (6h DB + logs + env collected)
- ✅ 聚焦 nv_gw
- ✅ 所有修改写入仓库 (NOP 回合记录)
- ✅ 只改 HM1 不改 HM2 (本轮无变更)
- ✅ 少改多轮 (本轮不改, 等数据积累)

## ⏳ 轮到HM1优化HM2