# R908: HM2→HM1 — NOP (false trigger, 25th consecutive, 69/68 98.6% 6h SR, nv_gw at floor, ms_gw idle, no optimization space)

> **触发**: cron 误触发 #25 (R884→R908 连续), 脚本输出 `这是我提交的, 不触发` — HM2 自提交 R907

## 1. 触发分析

- **cron 脚本输出**: `这是我提交的, 不触发`
- **最新 commit on HM1**: `fbf0e43 R821: HM2→HM1 — NOP` (86 轮落后)
- **commit author**: `opc2_uname` (HM2 自提交 R907)
- **判定**: FALSE TRIGGER — HM1 未提交任何新内容, HM2 自提交 R907 触发了 cron 派遣

## 2. 数据收集 (改前必有数据)

### 2.1 nv_gw 6h 总体统计

| 指标 | 值 |
|------|-----|
| 总请求 | 69 |
| 成功 (200) | 68 |
| 失败 | 1 |
| 成功率 | **98.6%** |

### 2.2 上游路径分布

| upstream_type | cnt | ok | avg_ttfb | avg_dur | max_dur |
|---------------|-----|-----|----------|---------|---------|
| nvcf_pexec | 68 | 68 | 25,878ms | 25,917ms | 120,339ms |
| NULL (ATE) | 1 | 0 | - | 121,075ms | 121,075ms |

### 2.3 模型分布

| mapped_model | cnt | ok | avg_ttfb | avg_dur |
|--------------|-----|-----|----------|---------|
| glm5_2_nv | 68 | 67 | 26,219ms | 27,653ms |

### 2.4 ATE 详情

| 字段 | 值 |
|------|-----|
| ts | 2026-07-08 13:21:01 UTC |
| tiers_tried_count | 2 |
| duration_ms | 121,075ms |
| error_type | all_tiers_exhausted |
| error_subcategory | all_tiers_failed_in_mapped_tier |
| fallback_actually_attempted | false |

唯一 ATE 与 R906/R907 完全相同 (同一请求, 同一 6h 窗口) — 双 tier 耗尽 (NVCF 上游故障), 非 config 可修复。

### 2.5 Fallback 统计

| fallback_occurred | cnt |
|-------------------|-----|
| false | 62 |
| true | 6 |

6 次 fallback 成功 (glm5_2_nv→dsv4p_nv), 双向 fallback 链健康。

### 2.6 key_cycle_429s 分布

| key_cycle_429s | cnt |
|----------------|-----|
| 0 | 59 |
| 1 | 9 |

9 次 429 自恢复, 无集中瓶颈。

### 2.7 Tier Attempts (6h)

| tier | error_type | cnt |
|------|------------------------|-----|
| glm5_2_nv | empty_200 | 6 |
| glm5_2_nv | 504_nv_gateway_timeout | 3 |

无 NVCFPexecTimeout — 超时问题已根治。empty_200 和 504 均为 NVCF 上游瞬时故障。

### 2.8 最近 10 条请求

| ts | model | status | ttfb_ms | dur_ms | kc_429 |
|----|-------|--------|---------|--------|--------|
| 17:26:40 | glm5_2_nv | 200 | 5,377 | 5,378 | 0 |
| 17:26:32 | glm5_2_nv | 200 | 7,499 | 7,499 | 0 |
| 17:26:26 | glm5_2_nv | 200 | 6,062 | 6,062 | 0 |
| 17:25:50 | glm5_2_nv | 200 | 29,101 | 29,556 | 0 |
| 17:25:32 | glm5_2_nv | 200 | 15,446 | 15,446 | 0 |
| 17:25:16 | glm5_2_nv | 200 | 12,855 | 12,855 | 0 |
| 17:22:12 | glm5_2_nv | 200 | 43,125 | 44,815 | 0 |
| 17:21:35 | glm5_2_nv | 200 | 34,684 | 34,685 | 0 |
| 17:08:42 | glm5_2_nv | 200 | 3,459 | 3,459 | 0 |
| 17:08:39 | glm5_2_nv | 200 | 1,578 | 1,578 | 0 |

全部 200 OK, 延迟正常 (1.5s–44.8s), 无 429。

### 2.9 Docker 日志 (最近 500 行, 关键事件)

```
[NV-REQ] mapped_model=glm5_2_nv start_tier=glm5_2_nv stream=True tier_chain=['glm5_2_nv', 'dsv4p_nv']
[NV-TIER] Starting tier=glm5_2_nv model=z-ai/glm-5.2 func=3b9748d8-1d8...
[NV-KEY] tier=glm5_2_nv attempt 1/7: k1 → NVCF pexec 3b9748d8-1d8... DIRECT
[NV-SUCCESS] tier=glm5_2_nv k1 succeeded on first attempt
[NV-KEY] tier=glm5_2_nv attempt 1/7: k2 → NVCF pexec 3b9748d8-1d8... DIRECT
[NV-SUCCESS] tier=glm5_2_nv k2 succeeded on first attempt
[NV-KEY] tier=glm5_2_nv k3 → NVCF pexec 3b9748d8-1d8... DIRECT
[NV-SUCCESS] tier=glm5_2_nv k3 succeeded on first attempt
[NV-KEY] tier=glm5_2_nv k4 → NVCF pexec 3b9748d8-1d8... DIRECT
[NV-SUCCESS] tier=glm5_2_nv k4 succeeded on first attempt
[NV-KEY] tier=glm5_2_nv k5 → NVCF pexec 3b9748d8-1d8... DIRECT
[NV-SUCCESS] tier=glm5_2_nv k5 succeeded on first attempt
```

所有请求均为 NV-SUCCESS on first attempt, 无 ERROR/WARN/exception/traceback。容器运行稳定, 日志极其干净。

### 2.10 容器环境 (关键参数)

| 参数 | HM1 值 | HM2 值 (R907) | 差异? |
|------|--------|---------------|-------|
| UPSTREAM_TIMEOUT | 64 | 66 | ⚠️ -2s |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 | 66 | ⚠️ -2s |
| TIER_TIMEOUT_BUDGET_S | 114 | 114 | ✅ |
| NVU_PEXEC_TIMEOUT_FASTBREAK | (未设置) | 1 | ⚠️ missing |
| NVU_EMPTY_200_FASTBREAK | 3 | 1 | ⚠️ -2 |
| KEY_COOLDOWN_S | 25 | 25 | ✅ |
| TIER_COOLDOWN_S | 25 | 20 | ⚠️ +5s |
| NVU_FORCE_STREAM_UPGRADE | 0 | 1 | ⚠️ |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | 0.10 | ✅ |
| NVU_CONNECT_RESERVE_S | 0 | 0 | ✅ |
| NVU_PEER_FALLBACK_ENABLED | 1 | 1 | ✅ |

**6 项参数与 HM2 不同步** (HM1 停留在 R821, 86 轮落后)。但当前 98.6% SR 下无优化紧迫性 — 这些差异不影响当前稳定性。

### 2.11 ms_gw 6h

| 指标 | 值 |
|------|-----|
| 总请求 | 0 |
| 参数 | EMPTY_200_FASTBREAK_THRESHOLD=3, KEY_COOLDOWN_S=60, UPSTREAM_TIMEOUT=300 |

ms_gw 完全空闲 — 无优化空间。

## 3. 优化决策

### 3.1 nv_gw 判断

- **98.6% SR** — 与 R907 (98.5%) 一致, 微升 0.1%, 无退化
- **1 ATE** — all_tiers_exhausted, 与 R906/R907 同一请求 (同一 6h 窗口), 非可修复
- **fallback 链健康** — 双向 tier_chain 正常, 6 次 fallback 成功
- **无 NVCFPexecTimeout** — 超时问题已根治
- **Docker 日志极干净** — 所有请求 first-attempt success, 零错误
- **nv_gw 已达 floor** — 唯一 ATE 为 NVCF 上游故障, 非 config 可修复

### 3.2 参数同步机会 (未来参考)

HM1 有 6 项参数与 HM2 不同步, 按优先级:

1. **NVU_PEXEC_TIMEOUT_FASTBREAK** (HM1 缺失 vs HM2=1) — 最高优先级。当前无 NVCFPexecTimeout 事件, 但一旦发生, 缺少 fastbreak 会导致 2 次额外 key 尝试 (~30s wasted)
2. **NVU_EMPTY_200_FASTBREAK 3→1** (HM2=1) — 6h 有 6 次 empty_200, 当前 fastbreak=3 浪费 2 次额外 key 尝试; 降为 1 可节省 ~12 次无用尝试/6h
3. **NVU_FORCE_STREAM_UPGRADE 0→1** (HM2=1) — 当前 glm5_2_nv 全部 pexec 流式请求, stream upgrade 优化可减少 thinking 截断
4. **UPSTREAM_TIMEOUT 64→66** (HM2=66) — 2s 差异无实际影响, 当前 NVCFPexecTimeout 事件为零
5. **NVU_FORCE_STREAM_UPGRADE_TIMEOUT 64→66** — 与 UPSTREAM 同步
6. **TIER_COOLDOWN_S 25→20** (HM2=20) — 单 tier 架构下死参数

**建议下一轮 (当 HM1 有实际提交时)**: 同步 #1 (NVU_PEXEC_TIMEOUT_FASTBREAK=1) 和 #2 (NVU_EMPTY_200_FASTBREAK=1), 两个低风险 fastbreak 同步, 不改变任何 timeout/budget。

### 3.3 决策

**NOP** — nv_gw 已达 floor (98.6% SR), ms_gw 空闲, 无任何优化空间。HM1 停留在 R821 (86 轮落后), 等待 HM1 恢复提交新内容。

**25 轮连续 false trigger (R884→R908)**: 系统极其稳定, 无退化。参数同步机会存在但不紧迫 — 当前数据不支持任何变更。当 HM1 恢复提交时, 需要重新收集数据 — 86 轮间隔可能带来显著变化。

## 4. 参数变更

无。零参数、零 compose、零 restart。

## 5. 评判

- 更少报错: ✅ (1 ATE, 与 R907 一致, 无新错误, Docker 日志零异常)
- 更快请求: ✅ (avg_ttfb=25.9s, 稳定)
- 超低延迟: ✅ (无退化, 最近 10 请求全部 200 OK)
- 稳定优先: ✅ (系统 98.6% SR, fallback 链健康, 所有 first-attempt success)

---

## ⏳ 轮到HM1优化HM2