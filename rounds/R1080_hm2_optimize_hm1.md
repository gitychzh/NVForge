# HM2 Optimize HM1 — Round R1080

## 触发分析

- **Cron 脚本输出**: `这是我提交的, 不触发` → FALSE TRIGGER (double-dispatch)
- **最新 commit**: 0661be1 (R1079, author=opc2_uname, HM2)
- **HM1 git log**: fbf0e43 (R821) — 落后 259 轮
- **判定**: 自提交误触发，非真实 HM1→HM2 回合。R1079 symlink已正确→双触发模式。

## 数据收集（改前必有数据）

### 6h DB 全景
- **总量**: 60 req / 52 OK (86.7%) / 8 fail
- **dsv4p_nv**: 4/4 ATE (100% 失败), avg 88,369ms, all_tiers_exhausted, NVCF 504 gateway-level (外部)
- **glm5_2_nv**: 56/52 OK (92.9%), avg 26,659ms, 4 NVStream_TimeoutError
- **nv_tier_attempts**: 2 rows — glm5_2_nv IntegrateRemoteDisconnected (1×20,284ms) + IntegrateTimeout (1×90,566ms)
- **fallback_occurred**: 0/60 (无 fallback 触发)
- **ms_gw**: 10 total, 0 OK — BrokenPipeError code-level relay（非配置可修）

### 与 R1079 对比
| 指标 | R1079 | R1080 | Δ |
|------|-------|-------|---|
| 总量 | 59/51(86.4%) | 60/52(86.7%) | +1req/+0.3pp |
| dsv4p_nv ATE | 4/4, 88,369ms | 4/4, 88,369ms | 完全相同 |
| glm5_2_nv SR | 51/55(92.7%) | 52/56(92.9%) | +0.2pp |
| nv_tier_attempts | 2 rows | 2 rows | 完全相同 |
| ms_gw | 10/0 OK | 10/0 OK | 完全相同 |

### 容器状态
- **nv_gw 重启**: 2026-07-10 09:47 UTC，已运行8h+，健康
- **最新日志**: 18:03 glm5_2_nv integrate k1 成功 (3s)
- **env 配置**: 与 R1079 完全相同，所有参数无变化

### 当前配置参数 (nv_gw env)
| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | R988, buffer=3.4s ✓ |
| TIER_TIMEOUT_BUDGET_S | 132 | R1071, 132=66+66 |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | R1078, 对齐UPSTREAM |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | 稳定 |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | 稳定 |
| NVU_EMPTY_200_FASTBREAK | 2 | R1031 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | 稳定 |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | 防御性 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | 对齐 UPSTREAM |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.10 | R982 |
| TIER_COOLDOWN_S | 18 | floor |
| KEY_COOLDOWN_S | 25 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |

## 决策: NOP

### 为什么 NOP
1. **数据与 R1079/R1078 几乎完全一致**: 60req/52OK(86.7%) vs 59req/51OK(86.4%)，仅+1req
2. **dsv4p_nv ATE 根因是 NVCF 504 外部**: all_tiers_exhausted，非本地配置可修
3. **glm5_2_nv 持续稳定**: 92.9% SR，NVStream_TimeoutError 4次为网络抖动
4. **ms_gw BrokenPipeError**: 代码级 relay 问题，非配置可修
5. **所有参数已在 optimal/floor**: UPSTREAM=66 buffer=3.4s, BUDGET=132, dsv4p budget=66, FASTBREAK=1/1/2, COOLDOWN=floor
6. **无新错误类型，无 auth-fail，无 key_cycle_429s 异常**

### 次级优化检查
- ms_gw: EMPTY_200_FASTBREAK_THRESHOLD=3 (已 floor)，ALL_EXHAUSTED_COOLDOWN_S=30，KEY_COOLDOWN_S=60 — 无优化空间
- ds scatter: 无 scatter 问题
- HM1 git log 仍停在 R821（259轮落后）— HM1 未执行任何优化回合

## 参数变更: 零

## 铁律确认
- ✅ 只改 HM1 不改 HM2
- ✅ 改前必有数据
- ✅ 少改多轮
- ✅ 铁律: 只改 HM1 不改 HM2

## ⏳ 轮到HM1优化HM2
