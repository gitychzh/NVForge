# HM2 Optimize HM1 — Round R981

## 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = opc2_uname (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch after R980)
- HM1 本地 git log 停留在 R821（160 轮落后）

## 6h 数据 (改前必有数据)

### nv_gw 6h 摘要
```
DB: 33req/30OK(90.9%)/3ATE(9.1%)
  - tiers_tried_count=1: 1 ATE (avg 112,060ms)
  - tiers_tried_count=2: 2 ATE (avg 174,417ms)
  - fallback_occurred=20 (59.4% of all requests, glm5_2→dsv4p tier fallback)
```

### nv_tier_attempts 6h (仅失败尝试)
```
glm5_2_nv NVCFPexecTimeout: 5 keys, 18 attempts total
  max=62,606ms (k4), uniform across K0-K4 (56,990-62,606ms) → function-level
  avg range: 54,958-61,400ms
glm5_2_nv 504_nv_gateway_timeout: 5 attempts (K0=1, K1=3, K3=1)
glm5_2_nv empty_200: 3 attempts (K1=1, K4=2)
glm5_2_nv budget_exhausted_after_connect: 1 attempt (K2)
dsv4p_nv: 0 tier attempts (all success)
```

### nv_gw 日志 (最近错误)
```
[16:03-16:05] glm5_2_nv: 504→k2→fast-break(K1 timeout)→dsv4p fallback SUCCESS
[16:04-16:05] glm5_2_nv: k3 timeout(49,205ms)→fast-break→dsv4p fallback SUCCESS
[16:18-16:19] glm5_2_nv: k3 504→k4 timeout(49,581ms)→fast-break→ALL-TIERS-FAIL (no dsv4p, FALLBACK_GRAPH={})
[16:34-16:35] glm5_2_nv: k4 504→k5 timeout(49,529ms)→fast-break→ALL-TIERS-FAIL (no dsv4p)
[16:37] NV-MS-FB: ms_gw relay failed after 124,325ms: TimeoutError → returning local 502
```

### ms_gw 6h
```
DB: 10 requests (ms_requests table populated)
Logs: MS-OK 2x, MS-OK-STREAM+MS-STREAM-DONE 1x, MS-ALL-EXHAUSTED 1x (stream_no_data_lines)
EMPTY_200=3 (floor), all at established values
```

### nv_gw env (当前)
```
UPSTREAM_TIMEOUT=64
TIER_TIMEOUT_BUDGET_S=112
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=3
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=64
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=25
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=45
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
NV_INTEGRATE_KEY_COOLDOWN_S=0
MIN_OUTBOUND_INTERVAL_S=0
FALLBACK_HEALTH_THRESHOLD=0.05 (dead param — func_health uses NVU_FALLBACK_HEALTH_THRESHOLD=0.10)
```

## 判定: NOP

### 与 R980 对比
| 指标 | R980 | R981 (fresh) |
|------|------|-------------|
| 6h SR | 33/30 90.9% | 33/30 90.9% |
| ATE | 3 | 3 |
| ATE tiers_tried=1 | 1 (avg 112,060ms) | 1 (avg 112,060ms) |
| ATE tiers_tried=2 | 2 (avg 174,417ms) | 2 (avg 174,417ms) |
| NVCFPexecTimeout max | 62,606ms | 62,606ms |
| ms_gw req | 10 | 10 |
| Fallback count | 20 | 20 |

- 数据完全相同 — 无退化
- NVCFPexecTimeout max=62,606ms < UPSTREAM=64 (1,394ms buffer) — 非绑定约束
- BUDGET=112 >> UPSTREAM=64 — 安全
- FASTBREAK=1, EMPTY_200=3, MIN_OUTBOUND=0, CONNECT=0, INTEGRATE=0 (全部 floor)
- FORCE_STREAM_UPGRADE=0 (禁用), FORCE_STREAM_TIMEOUT=64 ≥ UPSTREAM=64 (对齐)
- KEY_COOLDOWN=25, TIER_COOLDOWN=25 (长期稳定，无下调空间)
- FALLBACK_GRAPH={} 是 R832 设计的预期行为
- ms_gw 同模型 fallback 生效 (MS-OK/MS-STREAM-DONE), 1 次 streaming timeout 为代码级问题

### 决策: 零变更
- 无参数修改
- 无 compose 修改
- 无容器重启
- 铁律: 只改 HM1 不改 HM2 ✓

## ⏳ 轮到HM1优化HM2
