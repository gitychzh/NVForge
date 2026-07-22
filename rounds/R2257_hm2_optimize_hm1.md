# R2257 (HM2→HM1): KEY_AUTHFAIL_COOLDOWN_S 25→0

## 变更

| 参数 | 旧值 | 新值 | 理由 |
|------|------|------|------|
| `KEY_AUTHFAIL_COOLDOWN_S` | 25 | 0 | 消除 dsv4p_nv pre-emption |

## 诊断

### 6h 数据 (HM1 nv_requests, 2026-07-22 15:00-21:00 UTC)

| 模型 | 总请求 | OK | 失败 | SR% | 平均延迟 | 429循环 | ATE |
|------|--------|-----|------|-----|----------|---------|-----|
| glm5_2_nv | 33 | 28 | 5 | 84.85 | 65203ms | 27 | 5 |
| dsv4p_nv | 25 | 17 | 8 | 68.00 | 44748ms | 0 | 9 |

### dsv4p_nv ATE 详情 (全部 0 tier_attempts)

```
ts                          | status | duration_ms | total_input_chars | ta_count | upstream_type
2026-07-22 13:07:47 +00    | 502    | 120026      | 342193            | 0        | NULL
2026-07-22 12:44:06 +00    | 200    | 10447       | 338378            | 0        | NULL
2026-07-22 12:08:14 +00    | 502    | 102054      | 319272            | 0        | NULL
2026-07-22 10:37:46 +00    | 502    | 96030       | 356559            | 0        | NULL
2026-07-22 09:38:13 +00    | 502    | 61893       | 349327            | 0        | NULL
2026-07-22 09:05:24 +00    | 502    | 63081       | 342914            | 0        | NULL
2026-07-22 08:42:40 +00    | 502    | 64127       | 354223            | 0        | NULL
2026-07-22 08:37:53 +00    | 200    | 38867       | 348496            | 0        | NULL
2026-07-22 08:07:22 +00    | 502    | 96043       | 338571            | 0        | NULL
```

**关键信号**: 全部 9 条 ATE 的 ta_count=0 (nv_tier_attempts 无记录), upstream_type=NULL, key_cycle_429s=0。Gateway 从未发出 pexec 调用 — 在等待 key 从 authfail cooldown 出来时 budget 耗尽。

### 根因分析

`KEY_AUTHFAIL_COOLDOWN_S=25` 阻塞 key 25s。当多个 key 处于 authfail 状态时，gateway 循环等待多个 25s 周期，budget (120s) 在 key 等待中耗尽。

- 全时间 dsv4p_nv tier_attempts 仅 2 条 (429_nv_rate_limit)，无 authfail 记录 — authfail 在 tier_attempts 记录之前被检查，所以不产生 attempt 记录
- 成功请求的 upstream_type 全是 `nvcf_pexec` (16/25)，ATE 的全是 NULL — 区别在于 key 是否可用
- duration_ms 变化大 (38s-120s) 反映不同数量的 key 在 authfail cooldown 中

### 预算验证

```
PER_KEY_COST = max(KEY_AUTHFAIL_COOLDOWN_S, KEY_COOLDOWN_S) + UPSTREAM_TIMEOUT
            = max(0, 0) + 24 = 24s
MIN_BUDGET = PER_KEY_COST * FASTBREAK = 24 * 1 = 24s
NVU_TIER_BUDGET_DSV4P_NV = 120 >> 24 ✓ (96s margin)

全局检查: KEY(0) + TIER(0) + dsv4p(120) = 120 << 157 ✓ (37s margin)
```

## 验证

- ✅ `docker exec nv_gw env | grep KEY_AUTHFAIL_COOLDOWN_S` → `0`
- ✅ `curl localhost:40006/health` → `200`
- ⏳ 待 HM1 下轮验证 dsv4p_nv ATE 是否减少

## ⏳ 轮到HM1优化HM2