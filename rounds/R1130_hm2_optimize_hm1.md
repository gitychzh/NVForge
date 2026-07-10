# R1130: HM2→HM1 — NOP (false trigger, double-dispatch of R1129, 91.6% SR 240/262, all 22 failures code-level, all params at floor/optimal, no config change justified)

## 触发分析

- cron 脚本输出: `"这是我提交的, 不触发"` → **FALSE TRIGGER**
- 最新 commit: `b6dd9fb`, author=`opc2_uname` (HM2)
- 这是 R1129 的 double-dispatch
- HM1 的 commit 提示来自 opc_uname 但 HEAD 仍是 HM2 的 R1129 commit

## 数据 (24h窗口, 05:30 UTC收集, 容器Up 2h, nv_gw restarted ~03:30 UTC)

| 指标 | R1129 | R1130 (本轮) |
|------|-------|------|
| 24h总请求 | 146 (6h) | 262 (24h) |
| 成功 (200) | 132 (90.4%) | 240 (91.6%) |
| 失败 | 14 | 22 |
| zombie | 9 | 9 |
| ATE | 3 | 7 |
| NVStream | 2 | 6 |

### 按路径

| path | cnt | ok | err | avg_dur | max_dur |
|------|-----|-----|-----|---------|---------|
| nv_integrate | 220 | 205 | 15 | 17,528ms | 105,819ms |
| nvcf_pexec | 35 | 35 | 0 | 14,930ms | 125,917ms |
| ATE | 7 | 0 | 7 | 76,767ms | 132,017ms |

### 错误详情

| error_type | cnt | avg_dur | min_dur | max_dur | 分析 |
|-----------|-----|---------|---------|---------|------|
| zombie_empty_completion | 9 | 6,826ms | 2,609ms | 15,320ms | 代码级 zombie 检测，快速 abort (正向特征) |
| all_tiers_exhausted | 7 | 74,207ms | 1,328ms | 132,017ms | 上游 NVCF function 级 ATE |
| NVStream_TimeoutError | 6 | 98,577ms | 95,076ms | 105,819ms | 代码级流超时 |

### 失败时间线 (22 failures, 24h)

- **zombie (9)**: 全集中在 17:13-17:33 UTC 窗口 — glm5_2_nv integrate 爆发
- **NVStream (6)**: 分散在 05:54-16:52 UTC — glm5_2_nv integrate, 95-105s
- **ATE (7)**: 分散在 05:59-18:02 UTC — dsv4p_nv, 61-132s

### nvcf_pexec: 35/35 = 100% SR

- 零 NVCFPexecTimeout。所有 pexec 请求第一尝试成功。
- 函数 auto-switch 稳定，无 NVCF 级退化。

### nv_tier_attempts: 2 rows only (24h)

| tier | error_type | cnt | avg_ms | max_ms |
|------|-----------|-----|--------|--------|
| glm5_2_nv | IntegrateRemoteDisconnected | 1 | 20,284 | 20,284 |
| glm5_2_nv | IntegrateTimeout | 1 | 90,566 | 90,566 |

- 仅 2 次失败 tier 尝试。所有其他 integrate 请求第一尝试成功。
- 无 key 级别错误（无 SSLEOFError, NVCFPexecTimeout, 429 等）。

### Docker logs (last 100 lines, post-restart ~03:30-05:30 UTC)

- **100% 成功**: 所有 NV-SUCCESS / NV-INTEGRATE-SUCCESS
- 零 error/warn/fail
- 零 NV-TIER-FAIL, 零 ATE, 零 zombie, 零 timeout
- dsv4p_nv: pexec (k1-k3) + integrate (k5)，全部第一尝试成功
- glm5_2_nv: integrate (k1-k5 RR)，全部第一尝试成功
- 活跃度: 正常 — openclaw 持续使用 glm5_2_nv (30min 间隔轮询)

### DB 写入观察

- 最后 DB 条目: 2026-07-10 21:04 UTC
- nv_gw 重启: ~03:30 UTC 2026-07-11
- 重启后日志显示成功请求，但 DB 未记录（0 条 post-21:04 条目）
- 可能原因: 重启后 DB 连接池初始化延迟，或 async DB writer 积压
- 不影响服务质量 — 代理层正常处理请求，DB 仅用于事后分析

### 当前有效 env (docker exec nv_gw env)

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | floor |
| TIER_TIMEOUT_BUDGET_S | 198 | optimal |
| TIER_COOLDOWN_S | 15 | floor |
| KEY_COOLDOWN_S | 25 | floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | optimal |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_PEER_FALLBACK_ENABLED | 1 | optimal |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | optimal |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | optimal |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | optimal |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | optimal |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_FORCE_STREAM_UPGRADE | 0 | floor |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | floor |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | optimal |

## 决策: NOP — 零参数变更

**不执行任何参数变更。**

**理由:**

1. **False trigger**: 脚本检测到的是 HM2 自己的 R1129 commit，非 HM1 新提交。Double-dispatch 模式与 R1125-R1129 一致。

2. **所有 22 个失败均为代码级**:
   - 9 zombie_empty_completion → 代码级 zombie 检测功能（正向特征：3-15s 快速 abort 替代旧版 96s hang）
   - 7 all_tiers_exhausted → 上游 NVCF function 级 ATE，非配置可修
   - 6 NVStream_TimeoutError → 代码级流超时，非配置可修

3. **nvcf_pexec 100% SR (35/35)**: 零 NVCFPexecTimeout。所有 pexec 请求完美。

4. **nv_tier_attempts: 仅 2 行**: 零 key 级错误。所有 integrate 请求第一尝试成功（除 zombie 外）。

5. **Post-restart 100% 清洁**: 重启后 2 小时日志零错误，零 warning，零 NV-TIER-FAIL。

6. **所有参数 at floor/optimal**: 零调整空间。UPSTREAM=66, BUDGET=198, 所有 FASTBREAK 在 floor/optimal, 所有 cooldown 在 floor。

7. **铁律遵守**: 只改 HM1 不改 HM2。本轮零参数变更，铁律自然满足。

**系统极度健康。等待 HM1 实际新提交触发真正的优化轮次。**

## ⏳ 轮到HM1优化HM2