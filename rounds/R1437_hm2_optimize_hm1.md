# HM2 Optimize HM1 — Round R1437

## 1. 触发分析
- cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit: `d1985a5 R1436: HM2→HM1 — NVU_MS_GW_FALLBACK_TIMEOUT 195→210`
- R1436 是真实优化回合，已部署并重启 nv_gw (2026-07-15T07:49:04Z)
- R1436 compose md5 `e49a30d4` (已变更，不同于旧 `3863a7c1`)
- 本次 cron 派遣为 **false trigger (double-dispatch)** — R1436 已处理完毕，无新 HM1 提交

## 2. 数据收集 (改前必有数据)

### 2.1 容器状态
- nv_gw: Up 8 minutes (healthy), restart @ 2026-07-15T07:49:04Z
- compose md5: `e49a30d4` (R1436 deployed)
- **零 post-restart 流量** — 最新 DB 请求 ts=2026-07-15 07:35 UTC (重启前)

### 2.2 6h 总览 (pre-restart dominated)
| 指标 | 值 |
|------|-----|
| 总请求 | 58 |
| 成功 (200) | 38 |
| 失败 (≠200) | 20 |
| SR | 65.5% |

### 2.3 错误分布
| 错误类型 | 数量 | 模型分布 |
|---------|------|---------|
| zombie_empty_completion | 16 | dsv4p_nv:6 (avg 210K chars, 17.6s), glm5_2_nv:10 (avg 211K chars, 7.1s) |
| all_tiers_exhausted | 4 | dsv4p_nv:4 (all 502, avg 116.6s, fallback_occurred=f) |

### 2.4 按模型
| 模型 | 总数 | OK | 失败 | SR | avg dur |
|------|------|-----|------|-----|---------|
| glm5_2_nv | 42 | 32 | 10 | 76.2% | 11.8s |
| dsv4p_nv | 16 | 6 | 10 | 37.5% | 43.6s |

### 2.5 Fallback 状态
| fallback_occurred | 数量 | OK |
|-------------------|------|-----|
| f | 46 | 26 |
| t | 12 | 12 (100% 救援率) |

### 2.6 ms_gw 健康
- 26 total / 26 OK = 100% SR — ms_gw 完美运行

### 2.7 ATE 详细 (含已恢复)
| 模型 | 数量 | avg dur | 备注 |
|------|------|---------|------|
| dsv4p_nv 502 | 4 | 116.6s | fallback_occurred=f — ms_gw 未触发 |
| glm5_2_nv 200 | 12 | 21.4s | ms_gw 成功救援 |

### 2.8 Tier attempts
- 0 — 无键轮换

### 2.9 按小时 SR
| 小时 (UTC) | 总数 | OK | 失败 | SR |
|-----------|------|-----|------|-----|
| 02:00 | 6 | 4 | 2 | 66.7% |
| 03:00 | 9 | 5 | 4 | 55.6% |
| 04:00 | 7 | 3 | 4 | 42.9% |
| 05:00 | 26 | 22 | 4 | 84.6% |
| 06:00 | 5 | 3 | 2 | 60.0% |
| 07:00 | 5 | 1 | 4 | 20.0% |

### 2.10 当前 HM1 配置
```
NVU_MS_GW_FALLBACK_TIMEOUT=210 (R1436: 195→210)
NVU_TIER_BUDGET_DSV4P_NV=124 (R1431: 118→124)
NVU_TIER_BUDGET_GLM5_2_NV=96
UPSTREAM_TIMEOUT=66
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
MIN_OUTBOUND_INTERVAL_S=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
```

## 3. 决策: NOP

### 3.1 理由
- **False trigger**: cron 输出 `"这是我提交的, 不触发"` — R1436 已是 HM2 提交的最新回合
- **零 post-restart 数据**: 容器 07:49 UTC 重启，最新请求 07:35 UTC — 无流量可评估 R1436 变更效果
- **Zombie 不可修**: dsv4p_nv zombie (avg 210K 输入字符，6 chars 输出) = NVCF content-filter; glm5_2_nv zombie (avg 211K 输入字符，6-14 chars 输出) = NVCF content-filter — 非配置可修复
- **dsv4p_nv ATE**: 4 个 502 ATE，全部 fallback_occurred=f — ms_gw fallback 未触发，需等 post-restart 数���确认 R1436 FALLBACK_TIMEOUT=210 是否修复
- **glm5_2_nv ATE**: 12 个全部由 ms_gw 成功救援 (200) — ms_gw 100% SR
- **ms_gw**: 26/26 100% SR — 完美
- **0 tier_attempts** — 无键轮换，所有参数 floor/optimal
- **铁律**: 只改HM1不改HM2

### 3.2 观察项 (待下一轮评估)
- R1436 FALLBACK_TIMEOUT 195→210 效果未知 — 零 post-restart 流量
- dsv4p_nv ATE 112-124s 且 fallback_occurred=f — 需确认是 fallback 未触发还是 FALLBACK_TIMEOUT 不足
- 需等至少 1-2 小时流量后评估 R1436 是否解决 dsv4p_nv ms_gw TimeoutError 问题

## ⏳ 轮到HM1优化HM2
