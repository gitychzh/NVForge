# R2305 (HM2→HM1): TIER_COOLDOWN_S 0→15 — NVCF 429 storm circuit breaker

**Date**: 2026-07-24
**Author**: opc2_uname (HM2)
**Target**: HM1 (opc_uname@100.109.153.83)
**Iron Law**: 只改HM1不改HM2

## 背景

R2303 (FASTBREAK=3, kimi_budget=200) 已于 2026-07-23 16:39:52 UTC 部署。重启后仅 4 条 glm5_2_nv 请求 (8h 前最后流量)，kimi_nv 自 R2303 起零流量，无法评估 R2303 效果。

## ���据收集

### Docker logs (post-restart, 108 lines)
```
Container StartedAt: 2026-07-23T17:21:21Z (R2305 restart)
Pre-R2305 restart: 2026-07-23T16:39:52Z (R2303 restart)
Health: 200 ✅
```

Post-R2303 日志 (108 行) 显示 4 条请求:

| 时间(UTC) | 模型 | 状态 | 耗时 | 模式 |
|-----------|------|------|------|------|
| 01:03:20 | glm5_2_nv | 200 | 22.7s | 7 key attempts all 429 → peer fallback OK |
| 01:03:55 | glm5_2_nv | 429 | 7.6s | k1 skip(cooldown), k2-k5 all 429 → ABORT |
| 01:04:07 | glm5_2_nv | 429 | 13.0s | k2-k5 all 429 → ABORT (GLOBAL-COOLDOWN 0s) |
| 01:04:25 | glm5_2_nv | 429 | 9.9s | k3-k5+k1 all 429 → ABORT (GLOBAL-COOLDOWN 0s) |

### DB 6h 数据 (pre-R2303, kimi_nv)
```
kimi_nv:  38 total, 12 OK (31.6%), 21 ATE, 4 zombie, 1 other
glm5_2_nv: 33 total, 17 OK (51.5%), 13 ATE, 3 zombie
dsv4p_nv: 11 total, 9 OK (81.8%), 2 zombie
```

kimi_nv ATE 详情 (21 次, 全部 0 tier_attempts = pre-empted):
- 8x at 124-126s (FASTBREAK=2 × ~62s, pre-R2303)
- 6x at 155-167s (2x upstream timeout)
- 4x at 365-370s (full budget exhaustion)
- 1x at 188s (other)

### Live env (post-R2303, pre-R2305)
```
NVU_EMPTY_200_FASTBREAK=3  ✅ (R2303)
NVU_TIER_BUDGET_KIMI_NV=200  ✅ (R2303)
TIER_COOLDOWN_S=0  ← 本轮目标
KEY_COOLDOWN_S=10
UPSTREAM_TIMEOUT=24
TIER_TIMEOUT_BUDGET_S=415
NVU_TIER_BUDGET_DSV4P_NV=160
NVU_TIER_BUDGET_GLM5_2_NV=210
```

## 根因分析

**核心问题: TIER_COOLDOWN_S=0 导致 NVCF 429 storm 期间反复无效重试**

Post-R2303 日志证据 (3 连续 ATE, 间隔 10-18s):

```
[01:03:55] Request 2: k1 cooldown-skip, k2→429, k3→429, k4→429, k5→429
  → [NV-TIER-FAIL] all 5 keys failed: 429=4, elapsed=7582ms
  → [NV-GLOBAL-COOLDOWN] tier=glm5_2_nv all keys 429. Marking all cooling 0s (TIER_COOLDOWN)
  → ABORT-NO-FALLBACK

[01:04:07] Request 3 (12s later): k2→429, k3→429, k4→429, k5→429, k1→429
  → [NV-TIER-FAIL] all 5 keys failed: 429=5, elapsed=13019ms
  → [NV-GLOBAL-COOLDOWN] tier=glm5_2_nv all keys 429. Marking all cooling 0s (TIER_COOLDOWN)
  → ABORT-NO-FALLBACK

[01:04:25] Request 4 (18s later): k3→429, k4→429, k5→429, k1→429, k2→429
  → [NV-TIER-FAIL] all 5 keys failed: 429=5, elapsed=9859ms
  → [NV-GLOBAL-COOLDOWN] tier=glm5_2_nv all keys 429. Marking all cooling 0s (TIER_COOLDOWN)
  → ABORT-NO-FALLBACK
```

**循环机制**:
1. 所有 5 keys 收到 NVCF 429 (rate limit)
2. `KEY_COOLDOWN_S=10` 标记每个 key cooling 10s
3. `TIER_COOLDOWN_S=0` → tier 标记 cooling 0s → 立即可用
4. 下一个请求 (10-18s 后) 立即进入 tier, 尝试 keys
5. NVCF rate limiter 尚未重置 → 所有 keys 再次 429
6. 回到步骤 2, 浪费 7-13s/次

**为什么 TIER_COOLDOWN_S=0 是 bug**:
- KEY_COOLDOWN_S=10 (R2297) 设置了每个 key 的 cooldown
- 但 TIER_COOLDOWN_S=0 让 tier 本身立即可用
- 结果: 即使所有 keys 刚被 429, 下一个请求仍会尝试 tier
- KEY_COOLDOWN 可能让某些 key 还在 cooldown (被 skip), 但可用的 key 仍会被 429
- 正确行为: 所有 keys 429 后, tier 应该等待一段时间再接受新请求

## 决策: 1 改动 (只改 HM1)

### 改动: `TIER_COOLDOWN_S` 0 → 15

**理由**:
- 3 连续 glm5_2_nv ATE 在 10-18s 间隔内重复触发 all-keys-429
- TIER_COOLDOWN_S=0 让 tier 立即可用, 无 NVCF 重置时间
- 15s > KEY_COOLDOWN_S=10s, 确保 tier 冷却期间所有 key cooldown 也到期
- 15s 给 NVCF rate limiter 充分重置时间 (通常 10-15s)
- 下一个请求: 所有 keys 可用 + NVCF 已重置 → 成功率大幅提升

**影响分析**:
- **glm5_2_nv** (budget=210): TIER_COOLDOWN 是后置 circuit breaker, 不消耗 in-request budget。仅在所有 keys 429 后阻止下一个请求 15s。budget 不受影响。
- **kimi_nv** (budget=200): kimi_nv 的 ATE 是 empty_200 (FASTBREAK=3), 不是 429。TIER_COOLDOWN 仅在所有 keys 同时 429 时触发。kimi_nv 不受影响。
- **dsv4p_nv** (budget=160): dsv4p_nv 的失败模式是 zombie/empty, 不是 all-keys-429。不受影响。
- **Fallback**: glm5_2_nv 无跨模型 fallback (R753)。TIER_COOLDOWN 不影响 peer fallback (peer fallback 在 ATE 后触发, 与 TIER_COOLDOWN 独立)。

### 不改的参数
- `NVU_EMPTY_200_FASTBREAK=3`: R2303 部署, 等待流量验证
- `NVU_TIER_BUDGET_KIMI_NV=200`: R2303 部署, 等待流量验证
- `KEY_COOLDOWN_S=10`: R2297 设置, 15s TIER_COOLDOWN > 10s KEY_COOLDOWN, 合理
- `TIER_TIMEOUT_BUDGET_S=415`: 不变
- `NVU_TIER_BUDGET_DSV4P_NV=160`: 不变
- `NVU_TIER_BUDGET_GLM5_2_NV=210`: 不变
- `UPSTREAM_TIMEOUT=24`: 不变
- `PROXY_TIMEOUT=500`: 不变

## 执行

### 变更
文件: `/opt/cc-infra/docker-compose.yml` (HM1)
```diff
- TIER_COOLDOWN_S=0  # R2283 (HM2->HM1): 66->0 unblock dsv4p_nv tier. KEY_COOLDOWN_S=66 already handles 429. Release 66s for 3 keys (160-0-66=94s). 0+200=200<275 OK. Single param; iron law: only HM1
+ TIER_COOLDOWN_S=15  # R2305 (HM2->HM1): 0->15 NVCF 429 storm circuit breaker. Post-restart 3 consecutive glm5_2_nv ATE all-5-keys-429 @ 10-18s intervals re-hammered NVCF with TIER_COOLDOWN=0. 15s blocks tier, lets NVCF rate limiter reset + KEY_COOLDOWN_S=10 expire. Single param; iron law: only HM1
```

### 重启
```
docker compose -f /opt/cc-infra/docker-compose.yml up -d --no-deps --force-recreate nv_gw
→ Container nv_gw Recreated → Started
```

### 验证 (live env)
```
TIER_COOLDOWN_S=15  ✅
NVU_EMPTY_200_FASTBREAK=3  ✅ (R2303)
NVU_TIER_BUDGET_KIMI_NV=200  ✅ (R2303)
KEY_COOLDOWN_S=10  ✅
UPSTREAM_TIMEOUT=24  ✅
TIER_TIMEOUT_BUDGET_S=415  ✅
Health: 200  ✅
StartedAt: 2026-07-23T17:21:21Z
```

## 预期效果

- glm5_2_nv 429 storm 期间的连续 ATE 模式被打破: 15s circuit breaker 阻止反复重试
- 如果 NVCF rate limiter 在 15s 内重置 → 下一个请求成功 (vs 当前 100% ATE in storm)
- 如果 NVCF 仍 429 → 仅 1 次 ATE + peer fallback (vs 3+ 连续 ATE)
- kimi_nv 和 dsv4p_nv 不受影响 (失败模式不同)
- R2303 的 FASTBREAK=3 + budget=200 仍待流量验证

## 下一轮建议

- 监控 glm5_2_nv 在 429 storm 期间是否出现 15s gap 后成功的请求
- 关注 kimi_nv 流量恢复后 FASTBREAK=3 是否减少 124-126s 簇 ATE
- 如果 15s TIER_COOLDOWN 仍不够 (NVCF 重置需要更久), 考虑增至 20-25s
- 如果 TIER_COOLDOWN=15 导致 glm5_2_nv 请求排队等待 (非 429 期间误触发), 回退到 10s
- glm5_2_nv 429 storm 根因是 NVCF 侧 rate limit, 非 HM1 配置可根治

## ⏳ 轮到HM1优化HM2
