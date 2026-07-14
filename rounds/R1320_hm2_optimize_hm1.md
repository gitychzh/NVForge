# HM2 Optimize HM1 — Round R1320

## 触发分析
cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch)
- HM1 本地 git log 停留在 R1206 (114 轮落后)
- 铁律:只改HM1不改HM2

## 数据收集 (改前必有数据)

### 6h 总体
57req/51OK 89.5%SR, 6 zombie_empty_completion
0 ATE 0 IncompleteRead 0 tier_attempts 0 fallback
ms_gw: 13/13 100%

### 6h 按模型
glm5_2_nv: 57req/51OK 89.5%SR, avg_dur=10447ms, max_dur=50550ms
dsv4p_nv: 0 traffic
kimi_nv: 0 traffic

### 6h 错误类型
zombie_empty_completion: 6 (glm5_2_nv integrate, NVCF content-filter stop+12-46chars, input_chars ~200K avg, ~5s detection)

### 6h 逐小时
22:00: 4req/3OK 75.0%
23:00: 6req/5OK 83.3%
00:00: 6req/5OK 83.3%
01:00: 29req/28OK 96.6%
02:00: 5req/5OK 100.0%
03:00: 5req/3OK 60.0%
04:00: 2req/2OK 100.0%

### 容器状态
nv_gw: Up 6 hours (healthy)
compose md5: 6e1b58bc70eca49e500e3034b08376d9 (stable)

### 关键参数
UPSTREAM_TIMEOUT=66, TIER_COOLDOWN_S=15, KEY_COOLDOWN_S=25
NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2, NVU_TIER_BUDGET_DSV4P_NV=72
NVU_TIER_BUDGET_GLM5_2_NV=96, NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_FALLBACK_HEALTH_THRESHOLD=0.05, NVU_PEER_FB_SKIP_MODELS=(empty)
0 NV-TIER-FAIL, 0 NV-EMPTY-FASTBREAK, 0 NV-MS-FB

## 决策: NOP

zombie_empty_completion = NVCF content-filter (glm5_2_nv integrate, ~200K input_chars, finish_reason=stop but content_chars 12-46 < 50). Gateway detection+error-chunk correct. Not config-fixable. All params floor/optimal. 0 tier_attempts 0 ATE 0 IncompleteRead 0 fallback. ms_gw 13/13 100%. Compose md5 6e1b58bc stable. NVU_PEER_FB_SKIP_MODELS empty. Zero param. 铁律:只改HM1不改HM2

## ⏳ 轮到HM1优化HM2
