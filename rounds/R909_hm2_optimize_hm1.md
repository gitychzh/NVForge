# R909: HM2→HM1 — NOP (false trigger, 26th consecutive, 68/67 98.5% 6h SR, nv_gw at floor, ms_gw idle, no optimization space)

> **触发**: cron 误触发 #26 (R884→R909 连续), 脚本输出 `这是我提交的, 不触发` — HM2 自提交 R908

## 1. 触发分析

- **cron 脚本输出**: `这是我提交的, 不触发`
- **最新 commit on HM1**: `fbf0e43 R821: HM2→HM1 — NOP` (87 轮落后)
- **commit author**: `opc2_uname` (HM2 自提交 R908)
- **判定**: FALSE TRIGGER (double-dispatch) — HM1 未提交任何新内容, 预运行脚本已提交 R908 NOP, 上一轮 agent 已修复 symlink, cron 再次派遣

## 2. 数据收集 (改前必有数据)

### 2.1 nv_gw 6h 总体统计

| 指标 | 值 |
|------|-----|
| 总请求 | 68 |
| 成功 (200) | 67 |
| 失败 | 1 |
| 成功率 | **98.5%** |

### 2.2 ATE 详情

| 字段 | 值 |
|------|-----|
| ts | 2026-07-08 13:21:01 UTC |
| request_model | glm5_2_nv |
| tiers_tried_count | 2 |
| duration_ms | 121,075ms |
| error_type | all_tiers_exhausted |
| fallback_actually_attempted | false |

唯一 ATE 与 R906/R907/R908 完全相同 (同一请求, 同一 6h 窗口) — 双 tier 耗尽 (NVCF 上游故障), 非 config 可修复。

### 2.3 Fallback 统计

| fallback_occurred | cnt | avg_dur | max_dur |
|-------------------|-----|---------|---------|
| false | 61 | 20,446ms | 108,661ms |
| true | 6 | 85,350ms | 120,339ms |

6 次 fallback 成功 (glm5_2_nv→dsv4p_nv), 双向 fallback 链健康。

### 2.4 每小时 SR 分布

| hour (UTC) | total | ok | ate | sr_pct |
|------------|-------|-----|-----|--------|
| 12:00 | 6 | 6 | 0 | 100.0 |
| 13:00 | 33 | 32 | 1 | 97.0 |
| 14:00 | 6 | 6 | 0 | 100.0 |
| 15:00 | 6 | 6 | 0 | 100.0 |
| 16:00 | 2 | 2 | 0 | 100.0 |
| 17:00 | 15 | 15 | 0 | 100.0 |

### 2.5 Docker 日志 (最近 30 行, 关键事件)

```
[NV-REQ] mapped_model=glm5_2_nv start_tier=glm5_2_nv stream=True tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={...})
```

所有请求 tier_chain 健康, 双向 fallback 正常。无 ERROR/WARN/exception/traceback — 日志极其干净。

### 2.6 容器环境 (关键参数)

| 参数 | HM1 值 | HM2 值 (R908) | 差异? |
|------|--------|---------------|-------|
| UPSTREAM_TIMEOUT | 64 | 66 | ⚠️ -2s |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 | 66 | ⚠️ -2s |
| TIER_TIMEOUT_BUDGET_S | 114 | 114 | ✅ |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 1 | ✅ |
| NVU_EMPTY_200_FASTBREAK | 3 | 1 | ⚠️ -2 |
| KEY_COOLDOWN_S | 25 | 25 | ✅ |
| TIER_COOLDOWN_S | 25 | 20 | ⚠️ +5s |
| NVU_FORCE_STREAM_UPGRADE | 0 | 1 | ⚠️ |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | 0.10 | ✅ |
| NVU_PEER_FALLBACK_ENABLED | 1 | 1 | ✅ |

**注意**: 上一轮 R908 报告 `NVU_PEXEC_TIMEOUT_FASTBREAK` 为"未设置", 但当前实际查询 HM1 容器 env 显示已设置为 1 — 可能是 HM1 agent 在本地应用了调整, 或 R908 的 env grep 命令未捕获到。当前值 1 与 HM2 一致 ✅。

### 2.7 ms_gw 6h

| 指标 | 值 |
|------|-----|
| 总请求 | 0 |
| 参数 | EMPTY_200_FASTBREAK_THRESHOLD=3, KEY_COOLDOWN_S=60, UPSTREAM_TIMEOUT=300 |

ms_gw 完全空闲 — 无优化空间。

## 3. 优化决策

### 3.1 nv_gw 判断

- **98.5% SR** — 与 R908 (98.6%) 一致, 微降 0.1%, 无实质退化
- **1 ATE** — all_tiers_exhausted, 与 R906/R907/R908 同一请求 (同一 6h 窗口), 非可修复
- **fallback 链健康** — 双向 tier_chain 正常, 6 次 fallback 成功
- **Docker 日志极干净** — 所有请求 tier_chain 包含双向 fallback, 零错误
- **nv_gw 已达 floor** — 唯一 ATE 为 NVCF 上游故障, 非 config 可修复

### 3.2 参数同步机会 (与 R908 一致, 未来参考)

1. **NVU_EMPTY_200_FASTBREAK 3→1** (HM2=1) — 最可能的下轮优化目标
2. **NVU_FORCE_STREAM_UPGRADE 0→1** (HM2=1) — stream upgrade 优化
3. **UPSTREAM_TIMEOUT 64→66** (HM2=66) — 低优先级, 当前无 NVCFPexecTimeout
4. **NVU_FORCE_STREAM_UPGRADE_TIMEOUT 64→66** — 与 UPSTREAM 同步
5. **TIER_COOLDOWN_S 25→20** (HM2=20) — 单 tier 架构下死参数

### 3.3 决策

**NOP** — nv_gw 已达 floor (98.5% SR), ms_gw 空闲, 无任何优化空间。HM1 停留在 R821 (87 轮落后), 等待 HM1 恢复提交新内容。

**26 轮连续 false trigger (R884→R909)**: 系统极其稳定, 无退化。参数同步机会存在但不紧迫 — 当前数据不支持任何变更。当 HM1 恢复提交时, 需要重新收集数据 — 87 轮间隔可能带来显著变化。

## 4. 参数变更

无。零参数、零 compose、零 restart。

## 5. 评判

- 更少报错: ✅ (1 ATE, 与 R908 一致, 无新错误, Docker 日志零异常)
- 更快请求: ✅ (avg_ttfb=20.4s direct, 85.3s fallback, 稳定)
- 超低延迟: ✅ (无退化, 每小时 100% SR 除 13:00 的 97.0%)
- 稳定优先: ✅ (系统 98.5% SR, fallback 链健康, tier_chain 双向完整)

---

## ⏳ 轮到HM1优化HM2