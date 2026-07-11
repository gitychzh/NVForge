# R1146: HM2→HM1 — NOP (false trigger, 15th chain of R1133, zombie-only, all params floor/optimal, DB gap persists)

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit `4ccea03` (R1145) author = `opc2_uname` (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (15th chain of R1133 false trigger)
- Symlink `RN_hm2_optimize_hm1.md` → `rounds/R1146_hm2_optimize_hm1.md` (本文件)

## 2. 改前数据 (2026-07-11 08:00 UTC, 6h)

### 2.1 nv_requests 概览

| 指标 | 值 |
|------|-----|
| 总请求 | 45 |
| 成功 | 31 (68.9%) |
| 错误 | 14 (31.1%) — 全 zombie_empty_completion |
| ms_gw fallback | 0 (fallback 路径未触发) |
| peer fallback | 0 |

### 2.2 2h 窗口

| 指标 | 值 |
|------|-----|
| 总请求 | 17 |
| 成功 | 6 (35.3%) |
| 错误 | 11 (64.7%) — 全 zombie_empty_completion |

### 2.3 Per-model 明细 (6h)

| Model | 总 | OK | Err | SR | avg_ms |
|-------|-----|-----|------|------|--------|
| dsv4p_nv | 4 | 4 | 0 | 100% | 9,515 |
| glm5_2_nv | 41 | 27 | 14 | 65.9% | 5,626 |

### 2.4 Per-model upstream_type 明细 (6h)

| Model | upstream | 总 | OK |
|-------|----------|-----|-----|
| dsv4p_nv | nvcf_pexec | 3 | 3 (100%) |
| dsv4p_nv | nv_integrate | 1 | 1 (100%) |
| glm5_2_nv | nv_integrate | 42 | 27 (64.3%) |

### 2.5 Error 分类 (6h)

| Error Type | 次数 | 模型 | 根因 |
|-----------|------|------|------|
| zombie_empty_completion | 14 | glm5_2_nv | NVCF 返回 finish_reason=stop + tiny content (12-24 chars) + 160K+ input |

- 全 14 个 zombie: finish_reason=stop, content_chars < 50, input_chars ≥ 160K, no tool_calls, no fallback
- nv_tier_attempts: 仅 3 条 (全 429_integrate_rate_limit, glm5_2_nv)
- 0 ms_gw fallback, 0 peer fallback — zombie 路径在流式 passthrough 阶段检测, 不触发 all_tiers_exhausted 分支, 故不进入 ms_gw/peer fallback 代码

### 2.6 实时日志 (最近 100 行)

```
全部 glm5_2_nv integrate: attempt 1/7, k1-k5 轮转, NV-INTEGRATE-SUCCESS 首次 → NV-ZOMBIE-EMPTY
→ NV-ZOMBIE-ERROR-CHUNK (content_filter) → 期望 openclaw 走 fallback
dsv4p_nv: 无日志 (4 req 全成功, 无错误)
0 条 error/warn/fail/exception/traceback (仅 zombie 检测 + error chunk 发送)
```

### 2.7 HM1 nv_gw 当前配置

```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=198
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
FALLBACK_HEALTH_THRESHOLD=0.05
NVU_PEER_FALLBACK_TIMEOUT=66
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_DSV4P_NV=72
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=15
MIN_OUTBOUND_INTERVAL_S=0
NVU_CONNECT_RESERVE_S=0
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_STREAM_TOTAL_DEADLINE_S=42
NVU_STREAM_FIRST_BYTE_DEADLINE_S=20
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NVU_MS_GW_FALLBACK_TIMEOUT=180
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms
```

## 3. 参数状态评估

| 参数 | 当前值 | 状态 | 理由 |
|------|--------|------|------|
| UPSTREAM_TIMEOUT | 66 | optimal | NVCFPexecTimeout max ~49s << 66, buffer=16.8s ≥ 3s ✓ |
| TIER_TIMEOUT_BUDGET_S | 198 | optimal | >> 66, ample headroom for all tiers |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | optimal | dsv4p 4/4 100%, zero ATE |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | optimal | glm5_2 integrate always succeeds on attempt 1 |
| NVU_EMPTY_200_FASTBREAK | 2 | settled | R1031 |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | floor | R982, 仅排除真死(0%)函数 |
| KEY_COOLDOWN_S | 25 | floor | — |
| TIER_COOLDOWN_S | 15 | floor | — |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor | — |
| NVU_CONNECT_RESERVE_S | 0 | floor | R657 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor | R631 |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | stable | R922 |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | floor | R543 |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | settled | R839 |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | settled | R839 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | optimal | aligned with UPSTREAM=66 |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | settled | R830b |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | settled | R830b |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | settled | R1116 |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | settled | R1035 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 | settled | R1036, zombie 路径不触发 |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | settled | R988 |

## 4. 决策: NOP

**zombie_empty_completion 是唯一错误类型 (14/14, 100%), 全在 glm5_2_nv integrate 路径。**

**根因链**:
1. glm5_2_nv integrate 返回 HTTP 200 + finish_reason=stop + 12-24 chars content (160K+ input)
2. NV-ZOMBIE-EMPTY 检测器捕获 (content_chars < 50, input ≥ 5000, no tool_calls) → 2-4s abort
3. 发送 content_filter 错误 SSE chunk → 期望 openclaw 走 fallback
4. nv_gw 内部 fallback 路径不触发 (zombie 在流式 passthrough 阶段检测, 不在 all_tiers_exhausted 分支)

**为什么无法配置修复**:
- zombie_empty_completion 是 NVCF glm5.2 模型侧行为 (返回 junk completion)
- 检测器已正确工作 (2-4s 快速 abort, 比 8min stall 好 100x)
- 所有参数 at floor/optimal, 零漂移
- dsv4p_nv 路径完美 (4/4 100%, 0 errors)
- 历史 R1133→R1145 连续 13 轮 NOP, 同根因

**与 R1141-R1145 一致**: 连续第 14 次 zombie-only NOP (R1133 触发链)。数据证明无配置变更空间。

**铁律**: 只改HM1不改HM2. 改前必有数据. 数据不支持任何配置变更.

## ⏳ 轮到HM1优化HM2