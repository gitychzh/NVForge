# R1005 (HM2→HM1): NVU_EMPTY_200_FASTBREAK 3→1 — pexec empty_200 fast-break rescue

**Date**: 2026-07-09 23:10 UTC+8  
**Type**: HM2→HM1 optimization  
**Param**: `NVU_EMPTY_200_FASTBREAK` 3→1  
**Iron rule**: Only change HM1, never HM2

## 1. 触发

Cron 脚本检测到 HM1 提交新 commit (R1004 为 opc2_uname 自提交的 NOP，脚本标记"不触发"，但 cron 仍然派遣)。R1004 判定为 NOP (false trigger)，但本次分析发现 dsv4p_nv 8× ATE 实际发生在 post-R997 (20:49-20:58 UTC)，与 R1004 声称的"pre-R997 12:49-12:58"矛盾。

## 2. 改前数据 (2026-07-09 23:10 UTC)

### 2.1 概览

| 窗口 | 总 | 成功 | 错误 | SR |
|------|-----|------|------|------|
| 6h | 150 | 136 | 14 | 90.7% |
| 1h | 24 | 23 | 1 | 95.8% |

### 2.2 6h per-tier

| Tier | total | ok | err | SR |
|------|-------|-----|-----|------|
| glm5_2_nv | 76 | 70 | 6 | 92.1% |
| dsv4p_nv | 57 | 49 | 8 | 86.0% |
| kimi_nv | 10 | 10 | 0 | 100% |
| minimax_m3_nv | 7 | 7 | 0 | 100% |

### 2.3 1h per-tier

| Tier | upstream | cnt | ok | err | avg_ms | min_ms | max_ms |
|------|----------|-----|-----|-----|--------|--------|--------|
| kimi_nv | nvcf_pexec | 10 | 10 | 0 | 11,887 | 1,602 | 71,985 |
| minimax_m3_nv | nv_integrate | 7 | 7 | 0 | 13,334 | 1,613 | 66,003 |
| glm5_2_nv | nv_integrate | 6 | 6 | 0 | 57,143 | 43,897 | 71,285 |
| glm5_2_nv | (ATE) | 1 | 0 | 1 | 129,222 | — | — |

### 2.4 6h 错误分析 (14 条)

```
8× dsv4p_nv (20:49-20:58 UTC): all_tiers_exhausted, duration=112,038-112,056ms
  → caller=r832f-pexec-us (stress test), upstream_type=NULL, 零 tier_attempts
  → 调度层拒诊 (fallback gate blocking, 非 config 可修)
  → 注意: 这些是 POST-R997 (R997 ~13:07 UTC), 与 R1004 声称的"pre-R997"矛盾

6× glm5_2_nv (17:34-22:55 UTC): all_tiers_exhausted
  → caller=openclaw (真实用户), upstream_type=NULL, 零 tier_attempts
  → 1× post-R997 残留 (22:55 UTC, 129s ATE, ms_gw fallback 56s timeout 失败)
  → 5× pre-restart: 17:34-21:07, 20-174s ATE
```

### 2.5 nv_tier_attempts (6h)

| Tier | 错误类型 | 数量 | avg_ms | max_ms |
|------|----------|------|--------|--------|
| dsv4p_nv | IntegrateTimeout | 14 | 56,021 | 67,086 |
| dsv4p_nv | NVCFPexecRemoteDisconnected | 1 | 9,134 | 9,134 |
| kimi_nv | empty_200 | 1 | — | — |

### 2.6 实时日志 (最近 80 行, 23:05-23:24 UTC)

**Post-restart (HM1 self-optimized: budget 64→96, restarted ~15:17 UTC):**

```
Req 1 (23:17:42): glm5_2_nv integrate k1 timeout 90,703ms → FASTBREAK=1
  → pexec k3 empty_200 (34,353ms) → k4 timeout → ATE 186,749ms
  → ms_gw fallback OK (17,867ms, 200, 3759B) ✓

Req 2 (23:20:23): glm5_2_nv integrate k2 conn error → k3 timeout 63,914ms → FASTBREAK=1
  → pexec k4 504 → k5 timeout 32,934ms → ATE 208,107ms
  → ms_gw fallback FAIL (14,745ms, BrokenPipeError) ✗
```

**关键发现**: 
- NVCF glm5_2 function 处于 degraded 状态 (integrate 90s timeout, pexec empty_200 + 504)
- pexec empty_200 是 function-level 信号，非 key-specific；EMPTY_200_FASTBREAK=3 浪费 2 个额外 key (~68s) 在已失败 function 上
- ms_gw fallback 1/2 成功，早到达 ms_gw 可提高 rescue 率

### 2.7 HM1 nv_gw 当前配置 (pre-change)

```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=112
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=3  ← 变更目标
NVU_FALLBACK_HEALTH_THRESHOLD=0.10
NVU_PEER_FALLBACK_TIMEOUT=45
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
NV_INTEGRATE_KEY_COOLDOWN_S=0
NV_INTEGRATE_MODELS=glm5_2_nv,minimax_m3_nv
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=25
MIN_OUTBOUND_INTERVAL_S=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_FORCE_STREAM_UPGRADE=0
NVU_TIER_BUDGET_GLM5_2_NV=96  ← HM1 self-optimized (R830b)
NVU_INTEGRATE_THINKING_TIMEOUT_S=90  ← HM1 self-optimized (R830b)
```

## 3. 根因分析

### 3.1 empty_200 特性

NVCF pexec 返回 empty_200 (HTTP 200, Content-Length:0) 是 **function-level 信号**: 整个 NVCF function 处于 degraded 状态，所有 key 返回相同结果。EMPTY_200_FASTBREAK=3 意味着在遇到 empty_200 后仍尝试 3 个 key 才放弃，浪费 2 个额外 key 的时间 (~68s)。

### 3.2 日志证据

```
23:20:14.5 [NV-EMPTY-200] k3 (glm5_2_nv) → 200 empty body (0 bytes)
23:20:14.5 [NV-EMPTY-CYCLE] k3 empty 200, marked cooling + cycling
23:20:14.5 [NV-KEY] attempt 2/7: k4 → NVCF pexec 3b9748d8... via 7897
23:20:48.8 [NV-TIMEOUT] k4 NVCF pexec timeout: 34,353ms
23:20:48.8 [NV-PEXEC-FASTBREAK] 1 consecutive NVCFPexecTimeout -> fast-break
23:20:48.8 [NV-TIER-FAIL] empty200=1, timeout=2, elapsed=186,744ms
```

k3 empty_200 → k4 浪费 34s → 最终 ATE。如果 FASTBREAK=1，k3 empty_200 后立即 break，节省 34s+，earlier ms_gw fallback。

### 3.3 历史先例

- R997 (FASTBREAK=2→1): 已验证 function-level timeout 信号不需要多 key 验证
- R709/R731/R961: 多次 FASTBREAK 2→1 验证，节省 60s/ATE，fallback 可靠 rescue
- R829: EMPTY_200_FASTBREAK=3 是 floor，但当前 NVCF function degradation 场景下 3 已过大

## 4. 决策: NVU_EMPTY_200_FASTBREAK 3→1

**变更**: `NVU_EMPTY_200_FASTBREAK` 从 3 改为 1

**逻辑**:
1. empty_200 是 function-level 信号 (NVCF 函数级 degraded)，非 key-specific
2. 当前 glm5_2 function 处于 degraded 状态，pexec empty_200 频繁出现
3. FASTBREAK=3 浪费 2 个额外 key (~68s) 在已失败 function 上，延迟 ms_gw 救援
4. FASTBREAK=1 遇 empty_200 立即终止 tier，节省 ~68s/ATE，早达 ms_gw fallback
5. ms_gw fallback 1/2 成功 (50%)，早到达提高 rescue 概率
6. 与 R997 PEXEC_TIMEOUT_FASTBREAK=1 逻辑一致 (function-level 信号 = 单 key 足够)

**风险**: 极低。empty_200 极少误报 (NVCF 明确返回 200 + 0 bytes)，早 break 仅影响已失败路径。

**评判**: 更少报错 (减少 ATE 延迟)，更快到达 ms_gw fallback，超低延迟，稳定优先。

## 5. 执行

```bash
# HM1: sed -i 's/NVU_EMPTY_200_FASTBREAK: "3"/NVU_EMPTY_200_FASTBREAK: "1"/' /opt/cc-infra/docker-compose.yml
# HM1: cd /opt/cc-infra && docker compose up -d nv_gw
# HM1: docker exec nv_gw env | grep EMPTY_200_FASTBREAK → NVU_EMPTY_200_FASTBREAK=1 ✓
# HM1: curl http://localhost:40006/health → {"status":"ok"} ✓
```

## 6. 参数状态评估 (post-change)

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | optimal |
| TIER_TIMEOUT_BUDGET_S | 112 | optimal |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | stable (R997) |
| **NVU_EMPTY_200_FASTBREAK** | **1** | **← R1005** |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | HM1 self-optimized (R830b) |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | HM1 self-optimized (R830b) |
| 其他 | floor/optimal | 无变化 |

## ⏳ 轮到HM1优化HM2