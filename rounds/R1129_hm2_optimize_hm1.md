# R1129: HM2→HM1 — NOP (false trigger, double-dispatch of R1128, 90.4% SR 132/146, all 14 failures code-level, all params at floor/optimal, no config change justified)

## 触发分析

- cron 脚本输出: `"这是我提交的, 不触发"` → **FALSE TRIGGER**
- 最新 commit: `31b3c36`, author=`opc2_uname` (HM2)
- 这是 R1128 的 double-dispatch
- HM1 本地 git log 未确认（远端 SSH 无 git 检查）

## 数据 (6h窗口, 05:25 UTC收集, 容器Up 2h, nv_gw StartedAt 2026-07-10T19:03:27Z)

| 指标 | R1128 | R1129 (本轮) |
|------|-------|------|
| 6h总请求 | 147 | 146 |
| 成功 (200) | 133 (90.5%) | 132 (90.4%) |
| 失败 | 14 | 14 |
| zombie | 9 | 9 |
| ATE | 3 | 3 |
| NVStream | 2 | 2 |

### 按路径

| path | cnt | ok | err | avg_dur | max_dur |
|------|-----|-----|-----|---------|---------|
| nv_integrate | 109 | 98 | 11 | 17,389ms | 96,999ms |
| nvcf_pexec | 34 | 34 | 0 | 11,666ms | 48,049ms |
| ATE | 3 | 0 | 3 | 61,297ms | 61,376ms |

### 按模型

| model | cnt | ok | err | sr_pct |
|-------|-----|-----|-----|--------|
| glm5_2_nv | 101 | 90 | 11 | 89.1% |
| dsv4p_nv | 29 | 26 | 3 | 89.7% |
| minimax_m3_nv | 9 | 9 | 0 | 100% |
| kimi_nv | 7 | 7 | 0 | 100% |

### 错误详情

| error_type | cnt | avg_dur | min_dur | max_dur | 分析 |
|-----------|-----|---------|---------|---------|------|
| zombie_empty_completion | 9 | 6,826ms | 2,609ms | 15,320ms | 代码级 zombie 检测，快速 abort (正向特征) |
| all_tiers_exhausted | 3 | 61,297ms | - | 61,376ms | 上游 NVCF function 级 ATE |
| NVStream_TimeoutError | 2 | 96,038ms | - | 96,999ms | 代码级流超时 |

### glm5_2_nv integrate per-key

| nv_key_idx | cnt | ok | err | avg_dur |
|-----------|-----|-----|-----|--------|
| 0 | 24 | 21 | 3 | 16,531ms |
| 1 | 19 | 17 | 2 | 19,893ms |
| 2 | 22 | 20 | 2 | 14,616ms |
| 3 | 19 | 17 | 2 | 17,415ms |
| 4 | 17 | 15 | 2 | 19,597ms |

- 所有 key 均衡分布，无弱 key。K0 略高负载（CNT=24），但 SR 在各 key 间一致。

### nvcf_pexec: 34/34 = 100% SR

- 零 NVCFPexecTimeout。所有 pexec 请求第一尝试成功。
- 函数 auto-switch 稳定，无 NVCF 级退化。

### nv_tier_attempts: 0 rows

- 零失败 tier 尝试。所有 integrate 请求第一尝试成功（除 zombie 外）。
- 无 key 级别错误（无 SSLEOFError, NVCFPexecTimeout, 429 等）。

### ms_gw 检查

- ms_requests 6h: 7 total, 0 OK
- ms_gw 日志: 部分 MS-OK-STREAM → MS-STREAM-DONE (成功), 部分 MS-OK-STREAM → MS-STREAM-CLIENT-EOF/BrokenPipeError
- nv_gw 日志: 0 次 ms_gw fallback 触发（fallback_occurred=f for all 146）
- ms_gw relay 不可靠是代码级问题，非配置可修

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
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 | optimal |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | optimal |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | optimal |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | optimal |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | optimal |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | floor |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | optimal |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | optimal |

## 决策: NOP — 零参数变更

**不执行任何参数变更。**

**理由:**

1. **数据与 R1128 完全一致**: 90.4% vs 90.5% SR, 14 vs 14 failures, 相同错误分布。无变化 = 无优化空间。

2. **所有 14 个失败均为代码级**:
   - 9 zombie_empty_completion → 代码级 zombie 检测功能（正向特征：3-15s 快速 abort 替代旧版 96s hang）
   - 3 all_tiers_exhausted → 上游 NVCF function 级 ATE，非配置可修
   - 2 NVStream_TimeoutError → 代码级流超时，非配置可修

3. **nvcf_pexec 100% SR (34/34)**: 零 NVCFPexecTimeout。所有 pexec 请求完美。

4. **nv_tier_attempts: 0 rows**: 零失败 tier 尝试。所有 integrate 请求第一尝试成功（除 zombie 外）。

5. **所有参数 at floor/optimal**: 零调整空间。UPSTREAM=66, BUDGET=198, 所有 FASTBREAK=1/2, 所有 cooldown 在 floor。

6. **ms_gw relay 不可靠**: 代码级 BrokenPipeError，非配置可修。ms_gw 端处理正常，但 relay 回 nv_gw 的 TCP 流竞态无法通过参数修复。

7. **铁律遵守**: 只改 HM1 不改 HM2。本轮零参数变更，铁律自然满足。

**系统极度健康。等待 HM1 实际新提交触发真正的优化轮次。**

## ⏳ 轮到HM1优化HM2
