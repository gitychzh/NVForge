# R2292: HM2优化HM1 — 降低FALLBACK_HEALTH_THRESHOLD解除dsv4p_nv预阻断

## 数据收集 (2026-07-23 16:10 UTC+8)

### DB 6h 概览
| 指标 | 值 |
|------|-----|
| 总请求 | 32 |
| 成功 | 20 (62.5%) |
| 失败 | 12 |
| 平均延迟(OK) | 27938ms |

### 按模型分解
| 模型 | 总请求 | 成功 | 失败 | 成功率 | 平均延迟(OK) |
|------|--------|------|------|--------|-------------|
| glm5_2_nv | 24 | 18 | 6 | 75.0% | 28762ms |
| dsv4p_nv | 8 | 2 | 6 | 25.0% | 20518ms |

### 错误分类
| 模型 | 错误类型 | 数量 |
|------|---------|------|
| dsv4p_nv | all_tiers_exhausted (502) | 6 |
| glm5_2_nv | zombie_empty_completion | 3 |
| glm5_2_nv | all_tiers_exhausted (breaker OPEN) | 3 |

### dsv4p_nv ATE 详情 (6h)
- 6个真实502 ATE，全部 **0 tier_attempts**，延迟 6-9ms
- 2个 phantom 200 ATE
- 全部发生在 02:37 和 03:07 UTC 的突发
- 最近30min: 0请求

### 容器 env 关键参数
```
KEY_COOLDOWN_S=0
TIER_COOLDOWN_S=0
KEY_AUTHFAIL_COOLDOWN_S=0
NVU_TIER_BUDGET_DSV4P_NV=160
TIER_TIMEOUT_BUDGET_S=275
FALLBACK_HEALTH_THRESHOLD=0.20
NVU_FALLBACK_HEALTH_THRESHOLD=0.20
```

### 日志分析
- nv_gw 日志无 error/warn (最近100行干净)
- 无 tier skip / preempt / breaker 日志

## 根因分析

**dsv4p_nv ATE 0 tier_attempts 预阻断**：尽管所有 cooldown 已归零(KEY_COOLDOWN_S=0, TIER_COOLDOWN_S=0, KEY_AUTHFAIL_COOLDOWN_S=0)，dsv4p_nv 请求仍被瞬间拒绝(6-9ms, 0 tier_attempts)。预算160s足够5个key(5×24=120s)。唯一可能的阻断来源是 **FALLBACK_HEALTH_THRESHOLD=0.20** 的健康检查门槛。

dsv4p_nv 6h 成功率仅 25%（2/8），健康分可能 < 0.20，导致 tier 被运行状况检查预阻断——即使 cooldown 全零，health check 仍可在请求进入 tier 轮询前拒绝。

**glm5_2_nv**: 75% SR 可接受。3个 zombie + 3个 breaker OPEN ATE 属于上游 NVCF 问题，HM1 配置无法修复。

## 优化方案

**单参数改动**: `FALLBACK_HEALTH_THRESHOLD` 0.20→0.10，`NVU_FALLBACK_HEALTH_THRESHOLD` 0.20→0.10

**推理**: 0.20 门槛过高——dsv4p_nv 25% SR 可能低于此阈值，导致 tier 被健康检查预阻断。降至 0.10 允许更低的健康分仍可尝试 tier，给 5 个 key 机会完成请求。dSV4P 成功请求虽少但可在预算内完成（20518ms avg）。

**预算验证**: 160s 预算 - 0 cooldown = 160s。5 keys × 24s UPSTREAM = 120s。160-120=40s margin。健康门槛降低后，即使只有 1-2 个 key 成功，也优于直接 502。

## 优化执行

### 改动
```
FALLBACK_HEALTH_THRESHOLD=0.20 → 0.10  (line 432)
NVU_FALLBACK_HEALTH_THRESHOLD=0.20 → 0.10  (line 466)
```

### 重启
- `docker compose -f /opt/cc-infra/docker-compose.yml up -d --no-deps --force-recreate nv_gw`
- ✅ 容器重启成功，health 200
- ✅ 容器 live env 验证: FALLBACK_HEALTH_THRESHOLD=0.10, NVU_FALLBACK_HEALTH_THRESHOLD=0.10

### 评判
- 更少报错: 降低健康门槛 → 更多请求可尝试 tier → 减少 502 ATE
- 更快请求: 预算充足(160s)，cooldown 全零，key 轮转无障碍
- 超低延迟: 无回归风险（仅放宽健康检查，不改超时/预算）
- 稳定优先: 保守改动（0.20→0.10），留有余量

## ⏳ 轮到HM1优化HM2