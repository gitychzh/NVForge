# HM2 Optimize HM1 — Round R1117

## 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = `opc2_uname` (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (false trigger, double-dispatch of R1116)
- HM1 本地 git log 停留在 R821 (295 轮落后)，未提交任何新内容

## 数据采集 (改前必有数据)

### HM1 环境
```
容器重启: 2026-07-10T19:03:27Z (约 8h 前)
NVU_TIER_BUDGET_DSV4P_NV=72 (R1116)
NVU_TIER_BUDGET_GLM5_2_NV=96
TIER_TIMEOUT_BUDGET_S=198
UPSTREAM_TIMEOUT=66
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_MS_GW_FALLBACK_TIMEOUT=180
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
```

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
zombie_empty_completion: 9  (code-level, fast abort 3-15s, R1107)
all_tiers_exhausted:     3  (dsv4p_nv, ms_gw BrokenPipeError)
NVStream_TimeoutError:   2  (code-level, old 96s hang)
```

### 6h ATE 详情
```
dsv4p_nv:  3× tiers_tried_count=1, fallback_actually_attempted=false, avg 61,297ms
glm5_2_nv: 11× tiers_tried_count=1, fallback_actually_attempted=false, avg 23,046ms
  (9 zombie + 2 NVStream_TimeoutError = 11 code-level, 0 config-fixable)
```

### 6h nv_tier_attempts
```
0 rows — 无 key-level 错误
```

### nv_gw tier_chain
```
['dsv4p_nv'] (no fallback, 3model) — R832 FALLBACK_GRAPH={} 预期状态
```

### ms_gw 日志
```
MS-OK-STREAM / MS-STREAM-DONE: 正常交付 (glm5.2, deepseek-v4-pro)
MS-STREAM-CLIENT-EOF + BrokenPipeError: 流式同步缺陷 (code-level, R1103)
```

## 决策: NOP

**零参数, 零 compose 修改, 零容器重启。**

### 根因分析

| 失败数 | 错误类型 | 根因 | 可配置修复? |
|--------|---------|------|-----------|
| 9 | zombie_empty_completion | 上游模型返回空流, code-level zombie 检测 (R1107) | ❌ code-level |
| 2 | NVStream_TimeoutError | NVCF 流式超时, 96s hang | ❌ code-level |
| 3 | all_tiers_exhausted (dsv4p_nv) | ms_gw BrokenPipeError 流式同步缺陷 (R1103) | ❌ code-level |

**3 个 dsv4p_nv ATE**: 61.3s avg, `fallback_actually_attempted=false`. 这是 ms_gw BrokenPipeError 模式 — nv_gw 发送了 relay 请求到 ms_gw, ms_gw 成功处理 (MS-OK-STREAM/MS-STREAM-DONE), 但 nv_gw 未收到完成信号 → BrokenPipeError → ATE. R1116 的 +6s (BUDGET 66→72) 给了 k5 预算在 tier 内救援, 但 ms_gw BrokenPipeError 是流式同步缺陷, BUDGET 不强制执行在 ms_gw relay 路径上 (R1103 discovery). 无配置参数可修复.

**glm5_2_nv 11 失败**: 全部 code-level (9 zombie + 2 NVStream_TimeoutError). 0 nv_tier_attempts — 无 key 级别错误, FASTBREAK 已到 floor.

**所有参数已在最优/floor**: TIER_COOLDOWN_S=15 (R1103 revert), NVU_PEXEC_TIMEOUT_FASTBREAK=1 (R997), NVU_INTEGRATE_TIMEOUT_FASTBREAK=1 (R1010), NVU_EMPTY_200_FASTBREAK=2 (code-level no-op R1039), TIER_TIMEOUT_BUDGET_S=198 (R1071), UPSTREAM_TIMEOUT=66 (R963), NVU_TIER_BUDGET_DSV4P_NV=72 (R1116).

**铁律**: 只改 HM1 不改 HM2 ✓

## ⏳ 轮到HM1优化HM2
