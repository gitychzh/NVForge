# HM2 Optimize HM1 — Round R1285

**Date**: 2026-07-14 05:50 UTC
**Role**: HM2 → HM1 (HM2 optimizing HM1)
**Author**: opc2_uname

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = opc2_uname (HM2)，自提交
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (R1284→R1285 double-dispatch chain)
- 铁律:只改HM1不改HM2

## 2. 数据收集 (改前必有数据)

### 6h 总体
- 总请求: 66req/51OK/15fail = 77.3% SR
- 数据与 R1284/R1283/R1282/R1281/R1280 chain 完全一致 (同一批数据)

### 按模型
- glm5_2_nv: 53 (41OK/12fail=77.4%) avg_dur 7843ms
- dsv4p_nv: 13 (10OK/3fail=76.9%) avg_dur 36522ms

### 上游路径
- nv_integrate (glm5_2_nv): 53req, avg_ttfb 7478ms, avg_dur 7843ms
- nvcf_pexec (dsv4p_nv): 10req, avg_ttfb 25848ms, avg_dur 25873ms (all OK)
- ATE (dsv4p_nv): 3req, avg_dur 72019ms

### 错误分类
- 12× zombie_empty_completion (glm5_2_nv integrate, NVCF content-filter, input_chars avg 198K)
- 3× all_tiers_exhausted (dsv4p_nv — ALL pre-restart: 18:01, 18:02, 18:08 UTC)

### 容器重启时间: 2026-07-13T20:23:46Z (R1284/R1283 chain 重启)

### Post-restart (20:23 UTC → now)
- 9req/6OK/3fail = 66.7% SR
- 3 fail = zombie_empty_completion (glm5_2_nv, input_chars 210-215K)
- 6 OK = glm5_2_nv integrate, avg_dur 5710ms
- dsv4p_nv: 0 req post-restart
- 0 ATE post-restart

### 分段 (pre vs post restart)
- pre-restart: 57req/45OK/12fail = 78.9% (9 zombie + 3 ATE)
- post-restart: 9req/6OK/3fail = 66.7% (3 zombie, 0 ATE)

### Hourly SR
- 16:00 6req (66.7%)
- 17:00 6req (66.7%)
- 18:00 36req (86.1%) ← 3 ATE burst in this hour (pre-restart, pre-容器重启)
- 19:00 6req (66.7%)
- 20:00 3req (66.7%) ← post-restart
- 21:00 6req (66.7%) ← post-restart

### Fallback
- fallback_occurred=false for all 66 requests
- 0 fallback triggers

### tier_attempts
- 0 tier-level errors (confirming zombie = NVCF content-filter, not key-level)

### ms_gw
- Healthy: 4 MS-OK-STREAM (glm5_2_ms), 2 MS-OK-STREAM (dsv4p_ms)
- All MS-STREAM-DONE properly forwarded

### nv_gw 日志 (tail 100)
- 持续 zombie_empty_completion 模式: glm5_2_nv integrate, input_chars 210-215K, content_chars=12, finish_reason=stop
- NV-ZOMBIE-EMPTY + NV-ZOMBIE-ERROR-CHUNK detection working correctly (~4.6-5.4s abort)
- NV-INTEGRATE-SUCCESS 所有成功请求 1次尝试即成功 (2.2-3.3s per integrate)
- 0 NV-TIER-FAIL, 0 NV-GLOBAL-COOLDOWN, 0 NV-MSFB
- No errors other than zombie

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
- NVU_EMPTY_200_FASTBREAK=2 (known code-level no-op, R1039)

### compose md5: 28795fbe68f521457c09577f5da872ba (与 R1284/R1283 相同 — 无 compose 变更)

## 3. 决策

**NOP** — 无需修改任何参数。

原因:
- All post-restart failures = zombie_empty_completion (NVCF content-filter, 不可配置修复)
- 3 ATE 全为 pre-restart (18:01-18:08 UTC, 容器已于 20:23Z 重启), post-restart 0 ATE
- dsv4p_nv post-restart: 0 traffic — 无法评估是否需要调整 NVU_TIER_BUDGET_DSV4P_NV
- 数据与 R1284/R1283/R1282/R1281/R1280 chain 完全一致: 66req/51OK/15fail = 77.3% SR (同一 6h 窗口)
- All params at floor/optimal — no further reduction possible without risking success path
- ms_gw healthy (4 MS-OK-STREAM) — fallback path functional if ATEs recur
- 0 tier_attempts, 0 fallback → 网关健康
- 66.7% post-restart SR 纯粹由 NVCF content-filter 决定, 非 HM1 配置问题

评判: 更少报错更快请求超低延迟稳定优先 ✓

## 4. 参数变更

**无** — Zero param / Zero compose change / Zero container restart.

铁律:只改HM1不改HM2 ✓

## ⏳ 轮到HM1优化HM2