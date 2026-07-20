# R2074 — hermes2 R18 巡检轮: NVCF 新一轮限流, SR 暴跌至 33.9%, Tier 429 翻倍 +113%

## 基本信息

- 时间: 2026-07-20 20:10 UTC+8
- 轮号: hermes2 R18 (仓库 R2074)
- 类型: 巡检轮 (不改代码)
- 上一轮: R2073 (hermes2 R17, SR 65.4%, Tier 429=23, breaker OPEN)

## 30min 数据 (20:00-20:30)

### nv_requests (dsv4p_nv mapped_model)

| status | count |
|--------|-------|
| 200 (成功) | 58 |
| 502 (all_tiers_exhausted) | 101 |
| 429 (gateway 429) | 12 |
| **总计** | **171** |
| **SR** | **33.9%** (R17: 65.4%, -31.5pp) |

### 错误分类

| error_type | count |
|------------|-------|
| all_tiers_exhausted | 111 |
| zombie_empty_completion | 2 |

### nv_tier_attempts (dsv4p_nv tier)

| error_type | count |
|------------|-------|
| 429_nv_rate_limit | 49 |

> 注意: tier_attempts 中 dsv4p_nv 零成功！49 条全是 429。所有 tier 尝试都被 NVCF 429 拒绝。

### Tier 429 按 key 分布

| nv_key_idx | 429 count |
|------------|-----------|
| 0 | 4 |
| 1 | 9 |
| 2 | 12 |
| 3 | 15 |
| 4 | 9 |
| **总计** | **49** |

### fallback 率

- 30min fallback 计数: 139 (R17: 150, -7.3%)
- breaker: PRIMARY-BREAKER-SKIP-STREAM 持续 OPEN
- 有一条 PRIMARY-FAIL-STREAM: "nv_gw 流式 server_5xx status=429 after 383ms, 切 fallback: upstream 429"

### 容器状态

- nv_gw: Up 50 min
- hm4104: Up 4 hours
- ms_gw: Up 3 days
- curl /health: OK
- KEY_COOLDOWN_S=180 ✓

## 核心判断: NVCF 新一轮限流，非僵持，是恶化

**R17 → R18 对比:**

| 指标 | R17 | R18 | 变化 |
|------|-----|-----|------|
| 总请求 | 26 | 171 | +558% |
| SR | 65.4% | 33.9% | -31.5pp |
| all_tiers_exhausted | 9 | 111 | +102 |
| Tier 429 | 23 | 49 | +113% |
| fallback | 150 | 139 | -7.3% |

**诊断:**

1. Tier 429 从 23 翻倍到 49 (+113%)，且 dsv4p_nv tier 的 tier_attempts 零成功 —— 所有 tier 尝试都被 NVCF 429 拒绝，5 把 key 全部被限流。
2. SR 从 65.4% 暴跌到 33.9% — 这是 429 爆炸的直接后果。502×101 = all_tiers_exhausted，没有一把 key 能通。
3. 这不是 nv_gw 配置问题。KEY_COOLDOWN_S=180 已经非常保守（R10 试过 240 也没改善）。根因是 **NVCF 上游收紧了对 dsv4p 的 rate limit**。
4. breaker OPEN 是正确行为 — 在 100% 429 的情况下，跳过 primary 直走 ms_gw 是唯一合理选择。
5. 总请求量从 26 跳到 171 (+558%) — 可能是 R17 的 breaker OPEN 导致更多请求被跳过（但不影响 tier 成功率，因为 tier 层的 429 是独立于 breaker 的）。

**为什么 R17 巡检建议的"手动重启 nv_gw"不适用:**

- 重启 nv_gw 只会短暂清除 breaker，但 NVCF 429 仍在，breaker 会立刻重新 OPEN。
- 重启无法解决 NVCF 上游限流 — 那是 NVCF 服务端行为，不在 nv_gw 可调范围内。
- R10 已验证 KEY_COOLDOWN_S=240 不能改善 429 — 更长冷却时间无效。

## 本轮改动

**无。巡检轮，不改代码。**

原因: 根因是 NVCF 上游限流，不在 nv_gw 可调旋钮范围内。调整 KEY_COOLDOWN_S 或 TIER_COOLDOWN_S 已被 R10-R11 验证无效。重启 nv_gw 无法清除 NVCF 服务端 rate limit。

## 下一步 (R19)

1. 观察 NVCF 限流是否自行缓解（Tier 429 能否从 49 回落）
2. 如果 Tier 429 持续 > 30，考虑联系 NVCF 侧确认 dsv4p function 的 rate limit 配额
3. 如果 Tier 429 回落到 < 20，SR 应自然回升到 60%+，届时 breaker 可能自动恢复
4. 继续巡检，不主动干预 — 上游限流期间任何 nv_gw 侧改动都是无效的

## 当前参数快照 (不变)

```
nv_gw:
  KEY_COOLDOWN_S=180
  TIER_COOLDOWN_S=180
  TIER_TIMEOUT_BUDGET_S=180
  UPSTREAM_TIMEOUT=90
  dsv4p_nv function_id=74f02205
  dsv4p_nv strip_params=[reasoning_effort, stream_options, thinking]
hm4104:
  PRIMARY_HEADER_TIMEOUT=180
  CIRCUIT_FAILURE_THRESHOLD=8
  CIRCUIT_OPEN_S=60
```