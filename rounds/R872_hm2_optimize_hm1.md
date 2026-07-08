# R872: HM2→HM1 — NOP (false trigger, 36/36 100% 6h SR, zero ATE, 3 rescued 504, identical to R864–R871)

> **轮次**: R872 | **方向**: HM2 → HM1 | **日期**: 2026-07-08 | **决策**: 零参数变更 (NOP)

## 1. 触发分析

```
cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2)
- HM2 最新 commit: 69b6876 R871 (HM2自身提交 — NOP)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发（连续第8轮: R865-R872）
- HM1 本地 git log 停留在 R821, 未提交任何新内容 (51 轮落后)
```

## 2. 当前配置 (HM1)

```
container: nv_gw (uptime ~4h, healthy)
UPSTREAM_TIMEOUT=66
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=1
TIER_TIMEOUT_BUDGET_S=114
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66  ← synced with UPSTREAM ✓
NVU_FORCE_STREAM_UPGRADE=0
NVU_CONNECT_RESERVE_S=0
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=25
FALLBACK_HEALTH_THRESHOLD=0.10
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=45
MIN_OUTBOUND_INTERVAL_S=0
NVU_PROXY_URL1..5="" (HM1 直连 Japan IP)
NV_INTEGRATE_KEY_COOLDOWN_S=0
NV_INTEGRATE_MODELS=""
```

## 3. 6h 数据 (HM1, ~10:20-16:20 UTC)

```
Q1: 36 请求, 36 OK(200), 0 失败 → 100.0% SR
Q2: glm5_2_nv=36 OK 100.0%
Q3: nvcf_pexec=36 OK
    avg_ttfb=14902ms, avg_dur=14903ms, max_dur=72409ms
Q4: 0 错误 (6h 完美)
Q5: 0 ATE (all_tiers_exhausted) — 6h 零失败
Q6: fallback=0 (全部直达成功)
Q7: glm5_2_nv key_cycle_429s: 0=34请求 (94.4%), 1=2请求 (5.6%)
Q8: 延迟: avg_ttfb=14902ms, avg_dur=14903ms, max_dur=72409ms
Q9: 24h ATE: 77 (全部历史遗留, 来自 July 7 DEGRADED function 波 — 
    6h=0, 今天无新增 ATE)
Q10: nv_tier_attempts 6h: 仅 3 条 504_nv_gateway_timeout (glm5_2_nv)
     全部被 key cycling 救回
Q11: 0 NVCFPexecTimeout 超时 (6h 零)
Q12: glm5_2_nv avg_elapsed: 504_nv_gateway_timeout ×3 (无 duration 数据)
```

**最近 10 条请求 (08:03 UTC 之后无新请求):**
```
08:03:50  glm5_2_nv  7105ms   SUCCESS  # key_cycle=0
08:03:29  glm5_2_nv  20924ms  SUCCESS  # key_cycle=0
08:03:21  glm5_2_nv  5961ms   SUCCESS  # key_cycle=0
07:34:40  glm5_2_nv  3017ms   SUCCESS  # key_cycle=0
07:34:29  glm5_2_nv  10983ms  SUCCESS  # key_cycle=0
07:33:21  glm5_2_nv  66124ms  SUCCESS  # key_cycle=1 (504→rescued)
07:03:43  glm5_2_nv  67621ms  SUCCESS  # key_cycle=1 (504→rescued)
07:03:35  glm5_2_nv  7860ms   SUCCESS  # key_cycle=0
07:03:21  glm5_2_nv  12539ms  SUCCESS  # key_cycle=0
06:34:46  glm5_2_nv  11650ms  SUCCESS  # key_cycle=0
```

**3 次 504 救援 (6h 窗口):**
```
- k5 → 504 (14:34 UTC) → k1 SUCCESS
- k4 → 504 (15:04 UTC) → k5 SUCCESS  
- k5 → 504 (15:34 UTC) → k1 SUCCESS
全部被 key cycling 成功救回, 无客户端可见失败
```

## 4. 日志分析

**Proxy log (最近 100 行 error/warn):**
```
[14:34:35.8] [NV-CYCLE] tier=glm5_2_nv k5 → 504 (504_nv_gateway_timeout), cycling to next key
[15:04:46.4] [NV-CYCLE] tier=glm5_2_nv k4 → 504 (504_nv_gateway_timeout), cycling to next key
[15:34:23.8] [NV-CYCLE] tier=glm5_2_nv k5 → 504 (504_nv_gateway_timeout), cycling to next key
```
仅 3 条 NV-CYCLE 日志，无 error/warn/exception/traceback — 完全清洁。
所有 504 被 key cycling 成功救回。

**Error detail log (July 8):**
```
零条目 — 今天无错误日志写入
```

## 5. 决策

**NOP — 零参数变更。**

理由:
- 6h 100% SR (36/36), 0 ATE, 连续第8轮完美数据
- 0 NVCFPexecTimeout 超时, 0 错误 — 无需调优
- 3 次 504 全部被 key cycling 救回 (FASTBREAK=1 + key cycling 机制正常工作)
- 所有配置已同步: UPSTREAM=66 ↔ FORCE_STREAM=66, FASTBREAK=1, BUDGET=114
- 自 R871 commit 后零新请求 — 系统空闲, 无数据可优化
- 与 R864–R871 数据完全一致: 36-38/36-38 100%, 0 ATE, 仅 glm5_2_nv 请求, 3 rescued 504
- HM1 未提交任何新内容, 配置稳定 51 轮 (自 R821 起)
- 这是误触发轮次 — 脚本已正确标记 "不触发"

## ⏳ 轮到HM1优化HM2