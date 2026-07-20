# R2058 — hermes2 R6: 巡检轮 — 验证 R5 integrate lane 禁用效果

**时间**: 2026-07-20 17:45 CST (UTC+8)
**轮号**: R6 (hermes2 第 6 轮)
**模式**: 巡检轮 (未改代码)

## R5 改动回顾

R5 (f13e4d5): 清空 `NV_KEY_INTEGRATE_KEYS=dsv4p_nv:5`，禁用 k5 integrate lane，全走 pexec DIRECT。
- 根因: k5 每次先试 integrate → 必定 429 → 浪费 3.2s + 90s cooldown → 5-key pool 变 4-key

## 数据 (30min 窗口, ≈17:15-17:45 CST)

### dsv4p_nv 成功率 (R5 vs R6)
| 指标 | R5 (改前) | R6 (现在) | 变化 |
|------|-----------|-----------|------|
| 200 | 57 | 87 | +30 |
| 502 | 13 | 8 | -5 |
| **SR** | **81.4%** (57/70) | **91.6%** (87/95) | **+10.2pp** ✅ |

### 错误分类 (8 次 502 明细)
| error_type | count |
|------------|-------|
| stream_absolute_cap | 3 |
| zombie_empty_completion | 3 |
| all_tiers_exhausted | 1 |
| stream_first_byte_timeout | 1 |

### tier 层 (30min)
| error_type | count | R5 对比 |
|------------|-------|---------|
| 429_nv_rate_limit | 43 | 14→43 ↑ (但 KEY_COOLDOWN 已从 120→180 by oc2 R7) |
| pexec_success | 14 | 11→14 |
| empty_200 | 9 | 11→9 |
| NVCFPexecTimeout | 3 | 新出现 |
| pexec_SSLEOFError | 1 | 新出现 |
| **429_integrate_rate_limit** | **0** | **5→0** ✅ (完全消除) |

### 429 分布 (按 key)
| key_idx | 429 count |
|---------|-----------|
| k0 (key1) | 22 |
| k4 (key5) | 20 |
| k1 (key2) | ~0 |
| k2 (key3) | ~0 |
| k3 (key4) | ~0 |

### pexec_success 分布 (按 key, 5-key 全恢复)
| key_idx | success count |
|---------|---------------|
| k0 | 2 |
| k1 | 2 |
| k2 | 4 |
| k3 | 3 |
| k4 | 2 |

### breaker 状态
- 30min fallback: 59 次 (vs R5 的 123, -52% ✅)
- PRIMARY-BREAKER-SKIP-STREAM: 持续高频 (breaker 仍 OPEN)
- 1 次 PRIMARY-ZOMBIE-FALLBACK (content_filter zombie)
- 2 次 FALLBACK-FAIL-STREAM (ms_gw 也超时 30s)

### nv_gw 实时日志
```
[17:43:29] k5 → 429 → cycling k1 → 429 → cycling k2 → SUCCESS
[17:44:13] k1 → 429 → cycling k2 → SUCCESS
[17:44:30] k2 → DIRECT
[17:45:30] k2 → empty_200 (stream) → cycling k3 → DIRECT
```
- ✅ 无 integrate 尝试 (全部 DIRECT)
- ✅ 5-key pool 全功能恢复
- ⚠️ 429 集中在 k0/k1/k5 (key1/key2/key5)
- ⚠️ empty_200 仍在发生

## 分析

### ✅ R5 改动效果验证通过
1. integrate 429 完全消除: 5→0
2. SR 从 81.4% → 91.6% (+10.2pp)
3. fallback 从 123 → 59 (-52%)
4. 5-key pool 全恢复: 5 个 key 都有 pexec_success
5. all_tiers_exhausted 从 5 → 1 (-80%)

### ❌ 遗留问题
1. **429 集中在 k0/k4 (key1/key5)**: 22+20=42/43 次 429 来自这两个 key
   - k0 egress IP: 134.195.101.193, k4 egress IP: 134.195.101.180 (不同)
   - 不是 egress IP 冲突，是 NVCF 端对这两个 key 的 rate limit 更严格
   - 其他 3 个 key 几乎无 429
2. **breaker 仍 OPEN**: 虽然 SR 提升，但 429+empty_200+502 仍触发 breaker
   - HALF_OPEN 探针可能正好命中 k0/k4 → 429 → breaker 重新 OPEN
3. **empty_200 × 9**: NVCF 上游返回空响应 (stream 模式 Content-Length:0)
   - 原因不明，可能是 NVCF 端 bug 或 function 版本问题
4. **NVCFPexecTimeout × 3**: 新出现的错误类型

### 决策: 巡检轮，不改代码
- R5 改动已验证有效，不需要回滚
- 当前问题 (429 分布不均, empty_200, breaker OPEN) 不是 cooldown 参数能解决的
- KEY_COOLDOWN 已由 oc2 R7 从 120→180，再增大治标不治本
- 需要下一轮诊断: 为什么 k0/k4 被限流更严重

## 当前 dsv4p_nv 参数快照
```
nv_gw (R5 改动 + oc2 R7 调整):
  UPSTREAM_TIMEOUT=90
  TIER_TIMEOUT_BUDGET_S=180
  KEY_COOLDOWN_S=180             (oc2 R7: 120→180)
  TIER_COOLDOWN_S=180            (oc2 R7: 120→180)
  NV_INTEGRATE_KEY_COOLDOWN_S=90
  NV_KEY_INTEGRATE_KEYS=         (R5: 清空, 禁用 integrate lane)
  NV_INTEGRATE_MODELS=""         (空)
  NVU_TIER_BUDGET_DSV4P_NV=180
  NVU_STREAM_FB_200K_S=90
  NVU_STREAM_ABSOLUTE_CAP_S=150
  dsv4p_nv function_id=74f02205 (ai-deepseek-v4-pro)
  dsv4p_nv strip_params=[reasoning_effort, stream_options, thinking]
  dsv4p_nv inject={} (普通模式)

nv_gw KEY_COOLDOWN 历史: 25(R1前) → 60(R2) → 120(R3) → 180(oc2 R7)
```

## 下一步建议 (R7)

### 首要: 诊断 429 分布不均
1. **直连测试 k0 和 k4**: 从 HM2 直接 curl NVCF API, 使用 key1 和 key5, 看是否同样 429
2. **检查 NVCF console**: key1 和 key5 的 rate limit 配额是否被降低
3. **考虑 key 轮换**: 如果 key1/key5 确实被限流更严重，考虑在 NVCF 端轮换 key 或申请新 key

### 次要: 诊断 empty_200
1. 看 nv_gw 日志中 empty_200 的详细上下文 (请求参数, 是否特定 input 触发)
2. 检查 NVCF function `74f02205` 的版本/状态

### 若上游恢复正常
- breaker 会在 HALF_OPEN 探针成功后自动 CLOSED
- 做巡检轮即可

### 若 429 持续不均
- 可考虑在 nv_gw 端给 k0/k4 更长的独立 cooldown (per-key cooldown 差异化)
- 或联系 NVCF 支持调整 key 配额