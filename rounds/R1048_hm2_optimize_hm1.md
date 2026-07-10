# R1048: HM2→HM1 — NOP (false trigger, double-dispatch, 100% 6h SR, 0 post-restart errors)

## 1. 触发分析

- **cron 脚本输出**: "这是我提交的, 不触发"
- **最新 commit author**: opc2_uname (HM2)
- **HM2 git log**: R1047 (NOP) 为最新 — pre-run script 已提交
- **HM1 本地 git log**: R821 (227 轮落后)
- **判定**: 双派遣 false trigger。R1047 已由 pre-run script 提交，symlink 已指向 R1047，cron 仍再次派遣。

## 2. 数据收集 (改前必有数据)

| 窗口 | 请求 | OK | 失败 | SR |
|------|------|----|------|----|
| 6h | 35 | 35 | 0 | 100.0% |
| 1h | 9 | 9 | 0 | 100.0% |

### 1h 按 tier

| tier_model | 请求 | OK | 失败 | SR |
|------------|------|----|------|----|
| glm5_2_nv | 9 | 9 | 0 | 100.0% |

### 1h 延迟 (200 OK)

| tier_model | avg_ms | min_ms | max_ms | cnt |
|------------|--------|--------|--------|-----|
| glm5_2_nv | 8519 | 4835 | 11495 | 9 |

### nv_tier_attempts (6h)

0 rows — 无错误。

### nv_requests 错误 (6h)

0 rows — 无失败请求。

### 容器状态

- nv_gw: Up 2 hours (healthy)
- ms_gw: Up 7 hours (healthy)

### 日志摘要

- 最近 30 行: 全部 glm5_2_nv integrate first-attempt success (7/7)
- 1 次 SSLEOFError k2 (5002ms) → 自动 cycle 到 k3 → 成功 — 正常自愈
- 无 NV-TIER-FAIL, 无 ATE, 无 error/warn

## 3. 当前参数

| 参数 | 值 | 状态 |
|------|----|------|
| UPSTREAM_TIMEOUT | 66 | floor |
| TIER_TIMEOUT_BUDGET_S | 110 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| KEY_COOLDOWN_S | 25 | floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| TIER_COOLDOWN_S | 18 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | optimal |
| NVU_EMPTY_200_FASTBREAK | 2 | code-bug (threshold=1 in log) |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | optimal |
| NVU_FORCE_STREAM_UPGRADE | 0 | optimal |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | floor |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | optimal |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.10 | optimal |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | optimal |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | optimal |

## 4. ms_gw 检查

- ms_gw: Up 7 hours, 健康, 无错误
- 参数: EMPTY_200_FASTBREAK_THRESHOLD=3, KEY_COOLDOWN_S=60, UPSTREAM_TIMEOUT=300
- 无优化空间 — 所有参数合理

## 5. 决策: NOP

- 所有参数在最优/floor
- 6h 100% SR, 0 错误
- nv_tier_attempts 0 rows
- 日志干净: 仅一次 SSLEOFError 自愈
- ms_gw 无优化空间
- **铁律: 只改 HM1 不改 HM2**

Zero param; iron rule: only change HM1 never HM2.

## 6. 触发类型

False trigger (double-dispatch). R1047 已由 pre-run script 提交，symlink 已正确。cron 重复派遣。

## ⏳ 轮到HM1优化HM2