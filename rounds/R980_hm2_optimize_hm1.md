# HM2 Optimize HM1 — Round R980

## 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = opc2_uname (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch after R979)
- HM1 本地 git log 停留在 R821（159 轮落后）

## 6h 数据 (改前必有数据)

### nv_gw 6h 摘要
```
DB: 33req/30OK(90.9%)/3ATE(9.1%)
  - tiers_tried_count=1: 1 ATE (avg 112,060ms)
  - tiers_tried_count=2: 2 ATE (avg 174,417ms)
```

### nv_gw 日志
```
FALLBACK_GRAPH={} (R832 设计: 同模型 ms_gw fallback 替代跨模型 FALLBACK_GRAPH)
tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback) → 16:01-16:03 正常
tier_chain=['glm5_2_nv'] (no fallback, 3model) → 16:17+ R710 transient disappearance
  → ms_gw same-model fallback activated: 2 OK, 1 timeout (124s)
  → NV-MS-FB: ms_gw relay failed after 124325ms: TimeoutError: timed out
  → ms_gw successfully processed request (MS-STREAM-DONE 22636b) but nv_gw didn't see completion
  → Code-level streaming issue, not config-fixable
```

### ms_gw 6h
```
DB: 10 requests, 0 OK, 0 ATE (status column mismatch — ms_gw logs show successful processing)
Logs: EMPTY_200=3 (floor), 2 same-model fallback requests OK, 1 stream timeout
Params: ALL_EXHAUSTED_COOLDOWN_S=30, KEY_COOLDOWN_S=60, PROXY_TIMEOUT=600, UPSTREAM_TIMEOUT=300
All at established values, no drift.
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

### 与 R979 对比
| 指标 | R979 | R980 (fresh) |
|------|------|-------------|
| 6h SR | 34/31 91.2% | 33/30 90.9% |
| ATE | 3 | 3 |
| Fallback SR | 21/21 100% | 2/2 100% (ms_gw same-model) |
| ms_gw req | 0 (idle) | 10 (3 nv_gw fallback relay) |

- 数据几乎相同 — 无退化
- 所有参数在 floor/optimal — 无优化空间
- NVCFPexecTimeout 在 UPSTREAM=64 内 — 无绑定边缘
- BUDGET=112 >> UPSTREAM=64 — 安全
- FALLBACK_GRAPH={} 是 R832 设计的预期行为
- ms_gw 同模型 fallback 生效 (2/3 OK, 1 timeout 是代码级 streaming 问题)

### 决策: 零变更
- 无参数修改
- 无 compose 修改
- 无容器重启
- 铁律: 只改 HM1 不改 HM2 ✓

## ⏳ 轮到HM1优化HM2

