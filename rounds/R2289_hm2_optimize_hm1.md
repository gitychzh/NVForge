# R2289: HM2优化HM1 — NVU_BIG_INPUT_FAIL_N 5→8 (breaker触发更难)

## 数据采集 (6h窗口: ~2026-07-23 01:00-07:03 UTC)

### 总览

| 指标 | 数值 |
|---|---|
| 总请求 | 36 |
| 成功 | 16 |
| 失败 | 20 |
| 成功率 | 44.4% |

### 每模型

| 模型 | 总请求 | 成功 | 失败 | 成功率 | 平均延迟(ms) |
|---|---|---|---|---|---|
| dsv4p_nv | 14 | 2 | 12 | 14.3% | 2938 |
| glm5_2_nv | 22 | 14 | 8 | 63.6% | 27096 |

### 错误分布

| 模型 | 错误类型 | 数量 |
|---|---|---|
| dsv4p_nv | ATE (all_tiers_exhausted) | 12 |
| glm5_2_nv | ATE (all_tiers_exhausted) | 5 |
| glm5_2_nv | zombie_empty_completion | 3 |

### dsv4p_nv ATE详细

- 全部12个: duration 6-11ms, tier_attempts=0
- 集中在 01:37-03:07 UTC (NVCF function 74f02205 health-preempted)
- 07:00+ 无新dsv4p_nv请求，无法验证恢复

### glm5_2_nv ATE详细

| 类型 | 数量 | duration | 特征 |
|---|---|---|---|
| breaker OPEN instant-reject | 3 | 7ms | 0 tier_attempts, 381K input, big_input breaker OPEN |
| peer-fallback exhaust | 2 | 35s | 0 tier_attempts, 373K input, peer-fallback timeout |

### nv_gw环境

| 参数 | 值 |
|---|---|
| NVU_BIG_INPUT_COOLDOWN_S | 900 (R2288) |
| NVU_BIG_INPUT_FAIL_N | 5 → **8** |
| NVU_BIG_INPUT_THRESHOLD | 370000 |
| NVU_BIG_INPUT_MODELS | glm5_2_nv |
| TIER_COOLDOWN_S | 0 |
| KEY_COOLDOWN_S | 0 |
| NVU_TIER_BUDGET_DSV4P_NV | 160 |
| NVU_TIER_BUDGET_GLM5_2_NV | 200 |
| TIER_TIMEOUT_BUDGET_S | 275 |
| UPSTREAM_TIMEOUT | 24 |
| Container StartedAt | 2026-07-23T06:54:31Z (R2288重启后) |

## 根因分析

R2288将`NVU_BIG_INPUT_COOLDOWN_S`从2100→900后，breaker OPEN的阻断窗口从35min缩到15min。但**breaker触发阈值仍然太低**：`NVU_BIG_INPUT_FAIL_N=5`意味着仅需5次连续big_input失败就OPEN breaker。

在6h窗口内：
1. **3个glm5_2_nv ATE (7ms, 0 tier_attempts)** 是breaker OPEN instant-reject — 请求到达时breaker已OPEN，直接拒绝
2. 这些请求的input=381K，超过370K threshold → 被big_input逻辑拦截
3. 一旦breaker OPEN，**所有**glm5_2_nv大输入请求都被拒绝，直到breaker CLOSED
4. 即使在900s cooldown后breaker CLOSED，只要再有5次连续失败，breaker立即重新OPEN

**5次失败太容易触发**：glm5_2_nv的big_input请求本身成功率不高（NVCF大输入处理不稳定），5次连续失败很容易在短时间内累积。

## 修复

| 参数 | 旧值 | 新值 | 变更 |
|---|---|---|---|
| NVU_BIG_INPUT_FAIL_N | 5 | 8 | +3 (60%更难触发) |

**理由**: 将breaker触发阈值从5提升到8，需要8次**连续**big_input失败才OPEN breaker。这显著降低了breaker误触发概率，同时仍然在真正的持续失败场景下提供保护。配合R2288的900s cooldown，breaker OPEN后15min自动恢复。

**为什么单参数变更**: 只改`NVU_BIG_INPUT_FAIL_N`。R2288已优化cooldown，本轮提升触发阈值。dsv4p_nv不受影响（NVU_BIG_INPUT_MODELS=glm5_2_nv only）。iron law: only HM1。

## 执行

```bash
# 修改 compose 文件
python3 -c "
import os
path = '/opt/cc-infra/docker-compose.yml'
with open(path) as f:
    c = f.read()
c = c.replace('    - NVU_BIG_INPUT_FAIL_N=5\n', '    - NVU_BIG_INPUT_FAIL_N=8  # R2289 ...\n', 1)
with open(path, 'w') as f:
    f.write(c)
"

# 重启 nv_gw
docker compose -f /opt/cc-infra/docker-compose.yml up -d --no-deps --force-recreate nv_gw
```

## 验证

```
$ docker exec nv_gw env | grep NVU_BIG_INPUT_FAIL_N
NVU_BIG_INPUT_FAIL_N=8

$ curl -s -o /dev/null -w "%{http_code}" http://localhost:40006/health
200

$ docker inspect --format '{{.State.StartedAt}}' nv_gw
2026-07-23T07:26:22Z
```

## ⏳ 轮到HM1优化HM2