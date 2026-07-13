# R1266: HM2→HM1 — NOP (false trigger, R1265 needs observation time)

## 1. 触发分析

```
From github.com:gitychzh/NVForge
HEAD is now at 59fd69a R1265: HM2→HM1 — Remove dsv4p_nv from ms_gw MODELMAP; route dsv4p ATE via peer-fallback
[2026-07-14 02:30:15] 这是我提交的, 不触发
```

- 最新 commit author = opc2_uname (HM2)
- R1265 已由 HM2 提交 (59fd69a)
- 脚本检测到自提交并标记"不触发"，但 cron 仍被派遣 → 误触发/双派遣 (false trigger / double-dispatch)

## 2. 数据收集 (改前必有数据)

### 2.1 容器状态
- nv_gw: Up 7 minutes (healthy), restarted ~02:25 UTC (R1265 部署后重启)
- ms_gw: Up 9 hours (healthy)
- logs_db: Up 9 hours (healthy)
- compose md5: 0dff5e071f93fc571baa92c55a21becc (R1265 已部署)

### 2.2 6h 总体 (DB: nv_requests, 窗口: ~2026-07-13 12:00–18:00 UTC)
- **88req/71OK/17fail = 80.7% SR** (与 R1265 报告的 80.5% 一致, 统计误差)
- 有效窗口: nv_gw 重启于 02:25Z, 重启前数据含 R1265 前窗口

### 2.3 错误分类 (17 failures, 全部重启前)
| 错误类型 | 数量 | 模型 | 说明 |
|----------|------|------|------|
| zombie_empty_completion | 11 | glm5_2_nv | NVCF content-filter stop+12chars, avg 15s, 代码级 |
| all_tiers_exhausted | 5 | 3 dsv4p_nv + 2 glm5_2_nv | 重启前 ATE; dsv4p 走 ms_gw (R1265 修复目标), glm5_2 404 NONCYCLE |
| NVStream_IncompleteRead | 1 | glm5_2_nv | 24s, 网络层中断, 代码级 |

### 2.4 按模型
| 模型 | 请求 | OK | 失败 | SR | avg_ttfb | avg_dur | max_dur |
|------|------|-----|------|------|----------|---------|---------|
| glm5_2_nv | 74 | 60 | 14 | 81.1% | 11.3s | 12.9s | 44.8s |
| dsv4p_nv | 14 | 11 | 3 | 78.6% | 21.9s | 37.2s | 72.0s |

### 2.5 按上游类型
| 类型 | 请求 | OK | 失败 | SR | avg_ttfb | avg_dur |
|------|------|-----|------|------|----------|---------|
| nv_integrate | 68 | 57 | 11 | 83.8% | 11.5s | 13.0s |
| nvcf_pexec | 14 | 14 | 0 | **100%** | 25.6s | 25.6s |
| NULL (ATE) | 6 | 0 | 6 | 0% | 0.8s | 38.7s |

### 2.6 小时级 SR
| 小时 (UTC) | 请求 | OK | 失败 | SR |
|------------|------|-----|------|------|
| 12:00 | 23 | 19 | 4 | 82.6% |
| 13:00 | 6 | 5 | 1 | 83.3% |
| 14:00 | 8 | 6 | 2 | 75.0% |
| 15:00 | 6 | 4 | 2 | 66.7% |
| 16:00 | 6 | 4 | 2 | 66.7% |
| 17:00 | 6 | 4 | 2 | 66.7% |
| 18:00 | 33 | 29 | 4 | 87.9% |

### 2.7 dsv4p_nv ATE 详情 (3 例, 全部 R1265 部署前)
| 时间 (UTC) | ttfb | 总耗时 | tiers_tried | fallback |
|------------|------|--------|-------------|----------|
| 18:08 | 601ms | 72,023ms | 1 | false |
| 18:02 | 1,133ms | 72,015ms | 1 | false |
| 18:01 | 908ms | 72,020ms | 1 | false |

- 持续时间 72s = `NVU_TIER_BUDGET_DSV4P_NV=72` (budget binding)
- fallback_occurred=false — ms_gw 已触发但失败 (R1265 分析: 100% BrokenPipeError/TimeoutError)
- R1265 修复: 移除 dsv4p_nv 从 ms_gw MODELMAP → peer-fallback 接管

### 2.8 glm5_2_nv ATE 详情 (2 例, 全部 R1265 部署前)
| 时间 (UTC) | ttfb | 总耗时 | tiers_tried | fallback |
|------------|------|--------|-------------|----------|
| 12:39 | 784ms | 4,978ms | 1 | false |
| 12:37 | 794ms | 3,845ms | 1 | false |

- 404 NONCYCLE (R1241: NVCF function 3b9748d8 返回 404 on both integrate+pexec)
- 代码级/上游问题, 不可配置修复

### 2.9 Tier Attempts
- nv_tier_attempts: 0 rows (6h 窗口)
- 僵尸检测在 key 耗尽前触发, 无 key 级失败记录

### 2.10 Fallback 状态
- fallback_occurred: false (全部 88 请求)
- 0 peer-fallback 触发 (R1265 重启后仅 2 请求, 均 first-attempt 成功)

### 2.11 nv_gw 实时日志 (重启后 ~02:25–02:33 UTC)
```
[NV-SUCCESS] tier=dsv4p_nv k3 succeeded on first attempt
[NV-INTEGRATE-SUCCESS] tier=glm5_2_nv k1 succeeded on first attempt
[NV-INTEGRATE-SUCCESS] tier=glm5_2_nv k2 succeeded on first attempt
[NV-INTEGRATE-SUCCESS] tier=glm5_2_nv k3 succeeded on first attempt
[NV-ZOMBIE-EMPTY] glm5_2_nv zombie empty completion (207K input, 12 chars)
[NV-ZOMBIE-ERROR-CHUNK] glm5_2_nv sent content_filter SSE chunk
```
- 重启后完美: 全部 first-attempt 成功
- 1× zombie 正确检测 (代码级)

### 2.12 ms_gw 实时日志
- MS-OK-STREAM + MS-STREAM-DONE 正常 (ZHIPUAI/GLM-5.2 + deepseek-ai/deepseek-v4-pro)
- 无异常

### 2.13 R1265 部署验证
- `NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms` ✓ (dsv4p_nv 已移除)
- `curl http://localhost:40006/health` → `{"status":"ok"}` ✓
- Peer-fallback URL `http://100.109.57.26:40006/health` → `{"status":"ok"}` ✓ (HM2 可达)
- compose md5: 0dff5e071f93fc571baa92c55a21becc (R1265 已部署)

### 2.14 关键参数 (全部 floor/optimal, 无变化)
| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | floor |
| TIER_TIMEOUT_BUDGET_S | 210 | optimal |
| TIER_COOLDOWN_S | 15 | floor |
| KEY_COOLDOWN_S | 25 | floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | floor |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | optimal |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2,kimi (dsv4p removed) | R1265 |
| NVU_PEER_FB_SKIP_MODELS | (empty) | optimal |
| NVU_PEER_FALLBACK_ENABLED | 1 | enabled |

## 3. 分析

### 3.1 失败分类

| 类别 | 数量 | 占比 | 可配置修复? |
|------|------|------|------------|
| zombie_empty_completion (NVCF content-filter) | 11 | 64.7% | ❌ 代码级 |
| all_tiers_exhausted (dsv4p ATE) | 3 | 17.6% | ✅ R1265 已修复 (ms_gw→peer-fb) |
| all_tiers_exhausted (glm5_2 404 NONCYCLE) | 2 | 11.8% | ❌ NVCF 上游 |
| NVStream_IncompleteRead | 1 | 5.9% | ❌ 网络层 |

### 3.2 R1265 修复效果评估

**R1265 变更**: 移除 `dsv4p_nv:dsv4p_ms` 从 `NVU_MS_GW_FALLBACK_MODELMAP` → dsv4p ATE 走 peer-fallback 而非 ms_gw.

- 部署后仅 7 分钟, 2 请求 (1 dsv4p + 1 glm5_2), 均 first-attempt 成功
- 0 dsv4p ATE 发生 (无触发机会, 属于正常 — 低流量)
- 需要更长观察窗口 (至少 6h) 验证 peer-fallback 是否有效拦截 dsv4p ATE
- glm5_2_nv 和 kimi_nv 的 ms_gw fallback 路径不受影响

### 3.3 配置状态

- 所有参数已处于 floor/optimal — 无优化空间
- All FASTBREAK at floor — PEXEC=1, INTEGRATE=1, EMPTY_200=2
- All tier budgets optimal — DSV4P=72, GLM5_2=96
- R1265 修复已部署, 需要观察期
- Peer-fb enabled, skip_models empty, HM2 健康可达

### 3.4 实时日志评估

- 重启后完美: 5/5 请求 first-attempt 成功, 1× zombie 正确检测
- 0 NV-TIER-FAIL, 0 NV-ALL-TIERS-FAIL, 0 NV-MS-FB, 0 NV-PEER-FB
- 0 NV-GLOBAL-COOLDOWN, 0 NV-NONCYCLE-ERR
- 0 nv_tier_attempts 行

## 4. 决策: NOP

**Zero param change. Zero config change. Zero container restart.**

理由:
1. R1265 修复 (dsv4p_nv ms_gw→peer-fb) 刚部署 7 分钟, 需要更长观察期验证效果
2. 所有剩余失败均为代码级 (zombie + NVCF 404 + 网络中断) — 不可配置修复
3. 所有参数已处于 floor/optimal — 无优化空间
4. 重启后实时日志完美: 全部 first-attempt 成功
5. compose md5 已更新为 R1265 版本
6. 铁律: 只改 HM1 不改 HM2
7. 本轮为 false trigger (HM2 自提交 R1265 被调度)

**预期下一轮**: 6h 后观察 R1265 的 peer-fallback 效果, 确认 dsv4p_nv ATE 是否被 peer-fb 成功拦截.

## ⏳ 轮到HM1优化HM2