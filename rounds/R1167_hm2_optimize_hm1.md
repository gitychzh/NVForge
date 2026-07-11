# R1167: HM2→HM1 — NOP (false trigger, 35th chain of R1133, zombie-only, all params floor/optimal, NVCF content-filter not config-fixable)

## 触发判定
- cron 脚本输出: `"这是我提交的, 不触发"` → **误触发**
- 最新 commit: `5e037b4 R1166` (HM2 self-committed)
- 这是 R1133 zombie-only 触发链的第 35 次连续 NOP

## 数据摘要

| 窗口 | 总 | OK | Fail | SR |
|------|-----|-----|------|------|
| 6h | 37 | 12 | 25 | 32.4% |
| 2h | 8 | 4 | 4 | 50.0% |

- **全流量**: glm5_2_nv nv_integrate (37/37)
- **dsv4p_nv**: 0 请求 (零流量)
- **ms_gw**: 0 流量 (零 fallback)
- **fallback_occurred**: 全部 false (37/37)
- **nv_tier_attempts**: 仅 3 条 minor 429_integrate_rate_limit

## 错误分析

全部 25 个错误 = `zombie_empty_completion` (glm5_2_nv integrate):
- finish_reason=stop, content_chars=12 (<50 threshold), input_chars=164K-168K
- 每 30 分钟批量触发: NV-INTEGRATE-SUCCESS (first attempt) → NV-ZOMBIE-EMPTY (2-4s abort)
- 僵尸检测器正确发送 error SSE chunk 触发 openclaw fallback
- DB 中 fallback_occurred=f — nv_gw 内无跨 tier fallback (3model 单 tier 架构)
- NVCF glm5.2 模型侧行为: 返回 stop+12 chars 垃圾完成 — 非配置可修复

## 日志确认

```
[08:33:24] [NV-INTEGRATE-SUCCESS] tier=glm5_2_nv k5 succeeded on first attempt
[08:33:27] [NV-ZOMBIE-EMPTY] content_chars=12 < 50, input_chars=164969 >= 5000
[08:33:27] [NV-ZOMBIE-ERROR-CHUNK] sent finish_reason=content_filter error SSE chunk
```

模式: 100% first-key success, 无 tier_attempts 错误, 无 NV-TIER-FAIL, 无 NV-GLOBAL-COOLDOWN.
Zombie 检测在 2-4s 内快速 abort, 不消耗 BUDGET.

## 参数状态

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | optimal (R988) |
| TIER_TIMEOUT_BUDGET_S | 198 | optimal (R1088) |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor (R997) |
| NVU_EMPTY_200_FASTBREAK | 2 | settled (R1031) |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor (R1010) |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor (R631) |
| KEY_COOLDOWN_S | 25 | floor |
| TIER_COOLDOWN_S | 15 | settled (R1103) |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor (R657) |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | settled (R839) |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | settled (R839) |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | floor (R543) |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | stable (R922) |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | aligned with UPSTREAM=66 |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | settled (R830b) |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | settled (R830b) |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | settled (R1116) |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | settled (R1035) |
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 | settled (R1036) |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | settled |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | floor (R982) |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | floor (R982) |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | settled |

## 决策: NOP

零参数变更。zombie_empty_completion 是 NVCF glm5.2 模型侧行为 (finish_reason=stop + 12 chars content) — 非 nv_gw 配置可修复。僵尸检测器在 2-4s 内快速 abort, 不消耗预算。所有参数 at floor/optimal。dsv4p_nv 零流量 (无法验证)。ms_gw 零流量 (无 fallback 触发)。NV-TIER-FAIL 零出现 (无 tier 耗尽)。数据不支持任何配置变更。

铁律: 只改HM1不改HM2 ✓

## ⏳ 轮到HM1优化HM2