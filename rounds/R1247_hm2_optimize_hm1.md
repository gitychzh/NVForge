# HM2 Optimize HM1 — Round R1247

## 触发分析
- cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 GitHub commit: a11bb14, author=opc2_uname (HM2) — R1246 NOP
- HM1 本地 git log: 最新 R1206 (de04120), 41 轮落后于 HM2
- 判定: **FALSE TRIGGER** — HM1 未提交新内容, 自提交误触发

## 数据收集 (改前必有数据)

### 容器状态
- 容器: nv_gw, Up 26 minutes (healthy)
- 重启时间: 2026-07-13T14:33:57Z (26min ago)
- compose md5: 6e23559de1376d2d638f98f34a544139 (与 R1246 相同)

### 6h 总体
- 118req/94OK/24fail=79.7% SR

### 6h 错误分解
| error_type | cnt |
|---|---|
| zombie_empty_completion | 18 |
| all_tiers_exhausted | 5 |
| NVStream_IncompleteRead | 1 |

### 6h 按模型
| mapped_model | total | ok | err | sr_pct | avg_dur |
|---|---|---|---|---|---|
| glm5_2_nv | 113 | 90 | 23 | 79.6% | 25,333ms |
| dsv4p_nv | 5 | 4 | 1 | 80.0% | 51,182ms |

### 6h 按 upstream
| upstream_type | cnt | ok | err | avg_ttfb | avg_dur |
|---|---|---|---|---|---|
| nv_integrate | 103 | 85 | 18 | 19,811ms | 21,566ms |
| nvcf_pexec | 10 | 9 | 1 | 55,131ms | 55,132ms |
| (null) | 5 | 0 | 5 | 862ms | 69,177ms |

### 6h fallback
- fallback_occurred=f: 118 (100%) — 无 fallback 触发
- ms_gw: 9req/0OK — BrokenPipeError 模式

### 6h ATE tiers
- tiers_tried_count=1: 24, avg_dur=33,249ms

### 6h tier_attempts
- glm5_2_nv / IntegrateTimeout: 3, avg 90,826ms, max 91,140ms

### 6h 小时级 SR
| hour | total | ok | fail | sr_pct |
|---|---|---|---|---|
| 09:00 | 27 | 22 | 5 | 81.5% |
| 10:00 | 42 | 33 | 9 | 78.6% |
| 11:00 | 8 | 6 | 2 | 75.0% |
| 12:00 | 27 | 22 | 5 | 81.5% |
| 13:00 | 6 | 5 | 1 | 83.3% |
| 14:00 | 8 | 6 | 2 | 75.0% |

### 日志信号
- tier_chain=['glm5_2_nv'] (no fallback, 3model) — 预期 (FALLBACK_GRAPH={})
- NV-ZOMBIE-EMPTY 检测: 2 次 (最近 100 行)
- zombie_empty_completion: finish_reason=stop, content_chars=12 < 50, input_chars=171,799
- NV-MS-FB: 0 条 — ms_gw fallback 未触发 (BrokenPipeError 模式)

### 关键参数
- UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=210, TIER_COOLDOWN_S=15
- NVU_TIER_BUDGET_DSV4P_NV=72, NVU_TIER_BUDGET_GLM5_2_NV=96
- NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
- NVU_MS_GW_FALLBACK_TIMEOUT=200, NVU_PEER_FALLBACK_TIMEOUT=66
- NVU_PEER_FB_SKIP_MODELS=(空)
- KEY_COOLDOWN_S=25, KEY_AUTHFAIL_COOLDOWN_S=60
- NV_INTEGRATE_KEY_COOLDOWN_S=0, MIN_OUTBOUND_INTERVAL_S=0

## 决策
**NOP — 零参数, 零 compose 变更, 零容器重启**

18/24 失败 = zombie_empty_completion (75%) — code-level zombie detection, NVCF content-filter stop+12chars, gateway detection+error-chunk 正确. 不可配置修复.

5/24 失败 = all_tiers_exhausted (20.8%) — ms_gw BrokenPipeError 模式 (ms_gw 9req/0OK), streaming relay 同步缺陷. 不可配置修复.

1/24 失败 = NVStream_IncompleteRead (4.2%) — 网络瞬断, 不可配置修复.

所有参数已在 floor/optimal. BUDGET=210 充裕. 无 ms_gw fallback 超时瓶颈 (NVU_MS_GW_FALLBACK_TIMEOUT=200 < BUDGET=210). 无 peer-fallback budget 问题 (BUDGET-UPSTREAM=144 > PEER_FB=66). dsv4p_nv 5req/4OK=80% SR, pexec 路径正常.

铁律: 只改 HM1 不改 HM2.

## ⏳ 轮到HM1优化HM2
