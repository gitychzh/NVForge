# R910: HM2→HM1 — NOP (false trigger, 27th consecutive, 68/67 98.5% 6h SR, nv_gw at floor, ms_gw idle, no optimization space)

> **触发**: cron 误触发 #27 (R884→R910 连续), 脚本输出 `这是我提交的, 不触发` — HM2 自提交 R909

## 1. 触发分析

- **cron 脚本输出**: `这是我提交的, 不触发`
- **最新 commit on HM2**: `6c928fb R909: HM2→HM1 — NOP (false trigger, 26th consecutive...)`
- **commit author**: `opc2_uname` (HM2 自提交 R909)
- **判定**: FALSE TRIGGER (double-dispatch) — HM1 未提交任何新内容, 预运行脚本已提交 R909 NOP, 上一轮 agent 已修复 symlink, cron 再次派遣

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
| fallback_tiers_used | {glm5_2_nv, dsv4p_nv} |

唯一 ATE 与 R906/R907/R908/R909 完全相同 (同一请求, 同一 6h 窗口) — 双 tier 耗尽 (NVCF 上游故障), 非 config 可修复。

### 2.3 Fallback 统计

| fallback_occurred | cnt |
|-------------------|-----|
| false | 62 |
| true | 6 |

6 次 fallback 成功 (glm5_2_nv→dsv4p_nv), 双向 fallback 链健康。

### 2.4 每小时 SR 分布

| slot (6h→1h) | total | ok | fail | sr_pct |
|-------------|-------|-----|------|--------|
| 12:00 UTC | 6 | 6 | 0 | 100.0 |
| 13:00 UTC | 33 | 32 | 1 | 97.0 |
| 14:00 UTC | 6 | 6 | 0 | 100.0 |
| 15:00 UTC | 6 | 6 | 0 | 100.0 |
| 16:00 UTC | 2 | 2 | 0 | 100.0 |
| 17:00 UTC | 15 | 15 | 0 | 100.0 |

### 2.5 Docker 日志 (最近 100 行)

```
NO_ERRORS_FOUND — 零 ERROR/WARN/exception/traceback, 日志极其干净
```

### 2.6 容器环境 (关键参数)

| 参数 | HM1 值 | 状态 |
|------|--------|------|
| UPSTREAM_TIMEOUT | 64 | floor |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 | floor |
| TIER_TIMEOUT_BUDGET_S | 114 | tuned |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 3 | tuned |
| KEY_COOLDOWN_S | 25 | tuned |
| TIER_COOLDOWN_S | 25 | tuned (单 tier 死参数) |
| NVU_FORCE_STREAM_UPGRADE | 0 | off |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | tuned |
| NVU_PEER_FALLBACK_ENABLED | 1 | on |
| NVU_PEER_FALLBACK_URL | http://100.109.57.26:40006 | HM2 |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | tuned |

### 2.7 ms_gw 6h

| 指标 | 值 |
|------|-----|
| 总请求 | 0 |
| 参数 | EMPTY_200_FASTBREAK_THRESHOLD=3, KEY_COOLDOWN_S=60, UPSTREAM_TIMEOUT=300 |

ms_gw 完全空闲 — 无优化空间。

## 3. 优化决策

### 3.1 nv_gw 判断

- **98.5% SR** — 与 R909 (98.5%) 完全一致, 无退化
- **1 ATE** — all_tiers_exhausted, 与 R906/R907/R908/R909 同一请求 (同一 6h 窗口), 非可修复
- **fallback 链健康** — 双向 tier_chain 正常, 6 次 fallback 成功
- **Docker 日志极干净** — 零错误
- **nv_gw 已达 floor** — 唯一 ATE 为 NVCF 上游故障, 非 config 可修复

### 3.2 决策

**NOP** — nv_gw 已达 floor (98.5% SR), ms_gw 空闲, 无任何优化空间。HM1 停留在 R821 (87 轮落后), 等待 HM1 恢复提交新内容。

**27 轮连续 false trigger (R884→R910)**: 系统极其稳定, 无退化。数据与 R909 完全一致 — 同一 6h 窗口, 同一 ATE, 同一 SR。当 HM1 恢复提交时, 需要重新收集数据 — 87 轮间隔可能带来显著变化。

## 4. 参数变更

无。零参数、零 compose、零 restart。

## 5. 评判

- 更少报错: ✅ (1 ATE, 与 R909 一致, 无新错误, Docker 日志零异常)
- 更快请求: ✅ (avg_ttfb=26.2s, fallback 健康, 无退化)
- 超低延迟: ✅ (p50=11.9s, p95=80.0s, 稳定)
- 稳定优先: ✅ (系统 98.5% SR, fallback 链健康, tier_chain 双向完整)

---

## ⏳ 轮到HM1优化HM2