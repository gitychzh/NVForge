# HM2 Optimize HM1 — Round R1118

> **trigger**: false trigger (double-dispatch of R1117, same commit e0d8742)
> **nv_gw container restarted**: 2026-07-10 19:03 UTC
> **铁律**: 只改HM1绝不改HM2

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit e0d8742 = R1117 (HM2→HM1 NOP), author = `opc2_uname` (HM2 自提交)
- HM1 的 cron 正确检测到自提交并标记 "不触发"
- 但 cron 仍被派遣 — 误触发 (double-dispatch of R1117)
- R1117 已处理此 commit 并写入 NOP 回合
- HM1 本地 git log 停留在 R821 (296 轮落后)，未提交任何新内容

## 2. 改前数据 (R1117 相同窗口)

### 6h 总体 (nv_requests)
```
139req/125OK/14fail = 89.9% SR
```

### 6h 按模型
```
glm5_2_nv:     94req/83OK/11fail = 88.3% SR, avg 19,228ms
dsv4p_nv:      29req/26OK/3fail  = 89.7% SR, avg 19,314ms
minimax_m3_nv:  9req/9OK/0fail  = 100% SR, avg 14,483ms
kimi_nv:        7req/7OK/0fail  = 100% SR, avg 3,605ms
```

### 6h 错误分类
```
zombie_empty_completion: 9  (code-level, NVCF integrate empty content)
all_tiers_exhausted:     3  (dsv4p_nv, single-key empty_200, ms_gw BrokenPipeError)
NVStream_TimeoutError:   2  (code-level, 96s stream hang)
```

### 6h ATE 详情
```
dsv4p_nv:  3× tiers_tried_count=1, fallback_occurred=false, avg 61,297ms
  - all_empty_200=true, num_attempts=1 (single key, all others on cooldown)
  - ms_gw: 7req/0OK (BrokenPipeError, code-level)
  - peer_fb: not triggered (fallback_occurred=false)
```

### HM1 当前配置
```
TIER_COOLDOWN_S=15
TIER_TIMEOUT_BUDGET_S=198
UPSTREAM_TIMEOUT=66
KEY_COOLDOWN_S=25
KEY_AUTHFAIL_COOLDOWN_S=60
MIN_OUTBOUND_INTERVAL_S=0
NVU_CONNECT_RESERVE_S=0
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_STREAM_TOTAL_DEADLINE_S=42
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
NVU_TIER_BUDGET_DSV4P_NV=72
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
```

### Post-restart (19:03+ UTC)
```
4/4 100% SR (dsv4p_nv), clean
```

## 3. 分析

- **所有 14 个失败均为 code-level 或 NVCF server-side**：9 zombie_empty_completion (NVCF integrate 空响应)、2 NVStream_TimeoutError (流式 96s hang)、3 dsv4p_nv ATE (single-key empty_200 + ms_gw BrokenPipeError)
- **ms_gw 完全不可用**: 7req/0OK, BrokenPipeError 流式同步缺陷 (R1103), 非配置可修复
- **peer_fb 未触发**: fallback_occurred=false on all 3 ATE, 代码层 ms_gw 先于 peer_fb 但 ms_gw 失败后未降级到 peer_fb
- **所有参数已在地板/最优值**: FASTBREAK=1/1/2, TIER_COOLDOWN=15, KEY_COOLDOWN=25, BUDGET=198
- **Post-restart 零错误**: 4/4 100% SR, RR 正常轮转, 无 429s
- **No config parameter change justified**

## 4. 决策: NOP

**零参数, 零 compose 修改, 零容器重启。**

所有可配置参数已在地板值。剩余 14 个失败 (9 zombie + 3 ATE + 2 NVStream_TimeoutError) 均为 code-level 或 NVCF server-side 问题，无法通过配置参数修复。铁律：只改HM1不改HM2。

## 5. 触发确认
- R1117 已处理 commit e0d8742 并写入 NOP
- 本次为 double-dispatch false trigger
- 数据与 R1117 一致，无需额外操作

## ⏳ 轮到HM1优化HM2