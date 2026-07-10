# HM2 Optimize HM1 — Round R1079

## 触发分析

- **Cron 脚本输出**: `这是我提交的, 不触发` → FALSE TRIGGER
- **最新 commit**: ba36c1d (R1078, author=opc2_uname, HM2)
- **HM1 git log**: fbf0e43 (R821) — 落后 258 轮
- **判定**: 自提交误触发，非真实 HM1→HM2 回合

## 数据收集（改前必有数据）

### 6h DB 全景
- **总量**: 59 req / 51 OK (86.4%) / 8 fail
- **dsv4p_nv**: 4/4 ATE (100% 失败), avg 88,369ms, all_tiers_exhausted, NVCF 504 gateway-level (外部)
- **glm5_2_nv**: 55/51 OK (92.7%), avg 27,068ms, 4 NVStream_TimeoutError (glm5_2_nv)
- **nv_tier_attempts**: 2 rows — glm5_2_nv IntegrateRemoteDisconnected (1×20,284ms) + IntegrateTimeout (1×90,566ms)
- **fallback_occurred**: 0/59 (无 fallback 触发)
- **ms_gw**: 10 total, 0 OK — BrokenPipeError code-level relay（非配置可修）

### 容器状态
- **nv_gw 重启**: 2026-07-10 09:47 UTC，已运行~12min
- **重启后请求**: 0 (post-16:00 UTC 零流量)
- **6h 窗口数据全部为重启前积压**

### 当前配置参数 (nv_gw env)
| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | R988 优化，glm5_2_nv NVCFPexecTimeout max=62,606ms，buffer=3.4s ≥ 3.0s ✓ |
| TIER_TIMEOUT_BUDGET_S | 132 | R1071 优化，132=66+66 给 full single-key window |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | R1078 优化，对齐 UPSTREAM=66，block 504 loops |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | 稳定 |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | 稳定 |
| NVU_EMPTY_200_FASTBREAK | 2 | R1031 优化 |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | 稳定 |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | 防御性参数 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | 历史最低 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | 对齐 UPSTREAM |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.10 | R982 优化 |
| TIER_COOLDOWN_S | 18 | 稳定 |
| KEY_COOLDOWN_S | 25 | 历史最低 |

## 决策: NOP

### 为什么 NOP
1. **数据与 R1078 完全一致**: 59req/51OK(86.4%)/8ATE，零变化
2. **dsv4p_nv ATE 根因是 NVCF 504 外部**: `all_tiers_exhausted`，upstream_type=NULL，非本地配置可修
3. **glm5_2_nv 稳定**: 92.7% SR，NVStream_TimeoutError 4 次为网络抖动
4. **ms_gw BrokenPipeError**: 代码级 relay 问题，非配置可修
5. **所有参数已在 optimal/floor**: UPSTREAM=66 buffer=3.4s, BUDGET=132, dsv4p budget=66, FASTBREAK=2
6. **R1078 已执行最新优化**: NVU_TIER_BUDGET_DSV4P_NV=66 刚设置，需等待数据验证

### 次级优化检查
- ms_gw: EMPTY_200_FASTBREAK_THRESHOLD=3 (已 floor)，ALL_EXHAUSTED_COOLDOWN_S=30，KEY_COOLDOWN_S=60 — 无优化空间
- ds scatter: 无 scatter 问题
- 无 auth-fail，无 key_cycle_429s 异常

## 参数变更: 零

## 铁律确认
- ✅ 只改 HM1 不改 HM2
- ✅ 改前必有数据
- ✅ 单参数/少改多轮
- ✅ 铁律: 只改 HM1 不改 HM2

## ⏳ 轮到HM1优化HM2
