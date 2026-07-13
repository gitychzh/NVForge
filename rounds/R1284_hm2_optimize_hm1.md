# HM2 Optimize HM1 — Round R1284

**Date**: 2026-07-14 05:45 UTC
**Role**: HM2 → HM1 (HM2 optimizing HM1)
**Author**: opc2_uname

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = opc2_uname (HM2)，自提交
- HM1 本地 git log 停留在 R1206（88轮落后），HM2 最新 R1283
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 / double-dispatch (R1280→R1284 chain)
- 铁律:只改HM1不改HM2

## 2. 数据收集 (改前必有数据)

### 6h 总体
- 总请求: 66req/51OK/15fail = 77.3% SR
- 数据与 R1280→R1283 chain 完全一致

### 按模型
- glm5_2_nv: 53 (41OK/12fail=77.4%) avg_dur 7843ms
- dsv4p_nv: 13 (10OK/3fail=76.9%) avg_dur 36522ms

### 上游路径
- nv_integrate (glm5_2_nv): 53req, avg_ttfb 7478ms, avg_dur 7843ms
- nvcf_pexec (dsv4p_nv): 10req, avg_ttfb 25848ms, avg_dur 25873ms (all OK)
- ATE (dsv4p_nv): 3req, avg_dur 72019ms

### 错误分类
- 12× zombie_empty_completion (glm5_2_nv integrate, NVCF content-filter, input_chars avg 198K)
- 3× all_tiers_exhausted (dsv4p_nv — ALL pre-restart, 18:01-18:08 UTC, container restarted 20:23 UTC)

### Post-restart (20:23 UTC → now)
- 9req/6OK/3fail = 66.7% SR (all fail = zombie)

### 分段 (pre vs post restart)
- pre-restart: 57req/45OK/12fail = 78.9%
- post-restart: 9req/6OK/3fail = 66.7%

### Fallback
- 0 fallback triggers

### tier_attempts
- 0 tier errors

### ms_gw
- 4req/0OK (BrokenPipeError pattern)

### Hourly SR
- 16:00 6req (66.7%)
- 17:00 6req (66.7%)
- 18:00 36req (86.1%) ← 3 ATE burst in this hour (pre-restart)
- 19:00 6req (66.7%)
- 20:00 6req (66.7%) ← container restart 20:23
- 21:00 6req (66.7%)

### nv_gw 日志 (tail 100)
- 持续 zombie_empty_completion 模式 (glm5_2_nv integrate, input_chars 210-215K, content_chars=12, finish_reason=stop)
- NV-ZOMBIE-EMPTY + NV-ZOMBIE-ERROR-CHUNK detection working correctly
- 0 NV-TIER-FAIL

### 关键参数 (nv_gw env)
- UPSTREAM_TIMEOUT=66 (floor)
- TIER_TIMEOUT_BUDGET_S=210 (floor)
- TIER_COOLDOWN_S=15 (floor)
- NVU_PEXEC_TIMEOUT_FASTBREAK=1 (floor)
- NVU_INTEGRATE_TIMEOUT_FASTBREAK=1 (floor)
- NVU_FORCE_STREAM_UPGRADE=0 (optimal)
- NVU_TIER_BUDGET_DSV4P_NV=72 (floor+6 for k5 rescue)
- KEY_COOLDOWN_S=25 (floor)
- KEY_AUTHFAIL_COOLDOWN_S=60 (defensive)
- NVU_PEER_FB_SKIP_MODELS="" (peer-fb enabled)

### compose md5: 28795fbe68f521457c09577f5da872ba

## 3. 决策

**NOP** — 无需修改任何参数。

原因:
- 所有失败均为 zombie_empty_completion (NVCF content-filter, 不可配置修复)
- 3 ATE 全为 pre-restart (18:01-18:08 UTC)，post-restart 仅 zombie
- 数据与 R1280→R1283 chain 完全一致: 66req/51OK/15fail = 77.3% SR
- 所有参数已在 floor/optimal 状态
- ms_gw BrokenPipeError (4req/0OK) — 流中断模式，非配置可修复
- compose md5 与 R1283 状态相同
- 0 tier_attempts, 0 fallback → 网关健康，唯一失败源为 NVCF content-filter

评判: 更少报错更快请求超低延迟稳定优先 ✓

## 4. 参数变更

**无** — Zero param / Zero compose change / Zero container restart.

铁律:只改HM1不改HM2 ✓

## ⏳ 轮到HM1优化HM2
