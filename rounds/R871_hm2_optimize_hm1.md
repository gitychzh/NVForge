# R871: HM2→HM1 — NOP (false trigger, 38/38 100% 6h SR, zero ATE, 3 rescued 504, identical to R864–R870)

> **轮次**: R871 | **方向**: HM2 → HM1 | **日期**: 2026-07-08 | **决策**: 零参数变更 (NOP)

## 1. 触发分析

```
cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2)
- HM2 最新 commit: 6e553c0 R870 (HM2自身提交 — NOP)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发（连续第7轮: R865-R871）
- HM1 本地 git log 停留在 R821, 未提交任何新内容 (50 轮落后)
```

## 2. 当前配置 (HM1)

```
container: nv_gw (uptime ~12h, started 2026-07-08T04:12:50Z)
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

## 3. 6h 数据 (HM1, ~10:10-16:10 UTC)

```
Q1: 38 请求, 38 OK(200), 0 失败 → 100.0% SR
Q2: glm5_2_nv=36 OK 100.0%, NULL model=2 OK 100.0%
Q3: nvcf_pexec=36 OK, NULL upstream=2 OK
    avg_ttfb=14902ms, avg_dur=14903ms, max_dur=72409ms
Q4: 0 错误 (6h 完美)
Q5: 0 ATE (all_tiers_exhausted) — 6h 零失败
Q6: fallback=0 (全部直达成功)
Q7: glm5_2_nv key_cycle_429s: 0=33请求 (91.7%), 1=3请求 (8.3%)
Q8: 延迟: avg_ttfb=14902ms, avg_dur=14119ms, max_dur=72409ms, min=0ms
Q9: 24h ATE: 77 (全部历史遗留, 来自 July 7 DEGRADED function 波 — 
    6h=0, 今天无新增 ATE)
Q10: 自 R870 commit (16:10 UTC) 后: 0 新请求 — 系统空闲
Q11: nv_tier_attempts 6h: 仅 3 条 504_nv_gateway_timeout (glm5_2_nv)
     全部被 key cycling 救回
Q12: 0 NVCFPexecTimeout 超时 (6h 零)
```

**最近 10 条请求 (08:03 UTC 之后无新请求):**
```
08:03:50  glm5_2_nv  k5  7105ms  SUCCESS  # key_cycle=0
08:03:29  glm5_2_nv  k4  20923ms SUCCESS  # key_cycle=0
08:03:21  glm5_2_nv  k3  5961ms  SUCCESS  # key_cycle=0
07:34:40  glm5_2_nv  k2  3016ms  SUCCESS  # key_cycle=0
07:34:29  glm5_2_nv  k1  10983ms SUCCESS  # key_cycle=0
07:33:21  glm5_2_nv  ?   66124ms SUCCESS  # key_cycle=1 (504→rescued)
07:03:43  glm5_2_nv  ?   67621ms SUCCESS  # key_cycle=1 (504→rescued)
07:03:35  glm5_2_nv  ?   7860ms  SUCCESS  # key_cycle=0
07:03:21  glm5_2_nv  ?   12538ms SUCCESS  # key_cycle=0
06:34:46  glm5_2_nv  ?   11650ms SUCCESS  # key_cycle=0
```

**3 次 504 救援 (6h 窗口):**
```
- k5 → 504 (duration=66124ms) → k1 SUCCESS
- k4 → 504 (duration=67621ms) → k5 SUCCESS  
- k5 → 504 (duration=72409ms) → k1 SUCCESS
全部被 key cycling 成功救回, 无客户端可见失败
```

## 4. 日志分析

**Proxy log (最近 30 行):**
```
tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={...}) — FALLBACK_GRAPH 双向工作 ✓
所有请求: glm5_2_nv → NVCF pexec DIRECT → NV-SUCCESS (直达, 零 fallback)
3 次 504: NV-KEY → 504 → NV-CYCLE → next key → NV-SUCCESS
日志无 error/warn/exception/traceback — 完全清洁

最近请求 (16:03 UTC):
k3 6s SUCCESS, k4 21s SUCCESS, k5 7s SUCCESS — 全直达, 全成功
```

**Error detail log (July 8):**
```
零条目 — 今天无错误日志写入
```

**Error detail log (July 7 历史背景):**
```
18:19-21:05 UTC: glm5_2_nv DEGRADED function 波
  - 7× 400_nvcf_degraded → all_keys_failed → fallback dsv4p_nv
  - dsv4p_nv: empty_200 / 504 → all_tiers_failed → ATE
  - 24h ATE=77 全部来自此窗口, 今天无新增
```

## 5. 决策

**NOP — 零参数变更。**

理由:
- 6h 100% SR (38/38), 0 ATE, 连续第7轮完美数据
- 0 NVCFPexecTimeout 超时, 0 错误 — 无需调优
- 3 次 504 全部被 key cycling 救回 (FASTBREAK=1 + key cycling 机制正常工作)
- 所有配置已同步: UPSTREAM=66 ↔ FORCE_STREAM=66, FASTBREAK=1, BUDGET=114
- 自 R870 commit 后零新请求 — 系统空闲, 无数据可优化
- 与 R864–R870 数据完全一致: 38/38 100%, 0 ATE, 仅 glm5_2_nv 请求, 3 rescued 504
- HM1 未提交任何新内容, 配置稳定 49 轮 (自 R821 起)
- 这是误触发轮次 — 脚本已正确标记 "不触发"

## ⏳ 轮到HM1优化HM2