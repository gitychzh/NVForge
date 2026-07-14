# R1309: HM2→HM1 — NOP (23rd consecutive post-R1286, all params floor/optimal, zombie-only failures)

## 触发分析
- **Cron 脚本输出**: R1308 → HM2 turn, "这是我提交的, 不触发"
- **最新 commit author**: opc2_uname (HM2) — R1308
- **判定**: HM2 collected data from HM1, analyzed, decision: NOP

## 数据摘要 (改前必有数据)
- **DB NOW()**: 2026-07-14 02:03 UTC (last nv_requests ts)
- **6h**: 59req/51OK **86.4%SR**, 8 zombie_empty_completion (not config-fixable), glm5_2_nv integrate only
- **1h**: 29req/28OK **96.6% SR** (strong — only 1 zombie)
- **24h**: 271req/216OK **79.7% SR** (55 failures, all zombie)
- **0 tier_attempts** — no key-level failures
- **0 ATE** (all_tiers_exhausted=0)
- **0 key_cycle_429s**
- **0 fallback_occurred**
- **ms_gw**: 13/13 100% (from script)
- **Container**: nv_gw healthy, Up ~4 hours, restart 2026-07-13T22:14:51Z
- **Compose md5**: 6e1b58bc70eca49e500e3034b08376d9 (unchanged since R1286)
- **All params**: floor/optimal

## 错误分析
唯一错误类型: `zombie_empty_completion` (8/59 = 13.6%) — NVCF content filter: NVCF returns 200 Content-Length:0 on ~213K avg char input with content policy violation. Gateway zombie detection correctly aborts with synthetic error SSE chunk. **Not config-fixable** — NVCF-side content policy.

## 最近10条请求 (DB)
```
02:03:31 glm5_2_nv 200      8569ms nv_integrate
02:03:20 glm5_2_nv 200     10964ms nv_integrate
01:33:43 glm5_2_nv 200     10087ms nv_integrate
01:33:27 glm5_2_nv 200     15578ms nv_integrate
01:33:21 glm5_2_nv 502 zombie  5112ms nv_integrate  ← zombie
01:26:29 glm5_2_nv 200     16298ms nv_integrate
01:25:38 glm5_2_nv 200     50550ms nv_integrate
01:25:21 glm5_2_nv 200     17527ms nv_integrate
01:25:07 glm5_2_nv 200     13074ms nv_integrate
01:24:53 glm5_2_nv 200     13097ms nv_integrate
```

## 日志分析 (tail 100)
- 100% NV-INTEGRATE-SUCCESS on first attempt (k1-k5 round-robin)
- 1x NV-ZOMBIE-EMPTY (09:33:26, glm5_2_nv k3, content_chars=12 < 50, input_chars=175K, content_filter)
- 0 errors, 0 warnings, 0 ATE, 0 NV-TIER-FAIL
- Latency: 2-5s typical, 50s outlier (one large request)

## 容器状态
```
nv_gw Up 4 hours (healthy) — restart 2026-07-13T22:14:51Z
ms_gw healthy
Compose md5: 6e1b58bc70eca49e500e3034b08376d9
Env: UPSTREAM_TIMEOUT=66 TIER_COOLDOWN_S=15 KEY_COOLDOWN_S=25 MIN_OUTBOUND_INTERVAL_S=0
     NVU_PEXEC_TIMEOUT_FASTBREAK=1 NVU_INTEGRATE_TIMEOUT_FASTBREAK=1 NVU_EMPTY_200_FASTBREAK=2
     NVU_TIER_BUDGET_GLM5_2_NV=96 NVU_TIER_BUDGET_DSV4P_NV=72
     NVU_FALLBACK_HEALTH_THRESHOLD=0.05 NVU_MS_GW_FALLBACK_TIMEOUT=195
     NVU_FORCE_STREAM_UPGRADE=0 NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
     NVU_INTEGRATE_THINKING_TIMEOUT_S=90
     NVU_PEER_FB_SKIP_MODELS= (empty — peer-fb enabled for all)
```

## 决策: NOP

理由:
1. 所有参数 floor/optimal — 无可降空间
2. zombie_empty_completion 不可通过配置修复 (NVCF 内容过滤)
3. 0 tier_attempts = 0 ATE = 0 键级故障 — NVCF 功能健康
4. 1h 96.6% SR, 仅有 1 个 zombie
5. dsv4p_nv 0 traffic, kimi_nv 0 traffic — glm5_2_nv 独跑
6. ms_gw 13/13 100% — 健康
7. 日志显示 100% first-attempt integrate success (0 retries, 0 key cycling)
8. 铁律: 只改HM1不改HM2 — 无改可做
9. 23rd consecutive NOP post-R1286 — 系统已达稳态

## ⏳ 轮到HM1优化HM2