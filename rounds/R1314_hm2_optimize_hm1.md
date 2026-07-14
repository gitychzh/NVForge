# R1314: HM2→HM1 — NOP (false trigger, double-dispatch, 28th consecutive post-R1286, '这是我提交的, 不触发')

## 触发分析
- **Cron 脚本输出**: "这是我提交的, 不触发"
- **最新 commit**: R1313 (author=opc2_uname, HM2 self-commit)
- **HM1 git log**: 停在 R1206 (108 轮落后 HM2)
- **判定**: false trigger — HM1 未提交任何新内容

## 数据摘要 (改前必有数据)
- **DB NOW()**: 2026-07-14 03:03:38 UTC
- **6h**: 57req/50OK **87.7%SR**, 7 zombie_empty_completion (not config-fixable), glm5_2_nv integrate only
- **Hourly SR**: 66.7→71.4→83.3→83.3→96.6→100.0→0.0% (last hour: 1/1 zombie)
- **0 tier_attempts** — no key-level failures
- **0 ATE** (all_tiers_exhausted=0)
- **0 key_cycle_429s** (all 10 recent rows = 0)
- **0 fallback_occurred** (all 10 recent rows f=false)
- **ms_gw**: 13/13 100% OK (status='ok')
- **Container**: nv_gw Up 5 hours (healthy), ms_gw Up 17 hours (healthy)
- **Compose md5**: 6e1b58bc70eca49e500e3034b08376d9 (unchanged since R1286)
- **All params**: floor/optimal

## 错误分析
唯一错误类型: `zombie_empty_completion` (7/57 = 12.3%) — NVCF content filter (NVCF returns 200 Content-Length:0 on ~157K+ char input with content policy violation). Gateway zombie detection correctly aborts with synthetic error SSE chunk. Not config-fixable — NVCF-side content policy.

## 最近10条请求
```
03:03:20 glm5_2_nv 502 zombie   6463ms nv_integrate
02:33:45 glm5_2_nv 200          6165ms nv_integrate
02:33:39 glm5_2_nv 200          5686ms nv_integrate
02:33:20 glm5_2_nv 200         18173ms nv_integrate
02:03:32 glm5_2_nv 200          8569ms nv_integrate
02:03:20 glm5_2_nv 200         10964ms nv_integrate
01:33:43 glm5_2_nv 200         10087ms nv_integrate
01:33:27 glm5_2_nv 200         15578ms nv_integrate
01:33:21 glm5_2_nv 502 zombie   5112ms nv_integrate
01:26:29 glm5_2_nv 200         16298ms nv_integrate
```

## nv_gw 日志 (tail 100 grep error/warn/zombie/TIER-FAIL)
```
11:03:26 [NV-ZOMBIE-EMPTY] glm5_2_nv zombie empty completion: finish_reason=stop but content_chars=12 < 50, input_chars=175423 >= 5000 — aborting stream
11:03:26 [NV-ZOMBIE-ERROR-CHUNK] sent finish_reason=content_filter error SSE chunk
```
All other lines: NV-INTEGRATE-SUCCESS — k1-k5 all healthy, first-attempt success.

## 容器状态
```
nv_gw Up 5 hours (healthy)
ms_gw Up 17 hours (healthy)
Compose md5: 6e1b58bc70eca49e500e3034b08376d9
Env: UPSTREAM_TIMEOUT=66 TIER_COOLDOWN_S=15 KEY_COOLDOWN_S=25 MIN_OUTBOUND_INTERVAL_S=0
     NVU_PEXEC_TIMEOUT_FASTBREAK=1 NVU_INTEGRATE_TIMEOUT_FASTBREAK=1 NVU_EMPTY_200_FASTBREAK=2
     NVU_TIER_BUDGET_GLM5_2_NV=96 NVU_TIER_BUDGET_DSV4P_NV=72
     NVU_FALLBACK_HEALTH_THRESHOLD=0.05 NVU_MS_GW_FALLBACK_TIMEOUT=195
     NVU_PEER_FB_SKIP_MODELS= (empty — peer-fallback enabled for all)
     NVU_SSLEOF_RETRY_DELAY_S=1.0
```

## 决策: NOP

理由:
1. 所有参数 floor/optimal — 无可降空间
2. zombie_empty_completion 不可通过配置修复 (NVCF 内容过滤)
3. 0 tier_attempts = 0 ATE = 0 键级故障 — NVCF 功能健康
4. 5小时中仅1个 zombie (11:03), 其余全部 NV-INTEGRATE-SUCCESS
5. dsv4p_nv 0 traffic, kimi_nv 0 traffic — glm5_2_nv 独跑
6. ms_gw 13/13 100% — 健康后备
7. 铁律: 只改HM1不改HM2 — 无改可做

## ⏳ 轮到HM1优化HM2
