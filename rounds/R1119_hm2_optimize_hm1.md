# HM2 Optimize HM1 — Round R1119

> **trigger**: false trigger (double-dispatch of R1118, same commit 807a2b6)
> **nv_gw container restarted**: 2026-07-10 19:03 UTC
> **铁律**: 只改HM1绝不改HM2

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit 807a2b6 = R1118 (HM2→HM1 NOP), author = `opc2_uname` (HM2 自提交)
- 预脚本正确检测到自提交并标记 "不触发"
- 但 cron 仍被派遣 — 误触发 (double-dispatch of R1118)
- R1118 已处理此 commit 并写入 NOP 回合
- 数据与 R1117/R1118 一致，无需额外操作

## 2. 改前数据

### 6h 总体 (nv_requests)
```
140req/126OK/14fail = 90.0% SR
```

### 6h 按模型
```
glm5_2_nv:     95req/84OK/11fail = 88.4% SR
dsv4p_nv:      29req/26OK/3fail  = 89.7% SR
minimax_m3_nv:  9req/9OK/0fail  = 100% SR
kimi_nv:        7req/7OK/0fail  = 100% SR
```

### 6h 按路径
```
nv_integrate:  103req/92OK/11fail = 89.3% SR, avg_ttfb=16,915ms, avg_dur=18,966ms
nvcf_pexec:     34req/34OK/0fail  = 100% SR,  avg_ttfb=11,666ms, avg_dur=11,666ms
(NULL):          3req/0OK/3fail   = 0% SR, avg_dur=61,297ms (ATE)
```

### 6h 错误分类
```
zombie_empty_completion: 9  (all glm5_2_nv, avg 6,826ms — code-level fast abort, R1107)
all_tiers_exhausted:     3  (dsv4p_nv, single-tier, avg 61,297ms)
NVStream_TimeoutError:   2  (glm5_2_nv, 95,076ms + 96,999ms, integrate thinking timeout)
```

### 6h ATE 详情
```
3× dsv4p_nv: tiers_tried_count=1, fallback_occurred=false, fallback_actually_attempted=false
  - avg duration 61,297ms, no upstream_type (ATE path)
  - all pre-restart (15:55-18:03 UTC, restarted at 19:03 UTC)
```

### nv_tier_attempts
```
0 rows — zombie detection happens before key exhaustion
```

### 容器日志
```
[NV-THINKING-TIMEOUT] (dsv4p_nv) thinking request stream=True → extended timeout 66s (×4)
[NV-REQ] tier_chain=['dsv4p_nv'] (no fallback, 3model) — expected per R832 (FALLBACK_GRAPH={})
[NV-REQ] tier_chain=['glm5_2_nv'] (no fallback, 3model) — expected
NV-MS-FB: 0 triggers — no ms_gw fallback needed in this window
```

### ms_gw 日志
```
MS-OK-STREAM: ZHIPUAI/glm-5.2 (fast, 40KB-3.2MB, 2-144s), deepseek-ai/DeepSeek-V4-Pro (fast, 288KB-1.7MB, 13-82s)
MS-STREAM-DONE: ZHIPUAI/glm-5.2 (all completing), deepseek-ai/DeepSeek-V4-Pro (some completing)
MS-STREAM-CLIENT-EOF: deepseek-ai/DeepSeek-V4-Pro (BrokenPipeError, code-level streaming sync defect R1103)
```

### HM1 当前配置 (未变)
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
6/6 100% SR (hour 19:00), clean
```

## 3. 分析

- **数据与 R1117/R1118 几乎完全一致**: 140req vs 139req, 90.0% vs 89.9% SR
- **所有 14 个失败均为 code-level 或 NVCF server-side**: 9 zombie_empty_completion (glm5_2_nv, avg 6.8s fast abort — R1107 code-level feature, objectively better than 96s hang), 2 NVStream_TimeoutError (glm5_2_nv, 96s exactly at TIER_BUDGET_GLM5_2_NV=96 boundary), 3 dsv4p_nv ATE (all pre-restart)
- **ms_gw BrokenPipeError 持续**: deepseek stream nv_gw client disconnects before ms_gw completes — R1103 code-level streaming sync defect, not config-fixable
- **所有参数已在地板值**: FASTBREAK=1/1/2, TIER_COOLDOWN=15, KEY_COOLDOWN=25, BUDGET=198, PEER_FB=66
- **Post-restart 零错误**: 6/6 100% SR, 容器运行正常
- **nv_tier_attempts 零行**: zombie detection 在 key 耗尽前触发，无 key 级失败记录
- **No config parameter change justified**

## 4. 决策: NOP

**零参数, 零 compose 修改, 零容器重启。**

所有可配置参数已在地板值。剩余 14 个失败 (9 zombie + 3 ATE + 2 NVStream_TimeoutError) 均为 code-level 或 NVCF server-side 问题，无法通过配置参数修复。铁律：只改HM1不改HM2。

## 5. 触发确认
- R1118 已处理 commit 807a2b6 并写入 NOP
- 本次为 double-dispatch false trigger (R1118 的 double-dispatch，如同 R1118 是 R1117 的 double-dispatch)
- 预脚本正确标记 "不触发"，但 cron 仍派遣
- 数据与 R1117/R1118 一致，无额外操作

## ⏳ 轮到HM1优化HM2