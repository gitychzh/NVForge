# HM2 Optimize HM1 — Round R1186

## ⚠️ 触发分析

**cron 脚本输出**: `"这是我提交的, 不触发"` — **FALSE TRIGGER**

- 最新 commit: `aa27d14 opc2_uname: R1185: HM2→HM1 — NOP (false trigger, 53rd chain of R1133, zombie-only, all params floor/optimal, NVCF content-filter not config-fixable)`
- HM2 自提交, cron 脚本正确检测到 `"不触发"` 但仍被派遣
- HM1 本地 git log: `fbf0e43 R821` (365 轮落后)
- HM1 最新 HM1-authored commit: `7625e14` (R818, 2026-07-08)
- 本回合是第 54 轮 R1133 链式误触发

## 改前数据

### 容器状态
- nv_gw: Up 12 hours (healthy), 2026-07-11 03:03:24 CST
- ms_gw: Up 36 hours (healthy), 2026-07-09 00:01:24 CST
- logs_db: Up 7 days (healthy)

### 6h 请求统计（nv_requests）
| 指标 | 值 |
|------|-----|
| 总量 | 24 |
| 200 OK | 12 (50.0%) |
| 失败 | 12 (50.0%) |
| 全部流量 | nv_integrate (glm5_2_nv) |

### 错误分类
| error_type | cnt |
|------------|-----|
| zombie_empty_completion | 12 |

### 关键特征
- **0 ATE** (all_tiers_exhausted = 0)
- **0 fallback triggers** (fallback_occurred = false for all)
- **0 key_cycle_429s**
- **0 dsv4p_nv** 流量 (6h 窗口)
- **0 kimi_nv / minimax_m3_nv** 流量
- 全部 zombie: glm5_2_nv integrate, NVCF content-filter stop+12chars, 160K-178K input
- Gateway zombie detection + error-chunk 正确触发 (3-6s fast abort)
- tier_chain=['glm5_2_nv'] (no fallback, 3model) — R832 后预期正常状态

### Compose 状态
- md5: `7975939c245761e451a8813852dcb9bf` — 与 R1133 一致 (48h+ 未变)
- 所有参数 floor/optimal:
  - UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=198
  - TIER_COOLDOWN_S=15, KEY_COOLDOWN_S=25
  - NVU_TIER_BUDGET_DSV4P_NV=72, NVU_TIER_BUDGET_GLM5_2_NV=96
  - NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
  - NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms
  - NVU_MS_GW_FALLBACK_TIMEOUT=180, MIN_OUTBOUND_INTERVAL_S=0
  - KEY_AUTHFAIL_COOLDOWN_S=60, NVU_CONNECT_RESERVE_S=0
  - NVU_PEER_FB_SKIP_MODELS=glm5_2_nv

### ms_gw 状态
- 6h 流量: 接近零 (最后一次活动 ~2h 前)
- 所有 MS-OK-STREAM 成功
- 1× MS-STREAM-CLIENT-EOF (BrokenPipeError, dsv4p_ms) — R1088 模式但流量极低不具可操作性

## 决策: NOP

**理由**: 零真实错误。所有 12 次失败均为 zombie_empty_completion — NVCF content-filter 在 glm5_2_nv integrate 路径上返回 stop+12chars（160K-178K input）。Gateway 在 3-6s 内正确检测并 abort（vs 旧 96s hang）。此行为是 NVCF 上游内容过滤问题，非配置可修复。代码级 zombie detection 已正确部署和运行。

**优化空间**: 无。所有参数已 floor/optimal。compose md5 48h+ 未变。0 ATE、0 fallback 触发、0 key_cycle_429s。dsv4p_nv 0 流量。ms_gw 近零流量。无二级优化机会。

**参数变更**: 无。容器重启: 0。compose 变更: 0。

## ⏳ 轮到HM1优化HM2
