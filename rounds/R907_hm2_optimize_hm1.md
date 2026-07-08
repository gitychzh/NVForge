# R907: HM2→HM1 — NOP (false trigger, 24th consecutive, 66/65 98.5% 6h SR, nv_gw at floor, ms_gw idle, no optimization space)

> **触发**: cron 误触发 #24 (R884→R907 连续), 脚本输出 `这是我提交的, 不触发`

## 1. 触发分析

- **cron 脚本输出**: `这是我提交的, 不触发`
- **最新 commit**: `eee6117 R906: HM2→HM1 — NOP (false trigger, 23rd consecutive...)`
- **commit author**: `opc2_uname` (HM2 自提交)
- **判定**: FALSE TRIGGER (DOUBLE-DISPATCH) — 预运行脚本已写好 R906 并更新 symlink, cron 再次派遣 agent
- **HM1 git 状态**: 停留在 R821 (85 轮落后), 未提交任何新内容

## 2. 数据收集 (改前必有数据)

### 2.1 nv_gw 6h 总体统计

| 指标 | 值 |
|------|-----|
| 总请求 | 66 |
| 成功 (200) | 65 |
| 失败 | 1 |
| 成功率 | **98.5%** |

### 2.2 上游路径分布

| upstream_type | cnt | ok | avg_ttfb | avg_dur | max_dur |
|---------------|-----|-----|----------|---------|---------|
| nvcf_pexec | 65 | 65 | 26,694ms | 26,728ms | 120,339ms |
| (NULL/ATE) | 1 | 0 | - | 121,075ms | 121,075ms |

### 2.3 模型分布

| mapped_model | cnt | ok | avg_ttfb | avg_dur |
|--------------|-----|-----|----------|---------|
| glm5_2_nv | 66 | 65 | 26,694ms | 28,157ms |

### 2.4 ATE 详情

| 字段 | 值 |
|------|-----|
| ts | 2026-07-08 13:21:01 UTC |
| tiers_tried_count | 2 |
| duration_ms | 121,075ms |
| error_type | all_tiers_exhausted |
| error_subcategory | all_tiers_failed_in_mapped_tier |
| fallback_occurred | false |
| fallback_actually_attempted | false |

唯一 ATE 与 R906 完全相同 (同一请求, 同一 6h 窗口) — 双 tier 耗尽 (NVCF 上游故障), 非 config 可修复。

### 2.5 Fallback 统计

| fallback_occurred | cnt |
|-------------------|-----|
| false | 60 |
| true | 6 |

6 次 fallback 成功 (glm5_2_nv→dsv4p_nv), 双向 fallback 链健康。

### 2.6 key_cycle_429s 分布

| key_cycle_429s | cnt |
|----------------|-----|
| 0 | 57 |
| 1 | 9 |

9 次 429 自恢复, 无集中瓶颈。

### 2.7 Tier Attempts (6h)

| tier | error_type | cnt |
|-----------|------------------------|-----|
| glm5_2_nv | empty_200 | 6 |
| glm5_2_nv | 504_nv_gateway_timeout | 3 |

无 NVCFPexecTimeout — 超时问题已根治。empty_200 和 504 均为 NVCF 上游瞬时故障。

### 2.8 最近 10 条请求

| ts | model | status | ttfb_ms | dur_ms | kc_429 |
|----|-------|--------|---------|--------|--------|
| 17:22:12 | glm5_2_nv | 200 | 43,125 | 44,815 | 0 |
| 17:21:35 | glm5_2_nv | 200 | 34,684 | 34,685 | 0 |
| 17:08:42 | glm5_2_nv | 200 | 3,459 | 3,459 | 0 |
| 17:08:39 | glm5_2_nv | 200 | 1,578 | 1,578 | 0 |
| 17:08:35 | glm5_2_nv | 200 | 3,266 | 3,266 | 0 |
| 17:03:42 | glm5_2_nv | 200 | 6,233 | 6,233 | 0 |
| 17:03:36 | glm5_2_nv | 200 | 5,943 | 5,944 | 0 |
| 17:03:21 | glm5_2_nv | 200 | 11,880 | 11,880 | 0 |
| 16:33:21 | glm5_2_nv | 200 | 2,527 | 2,528 | 0 |
| 16:03:21 | glm5_2_nv | 200 | 5,773 | 5,773 | 0 |

全部 200 OK, 延迟正常 (1.5s–44.8s), 无 429。

### 2.9 Docker 日志 (最近 100 行, 关键事件)

```
[NV-EMPTY-FASTBREAK] tier=glm5_2_nv 1 consecutive empty_200 ≥ threshold 1, fast-break
[NV-TIER-FAIL] tier=glm5_2_nv all 5 keys failed: 429=0, empty200=1, timeout=0, other=0
[NV-FALLBACK] Tier glm5_2_nv all-failed → falling back to dsv4p_nv
[NV-FALLBACK-SUCCESS] Success on fallback tier dsv4p_nv after primary glm5_2_nv failed
[NV-CYCLE] tier=glm5_2_nv k4 → 504 (504_nv_gateway_timeout), cycling to next key
[NV-SUCCESS] tier=glm5_2_nv k5 succeeded after 1 cycle attempts
```

无 ERROR/WARN, 系统运行正常。容器启动于 2026-07-08T12:57:36 UTC (~17h 前), 稳定运行。

### 2.10 容器环境 (关键参数)

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

### 2.11 ms_gw 6h

| 指标 | 值 |
|------|-----|
| 总请求 | 0 |
| 参数 | EMPTY_200_FASTBREAK_THRESHOLD=3, KEY_COOLDOWN_S=60, UPSTREAM_TIMEOUT=300 |

ms_gw 完全空闲 — 无优化空间。

## 3. 优化决策

### 3.1 nv_gw 判断

- **98.5% SR** — 与 R906 (98.4%) 一致, 无退化
- **1 ATE** — all_tiers_exhausted, 与 R906 同一请求 (同一 6h 窗口), 非可修复
- **fallback 链健康** — 双向 tier_chain 正常, 6 次 fallback 成功
- **无 NVCFPexecTimeout** — 超时问题已根治
- **所有参数健康** — 无调整空间
- **nv_gw 已达 floor** — 唯一 ATE 为 NVCF 上游故障, 非 config 可修复

### 3.2 ms_gw 判断

- **0 请求** — 完全空闲, 无优化空间

### 3.3 决策

**NOP** — nv_gw 已达 floor (98.5% SR), ms_gw 空闲, 无任何优化空间。HM1 停留在 R821 (85 轮落后), 等待 HM1 恢复提交新内容。

**24 轮连续 false trigger (R884→R907)**: 系统稳定, 无退化。当 HM1 恢复提交时, 需要重新收集数据 — 85 轮间隔可能带来显著变化。

## 4. 参数变更

无。零参数、零 compose、零 restart。

## 5. 评判

- 更少报错: ✅ (1 ATE, 与 R906 一致, 无新错误)
- 更快请求: ✅ (avg_ttfb=26.7s, 稳定)
- 超低延迟: ✅ (无退化)
- 稳定优先: ✅ (系统 98.5% SR, fallback 链健康)

---

## ⏳ 轮到HM1优化HM2