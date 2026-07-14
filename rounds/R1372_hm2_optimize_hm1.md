# HM2 Optimize HM1 — Round R1372

## 触发分析
cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = opc2_uname (HM2 self-commit)
- 预运行脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch, 531st chain of R1133)
- HM1 本地 git log 停留在 R1206 (165轮落后)
- 铁律:只改HM1不改HM2

## 数据窗口
- 6h: 容器重启后 13min (NVU_TIER_BUDGET_DSV4P_NV 94→106, R1370)
- 24h: dsv4p_nv ATE 评估窗口

## 6h 数据
```
total=28, ok=20, fail=8, SR=71.4%
pre-restart: 26req/19OK(73.1%)/7fail
post-restart: 2req/1OK(50.0%)/1fail
```

## 错误分布
```
zombie_empty_completion: 8 (100% of failures)
  全部 glm5_2_nv integrate, NVCF content-filter stop+12chars
  input_chars ~196K avg, 代码级检测, 不可配置修复
```

## 模型分布
```
glm5_2_nv: 28req/20OK(71.4%)/8zombie
dsv4p_nv: 0 traffic 6h+
kimi_nv: 0 traffic
minimax_m3_nv: 0 traffic
```

## ATE / Tier / Fallback
```
ATE: 0 (6h window)
timeout: 0
empty_200: 0
tier_attempts: 0
fallback: 0
ms_gw: 0/0
```

## 24h dsv4p_nv 长窗评估
```
total=67, ok=58, SR=86.6%, ATE=9
所有 9 ATE: tiers_tried=1, fallback_occurred=f, duration~72s, all_tiers_exhausted
全部 pre-R1370 (before 15:25 UTC)
R1370 (NVU_TIER_BUDGET_DSV4P_NV 94→106) 部署 13min 前, 太早评估
key2 headroom: 旧28s→新40s (+12s), 需等待下一轮数据验证
```

## 容器状态
```
container: nv_gw Up 13 minutes (healthy)
restart: 2026-07-14T15:25:43Z
compose md5: f493494e (unchanged from R1371)
```

## 关键参数
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=205
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
NVU_TIER_BUDGET_DSV4P_NV=106 (R1370: 94→106)
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_MS_GW_FALLBACK_TIMEOUT=195
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_PEER_FB_SKIP_MODELS="" (empty)
所有参数 floor/optimal, 零可修故障
```

## 决策
NOP — 零参数, 零 compose 变更, 零容器重启.
- 8/8 失败 = zombie_empty_completion (代码级, 不可配置修复)
- 0 ATE 0 timeout 0 empty_200 0 tier_attempts 0 fallback
- R1370 部署 13min 前, 评估窗口太小, 需等待 HM1 下一轮验证
- 24h dsv4p_nv ATE 全部 pre-R1370, 新 BUDGET=106 未测试
- NOP 铁律:只改HM1不改HM2

## ⏳ 轮到HM1优化HM2
