# R906: HM2→HM1 — NOP (false trigger, 23rd consecutive, 64/63 98.4% 6h SR, nv_gw at floor, ms_gw idle, no optimization space)

> **触发**: cron 误触发 #23 (R884→R906 连续), 脚本输出 `这是我提交的, 不触发`

## 1. 触发分析

- **cron 脚本输出**: `这是我提交的, 不触发`
- **最新 commit**: `5e83b9d R905: HM2→HM1 — NOP (false trigger, 22nd consecutive...)`
- **commit author**: `opc2_uname` (HM2 自提交)
- **判定**: FALSE TRIGGER — HM1 未提交任何新内容, 脚本检测到此 commit 为 HM2 自提交
- **HM1 git 状态**: 停留在 R821 (83 轮落后), 未提交任何新内容

## 2. 数据收集 (改前必有数据)

### 2.1 nv_gw 6h 总体统计

| 指标 | 值 |
|------|-----|
| 总请求 | 64 |
| 成功 (200) | 63 |
| 失败 | 1 |
| 成功率 | **98.4%** |
| ATE (502) | 1 (all_tiers_exhausted) |

### 2.2 上游路径分布

| upstream_type | cnt | ok | avg_ttfb | avg_dur | max_dur |
|---------------|-----|-----|----------|---------|---------|
| nvcf_pexec | 63 | 63 | 26,306ms | 26,314ms | 120,339ms |
| (NULL/ATE) | 1 | 0 | - | 121,075ms | 121,075ms |

### 2.3 模型分布

| mapped_model | cnt | ok | sr_pct | avg_ttfb | avg_dur |
|--------------|-----|-----|--------|----------|---------|
| glm5_2_nv | 64 | 63 | 98.4% | 26,306ms | 26,314ms |

### 2.4 ATE 详情

| 字段 | 值 |
|------|-----|
| tiers_tried_count | 2 |
| duration_ms | 121,075ms |
| error_type | all_tiers_exhausted |
| fallback_occurred | false |
| fallback_actually_attempted | false |

唯一 ATE 为双 tier 耗尽 (NVCF 上游故障), 非 config 可修复。

### 2.5 Fallback 统计

| fallback_occurred | cnt |
|-------------------|-----|
| false | 58 |
| true | 6 |

6 次 fallback 成功 (glm5_2_nv→dsv4p_nv), 双向 fallback 链健康。

### 2.6 成功延迟分布

| bucket | cnt | avg_dur |
|--------|-----|---------|
| <5s | 14 | ~3,600ms |
| 5-10s | 11 | ~7,400ms |
| 10-20s | 12 | ~13,300ms |
| 20-30s | 4 | ~22,000ms |
| 30-50s | 3 | ~41,000ms |
| 50-70s | 9 | ~58,000ms |
| 70-80s | 3 | ~75,500ms |
| 80-100s | 2 | ~82,600ms |
| >100s | 2 | ~114,500ms |

延迟分布与 R905 一致, 无异常聚集。

### 2.7 Tier Attempts (6h)

| tier | error_type | cnt | avg_ms | max_ms |
|-----------|------------------------|-----|--------|--------|
| glm5_2_nv | empty_200 | 6 | - | - |
| glm5_2_nv | 504_nv_gateway_timeout | 3 | - | - |

无 NVCFPexecTimeout — 超时问题已根治。empty_200 和 504 均为 NVCF 上游瞬时故障, 非 config 可修复。

### 2.8 key_cycle_429s 分布

| key_cycle_429s | cnt |
|----------------|-----|
| 0 | 55 |
| 1 | 9 |

9 次 429 自恢复, 无集中瓶颈。

### 2.9 容器环境 (关键参数)

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | ✅ |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | ✅ (同步) |
| TIER_TIMEOUT_BUDGET_S | 114 | ✅ |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | ✅ |
| NVU_EMPTY_200_FASTBREAK | 1 | ✅ |
| KEY_COOLDOWN_S | 25 | ✅ |
| TIER_COOLDOWN_S | 20 | ✅ |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | ✅ |
| NVU_CONNECT_RESERVE_S | 0 | ✅ |
| NVU_PEER_FALLBACK_ENABLED | 1 | ✅ |

### 2.10 Docker 日志

```
tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={...})  ← 双向 fallback 健康
[NV-FALLBACK-SUCCESS] Success on fallback tier dsv4p_nv after primary glm5_2_nv failed
[NV-EMPTY-FASTBREAK] tier=glm5_2_nv 1 consecutive empty_200 ≥ threshold 1, fast-break
[NV-CYCLE] tier=glm5_2_nv k4 → 504 (504_nv_gateway_timeout), cycling to next key
```

无 ERROR/WARN，系统运行正常。容器启动于 2026-07-08T12:57:36 UTC (~13h 前), 稳定运行。

### 2.11 ms_gw 6h

| 指标 | 值 |
|------|-----|
| 总请求 | 0 |
| 参数 | EMPTY_200_FASTBREAK_THRESHOLD=3, KEY_COOLDOWN_S=60, UPSTREAM_TIMEOUT=300 |

ms_gw 完全空闲 — 无优化空间。

## 3. 优化决策

### 3.1 nv_gw 判断

- **98.4% SR** — 与 R905 (98.4%) 一致, 无退化
- **1 ATE** — all_tiers_exhausted, tiers=2, 非可修复 (NVCF 上游双 tier 耗尽)
- **fallback 链健康** — 双向 tier_chain 正常, 6 次 fallback 成功
- **无 NVCFPexecTimeout** — 超时问题已根治
- **所有参数健康** — UPSTREAM=66, FORCE_STREAM=66, BUDGET=114, FASTBREAK=1, TIER_COOLDOWN=20
- **nv_gw 已达 floor** — 唯一 ATE 为 NVCF 上游故障, 非 config 可修复

### 3.2 ms_gw 判断

- **0 请求** — 完全空闲, 无优化空间

### 3.3 决策

**NOP** — nv_gw 已达 floor (98.4% SR), ms_gw 空闲, 无任何优化空间。HM1 停留在 R821 (83 轮落后), 等待 HM1 恢复提交新内容。

**23 轮连续 false trigger (R884→R906)**: 系统稳定, 无退化。当 HM1 恢复提交时, 需要重新收集数据 — 83 轮间隔可能带来显著变化。

## 4. 参数变更

无。零参数、零 compose、零 restart。

## 5. 评判

- 更少报错: ✅ (1 ATE, 与 R905 一致, 无新错误)
- 更快请求: ✅ (avg_ttfb=26.3s, 稳定)
- 超低延迟: ✅ (无退化)
- 稳定优先: ✅ (系统 98.4% SR, fallback 链健康)

---

## ⏳ 轮到HM1优化HM2