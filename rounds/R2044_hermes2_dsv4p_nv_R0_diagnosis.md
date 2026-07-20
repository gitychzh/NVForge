# R2044 — hermes2 dsv4p_nv R0 首轮诊断 (不改代码)

> 日期: 2026-07-20 13:30-13:50 CST
> 代理: hermes2 (HM2)
> 轮类型: 首轮诊断 (R0), 只拉数据定基线, 不改代码
> 前轮: R2043 (HM2→HM1, KEY=TIER 60→75)

## 数据窗口

### 30min dsv4p_nv (nv_requests 表)
| status | error_type | count |
|--------|-----------|-------|
| 200 | - | 9 |
| 502 | stream_first_byte_timeout | 3 |
| 502 | zombie_empty_completion | 1 |

**30min SR = 9/13 = 69.2%** (低于 85% 阈值 → 诊断模式, 非 NOP)

### 24h dsv4p_nv (nv_requests 表)
| status | error_type | count |
|--------|-----------|-------|
| 200 | - | 581 |
| 502 | all_tiers_exhausted | 34 |
| 502 | stream_first_byte_timeout | 23 |
| 502 | zombie_empty_completion | 3 |
| 502 | NVStream_IncompleteRead | 2 |

**24h SR = 581/643 = 90.4%** (大体健康, 但 30min 窗口恶化)

### 24h tier 级错误 (nv_tier_attempts, dsv4p_nv)
| error_type | count |
|-----------|-------|
| 500_nv_error | 18 |
| IntegrateTimeout | 8 |
| IntegrateRemoteDisconnected | 4 |
| empty_200 | 1 |

### hm4104 fallback 率 (30min)
- 总 fallback/FALLBACK 事件: **110**
- PRIMARY-BREAKER-SKIP-STREAM: **56** (breaker OPEN 或 fallback 冷却)
- CONTENT_FILTER_ZOMBIE / PRIMARY-ZOMBIE-FALLBACK: **4**
- PRIMARY-STREAM-OK / PRIMARY-NONSTREAM-OK: **0** (无 primary 成功)
- FALLBACK-FAIL-STREAM (ms_gw timeout): **1**

### nv_gw breaker 状态
- nv_gw 日志中 breaker 状态: **CLOSED** (在 glm5_2_nv ms_fb 路径中记录)
- 但 hm4104 侧 PRIMARY-BREAKER-SKIP 56 次 → hm4104 自己的 breaker 对 dsv4p_nv 是 OPEN 或冷却中

## 诊断

### 核心发现: 三层现象

1. **nv_gw 层 (40006)**: dsv4p_nv 本身能工作。30min 9 次成功, 多 key (k2/k3/k4/k5) 首试即成功。nv_gw breaker CLOSED。

2. **hm4104 层 (4104)**: hm4104 自己的 breaker 对 dsv4p_nv 已 OPEN 或处于冷却, 30min 内 56 次 PRIMARY-BREAKER-SKIP, 0 次 primary 成功。所有 hermes2 请求被 hm4104 直接甩到 ms_gw。

3. **根因链**: hermes2 的请求 input 大 (本 session 的 system prompt + CLAUDE.md + STATE.md ≈ 160k chars), 触发 nv_gw 的 stream_first_byte_timeout (60s 首字节 deadline), hm4104 记录失败 → breaker 累积 → OPEN → 所有后续 hermes2 请求走 ms_gw。

### 具体证据

nv_gw 日志 (13:45:35):
```
[NV-STREAM-FIRST-BYTE-DEADLINE] (dsv4p_nv) passthrough first-byte deadline 60.0s exceeded
(input_chars=160997), breaking (upstream 200-then-hang)
```

这是 hermes2 自己的请求 (160k input)。NVCF 返回 200 但无首字节 → 60s deadline 触发 → nv_gw 返回 content_filter SSE chunk → hm4104 计为失败。

### 关键矛盾

- nv_gw 直接看: dsv4p_nv 30min SR 69.2% (9/13), 有成功有失败
- hm4104 看: 0 primary 成功, 56 次 breaker skip
- 原因: 30min 内 nv_gw 的 9 次成功来自 opencode/openclaw 等小 input agent, 不是 hermes2。hermes2 的大 input 请求全被 hm4104 breaker 拦截。

### 配置现状

- NV_INTEGRATE_MODELS="" (空, env 覆盖默认值, dsv4p_nv 走 pexec DIRECT)
- R838B per-key lane: dsv4p_nv:5 (k5 先试 integrate)
- NVU_FORCE_STREAM_EXCLUDE_MODELS 包含 dsv4p_nv (强制非流式)
- UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=180
- dsv4p_nv 首字节 deadline = 60s (UPSTREAM_TIMEOUT 的 passthrough 模式)

### 判定: 介入条件满足

30min SR 69.2% < 85%, 且 hm4104 breaker 对 dsv4p_nv OPEN 导致 hermes2 完全无法走 primary。这是系统性问题, 非偶发。

## 改动

无 (首轮诊断, 不改代码)

## 验证

无代码改动, 无需验证。

## 下一步建议 (R1)

1. **首要目标**: 让 hm4104 breaker 对 dsv4p_nv 恢复 CLOSED, 让 hermes2 能走 primary。
2. **方案 A (推荐)**: 等待 hm4104 breaker 自然冷却恢复 (冷却时间未知, 需查 hm4104 配置), 然后下一轮用小型 prompt 测试 (hermes chat -q "hello" --yolo 小 input) 确认链路通。
3. **方案 B**: 如果 breaker 冷却时间过长, 考虑调大 nv_gw 的 stream_first_byte_deadline (当前 60s) 或 UPSTREAM_TIMEOUT (当前 66s), 让大 input 有更多首字节时间。但 160k input 的 dsv4p 普通模式首字节实测 1.8-4.9s, 60s 应该充足 → 问题可能在 NVCF 侧对超大 input 的处理 (200-then-hang)。
4. **方案 C**: 调查 hm4104 的 breaker 配置, 确认 fail_n / cooldown 参数, 必要时调高容错。
5. **数据收集**: 下一轮先检查 hm4104 breaker 是否已恢复, 再决定是否改参数。

## 参数快照 (本轮)
```
KEY_COOLDOWN_S=25
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_FORCE_STREAM_UPGRADE=0
NVU_BIG_INPUT_FAIL_N=1
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=180
NV_INTEGRATE_KEY_COOLDOWN_S=90
TIER_COOLDOWN_S=25
NVU_BIG_INPUT_COOLDOWN_S=180
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=0
NV_INTEGRATE_MODELS="" (空, dsv4p_nv 走 pexec DIRECT)
NVU_FORCE_STREAM_EXCLUDE_MODELS=dsv4p_nv,glm5_2_nv (dsv4p 强制非流式)
dsv4p_nv function_id=74f02205 (ai-deepseek-v4-pro, ACTIVE)
dsv4p_nv strip_params=[reasoning_effort, stream_options, thinking]
dsv4p_nv inject={} (普通模式)
```