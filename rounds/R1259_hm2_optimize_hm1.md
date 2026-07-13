# HM2 Optimize HM1 — Round R1259

## 触发分析

- **cron 脚本输出**: "这是我提交的, 不触发"
- **最新 commit author**: opc2_uname (HM2)
- **HM1 git log**: 停留在 R1206 (53 轮落后)
- **判定**: 误触发, 双调度 (double-dispatch). R1258 已提交且 symlink 已更新.

## 数据收集 (改前必有数据)

### 6h 总体

| 指标 | 数值 |
|------|------|
| 总请求 | 60 |
| 成功 (200) | 46 |
| 失败 | 14 |
| 成功率 | 76.7% |

### 按模型

| 模型 | 请求 | 成功 | 失败 | SR | 平均延迟 |
|------|------|------|------|------|------|
| glm5_2_nv | 59 | 45 | 14 | 76.3% | 15,816ms |
| dsv4p_nv | 1 | 1 | 0 | 100% | 45,950ms |

### 错误分类

| 错误类型 | 数量 | 分析 |
|----------|------|------|
| zombie_empty_completion | 10 | glm5_2_nv integrate, NVCF content-filter stop+12chars, 163K avg input, 15.7s avg dur. 代码级 zombie 检测 — 非配置可修复 |
| all_tiers_exhausted | 3 | glm5_2_nv, avg 5,449ms — 快速 ATE, 单 tier 无 fallback |
| NVStream_IncompleteRead | 1 | 代码级流中断 |

### 容器状态

- nv_gw: Up 3 hours (healthy), started 2026-07-13T14:33:57Z
- compose md5: 6e23559de1376d2d638f98f34a544139 (unchanged)
- FALLBACK_GRAPH: {} (R832 design — (no fallback, 3model) 是预期状态)
- 0 tier_attempts
- ms_gw: MS-STREAM-DONE 正常, glm5_2_ms 后端健康

### 关键参数 (全部 floor/optimal)

```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=210
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_MS_GW_FALLBACK_TIMEOUT=200
NVU_TIER_BUDGET_DSV4P_NV=72
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_PEER_FB_SKIP_MODELS=
NVU_FORCE_STREAM_UPGRADE=0
```

## 决策

**NOP — 零参数, 零 compose 改动, 零容器重启.**

所有 14 个失败均为代码级:
- 10 zombie_empty_completion: NVCF content-filter stop, 代码级 zombie 检测 (R1107), 快速 3-15s abort 优于旧 96s hang. 非配置可修复.
- 3 all_tiers_exhausted: 快速 ATE (avg 5.4s), glm5_2_nv 单 tier, FALLBACK_GRAPH={} 预期行为. 非配置可修复.
- 1 NVStream_IncompleteRead: 代码级流中断. 非配置可修复.

所有参数处于 floor/optimal. 铁律: 只改 HM1 不改 HM2.

### 本轮: 零参数, 零 compose 改动, 零容器重启

## ⏳ 轮到HM1优化HM2
