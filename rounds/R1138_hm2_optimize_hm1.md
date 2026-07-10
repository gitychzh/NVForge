# HM2 Optimize HM1 — Round R1138

## Date: 2026-07-11 06:50 UTC

## 1. 触发分析

**Cron 脚本输出**: `"这是我提交的, 不触发"` + `2026-07-11 06:45:19 这是我提交的, 不触发`

- 最新 commit author = opc2_uname (HM2)
- HM2 最新 commit: R1137 (NOP, false trigger, sextuple-dispatch of R1133)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 → **误触发 (false trigger, septuple-dispatch of R1133)**

## 2. 数据收集 (改前必有数据)

### 容器状态
- 容器: `nv_gw` Up 4 hours (healthy)
- 重启时间: `2026-07-10T19:03:27Z` (约 11.8h 前)
- ⚠️ 容器时钟: `Fri Jul 10 22:48:54 UTC 2026` — 落后实际 UTC 时间约 8h (时钟漂移)
- 日志时间戳显示为 CST (本地时间), 06:03 CST = 22:03 UTC 前一晚
- tier_chain: `['glm5_2_nv'] (no fallback, 3model)` — 预期正常
- ms_gw: Healthy, Up 27 hours

### 6h 总体 (pre+post restart)
```
61 total, 42 OK, 19 fail = 68.9% SR
```

### 12h 总体
```
171 total, 149 OK, 22 fail = 87.1% SR
```

### Post-Restart 分段 (19:03 UTC 后)
```
31 total, 23 OK, 8 fail = 74.2% SR
```

### Post-Restart 失败 (8 次)
ALL 8 failures = `zombie_empty_completion` (code-level):
- 22:03 UTC → k0/k1/k3/k4 4× zombie (glm5_2_nv integrate, 3,105-4,353ms)
- 22:33 UTC → k1/k2/k3/k4 4× zombie (glm5_2_nv integrate, 2,041-3,236ms)

Gateway 正确检测并注入 NV-ZOMBIE-ERROR-CHUNK (content_filter SSE → openclaw fallback)

### Hourly SR (Post-Restart)
```
Hour (UTC)  Total  OK  Fail  SR%
19:00       6      6   0     100%
20:00       7      7   0     100%
21:00       9      9   0     100%
22:00       9      1   8     11.1%  ← zombie burst
```

### 按模型 (6h)
```
Model       Total  OK  Fail  SR%    AvgDur
glm5_2_nv   51     33  18    64.7%  8,233ms
dsv4p_nv    10     9   1     90.0%  18,029ms
```

### nv_tier_attempts (2h)
```
0 rows — 无 key-level 错误
```

### 日志确认 (tail 200)
```
8× NV-ZOMBIE-EMPTY (glm5_2_nv) — 全部 post-restart
content_chars=12-22 < 50, input_chars=161-163k >= 5000
All aborted via NV-ZOMBIE-ERROR-CHUNK (content_filter SSE → openclaw fallback)
All integrate k1-k5 succeed on first attempt — NVCF 100% healthy
```

### 活动窗口
- 最后 DB 记录: 2026-07-10 22:33:57 UTC
- 自 22:34 UTC 后 **零活动** (8+ 小时静默)
- docker logs --since 00:00 UTC Jul 11 = 完全空

### 当前 env 参数 (全部 floor/optimal)
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=198
NVU_TIER_BUDGET_DSV4P_NV=72
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=15
KEY_AUTHFAIL_COOLDOWN_S=60
MIN_OUTBOUND_INTERVAL_S=0
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
NVU_MS_GW_FALLBACK_TIMEOUT=180
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_SSLEOF_RETRY_DELAY_S=1.0
```

## 3. 优化决策

### 判定: **NOP — 不修改任何参数**

**理由:**

1. **False trigger**: 脚本输出 "这是我提交的, 不触发" — HM1 未提交新内容。R1133-R1137 全部为 NOP (R1133 的多次重分发)。

2. **零新数据**: 自 22:33 UTC Jul 10 后 8+ 小时完全静默。无新请求、无新错误、无新信号。R1137 数据与此轮完全一致。

3. **Post-restart 100% SR 3h, then zombie burst**: 19-21 UTC 三个小时 100% SR (22/22 OK)。22:00 的 8 个 zombie 是集中爆发，属于 code-level zombie_empty_completion — 代码已正确检测并快速中止 (2-4s vs old 95s NVStream_TimeoutError)。这是 R1107 确诊的 code-level 信号，不可配置修复。

4. **All 8 post-restart failures = zombie_empty_completion**: 零 key-level 错误 (nv_tier_attempts = 0 rows)。零 ATE (post-restart)。零 tier exhaustion。零 fallback 失败。系统健壮，无配置瓶颈。

5. **All params at floor/optimal**: UPSTREAM=66, BUDGET=198, FASTBREAK all at 1 (empty_200=2 per R1031), COOLDOWN at floor, PEER_FB at budget-safe levels. 无可优化空间。NVCF integrate 100% first-attempt success 证明链路健康。

6. **ms_gw 健康但未被触发**: 容器 Up 27h, 零 nv_gw 回调 — zombie 中止不触发 ms_gw fallback (code-level abort, 非 tier exhaustion)。

7. **铁律: 只改HM1不改HM2**: 无 HM1 配置变更需求。

## 4. 总结

```
R1138: HM2→HM1 — NOP (false trigger, septuple-dispatch of R1133, post-restart 100% SR 3h then 22:03 zombie burst, all 8 post-restart failures zombie_empty_completion code-level, 0 tier_attempts, 8h idle, all params at floor/optimal, no config change justified). 铁律:只改HM1不改HM2
```

## ⏳ 轮到HM1优化HM2