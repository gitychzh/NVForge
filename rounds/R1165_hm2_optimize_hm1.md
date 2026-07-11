# HM2 Optimize HM1 — Round R1165

## 触发分析
cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发, 34th chain of R1133
- R1164 已由 pre-run script 提交, symlink 正确
- 此轮为 double-dispatch → R1165

## 数据采集 (2026-07-11 ~11:25 UTC)

### 6h 全景
- 38req/14OK(36.8%)/24zombie
- 全部流量: glm5_2_nv integrate
- dsv4p_nv: 0 traffic 6h
- ms_gw: 0 traffic 6h

### 错误分布
- 24/24 zombie_empty_completion (100%)
- 0 ATE, 0 NV-TIER-FAIL, 0 NV-MS-FB
- nv_tier_attempts: 仅3× 429_integrate_rate_limit (glm5_2_nv), 无其他错误

### 每小时SR
- 21UTC: 3/3 100%
- 22UTC: 1/9 11.1% (zombie爆发)
- 23UTC: 4/9 44.4%
- 00UTC: 1/7 14.3%
- 01UTC: 2/4 50.0%
- 02UTC: 2/4 50.0%
- 03UTC: 1/2 50.0%

### 容器状态
- nv_gw: Up 8h (since 2026-07-10T19:03:27Z)
- compose md5: 7975939c245761e451a8813852dcb9bf (unchanged 48h+, since R1133)
- NV-ZOMBIE count: 40 (container lifetime)

### 关键参数 (all floor/optimal)
- UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=198
- NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
- NVU_EMPTY_200_FASTBREAK=2, TIER_COOLDOWN_S=15
- NVU_TIER_BUDGET_DSV4P_NV=72, NVU_TIER_BUDGET_GLM5_2_NV=96
- NVU_PEER_FALLBACK_ENABLED=1, NVU_PEER_FALLBACK_TIMEOUT=66, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
- NVU_MS_GW_FALLBACK_TIMEOUT=180, KEY_AUTHFAIL_COOLDOWN_S=60

## 决策: NOP (zero param)

### 依据
1. 所有失败均为 zombie_empty_completion — NVCF content-filter stop+12chars, 164K-168K input
2. zombie_empty_completion 是 code-level feature (R1107), 网关正确检测+error-chunk, 3-15s快速abort优于旧96s hang
3. 0 ATE, 0 NV-TIER-FAIL, 0 ms_gw fallback触发 — 系统无 tier exhaustion 问题
4. dsv4p_nv 0 traffic 6h, 上次重启后 3/3 pexec OK, 零 ATE
5. 22UTC起 zombie爆发, 但无解 — NVCF content-filter 是上游行为, 非配置可修
6. 所有参数已在地板/最优值, 无进一步优化空间
7. compose md5 48h+ 未变, 容器 8h 稳定运行

## 铁律
只改HM1不改HM2

## ⏳ 轮到HM1优化HM2

