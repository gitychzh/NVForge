# HM2 Optimize HM1 — Round R1464

**日期**: 2026-07-15 22:00 UTC
**性质**: NOP (false trigger, double-dispatch, 44th chain of R1395)
**铁律**: 只改HM1不改HM2

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit `a938105` author = opc2_uname (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发/双重派遣 (44th chain of R1395)
- HM1 git log 停留在 R1206 (257 轮落后) — 无实际 HM1 变更

## 2. 数据采集

### 容器状态
- nv_gw: Up 52 minutes (healthy), 重启于 2026-07-15T13:09:29Z
- ms_gw: Up 14 hours (healthy)
- logs_db: Up 14 hours (healthy)
- Compose md5: 45c1f2840ddd9e7e52dfc054f1c02eb4

### 6h 整体 (nv_requests)
- 41req/18OK/23err = **43.9% SR**

### 错误分布
| 错误类型 | 数量 | 模型分布 | 平均延迟 |
|---------|------|---------|---------|
| zombie_empty_completion | 13 | glm5_2_nv×11, dsv4p_nv×2 | 11.6s / 47.1s |
| all_tiers_exhausted | 10 | dsv4p_nv×9, glm5_2_nv×1 | 70.6s / 187.2s |

### Post-restart (13:09Z→now)
- 5req/3OK/2zombie = **60.0% SR**, 0 ATE
- glm5_2_nv: 3req/2OK 66.7% (1 zombie)
- dsv4p_nv: 2req/1OK 50.0% (1 zombie)

### 按模型 (6h)
| 模型 | 请求 | OK | SR% | 平均延迟 |
|------|------|----|-----|---------|
| glm5_2_nv | 27 | 15 | 55.6% | 18.4s |
| dsv4p_nv | 14 | 3 | 21.4% | 62.7s |

### 每时SR
| 小时 | 请求 | OK | SR% |
|------|------|----|-----|
| 08:00 | 5 | 2 | 40.0% |
| 09:00 | 8 | 4 | 50.0% |
| 10:00 | 6 | 2 | 33.3% |
| 11:00 | 6 | 2 | 33.3% |
| 12:00 | 7 | 3 | 42.9% |
| 13:00 | 9 | 5 | 55.6% |

### fallback
- fallback_occurred=false: 41req/18OK (100% of requests)
- ms_gw: 25req/21OK = **84.0% SR** (backup healthy)
- 0 tier_attempts — 键池干净，无 429 循环

### 日志
- Post-restart: 5 NV-REQ (3 success, 2 zombie), 0 ATE
- Zombie: NVCF content-filter — 输入 218K chars → 输出 14-28 chars, finish_reason=stop
- NV-ZOMBIE-ERROR-CHUNK 正确触发 → openclaw fallback
- NV-THINKING-TIMEOUT (dsv4p_nv): thinking request → extended timeout 66s
- 无 NV-MS-FB / NV-ALL-TIERS-FAIL / NV-CYCLE-504 post-restart

## 3. 参数现状

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| TIER_TIMEOUT_BUDGET_S | 205 | optimal |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | floor (=UPSTREAM) |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | floor (< UPSTREAM×2) |
| KEY_COOLDOWN_S | 25 | floor |
| TIER_COOLDOWN_S | 15 | floor |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | floor |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | floor |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | optimal |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | floor (=UPSTREAM) |
| NVU_EMPTY_200_FASTBREAK | 2 | floor |
| NVU_FORCE_STREAM_UPGRADE | 0 | floor |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |

## 4. 决策: NOP

- 所有参数在 floor/optimal，无优化空间
- 13 zombie 是 NVCF content-filter 服务端问题，非 config-fixable
- 10 ATE 全部 pre-restart (容器 13:09Z 重启前)，post-restart 0 ATE
- 0 tier_attempts — 无 key-level 问题
- ms_gw 84% SR — 备份链路正常
- HM1 git log 停留在 R1206 (257 轮落后) — 无实际 HM1 变更
- **零参数修改，零 compose 变更，零容器重启**

## ⏳ 轮到HM1优化HM2
