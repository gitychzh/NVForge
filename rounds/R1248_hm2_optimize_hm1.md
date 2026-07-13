# HM2 Optimize HM1 — Round R1248

## 触发分析
- cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 GitHub commit: c41dfe6 (R1247: HM2→HM1 NOP)
- HM1 未提交新内容 — R1247 为 HM2 自提交
- 判定: **FALSE TRIGGER** — 误触发

## 数据收集 (改前必有数据)

### 容器状态
- 容器: nv_gw, Up 34 minutes (healthy)
- ���启时间: 2026-07-13T14:33:57Z
- compose md5: 6e23559de1376d2d638f98f34a544139 (与 R1247 相同)

### 6h 总体
- 112req/89OK/23fail=79.5% SR

### 6h 错误分解
| error_type | cnt |
|---|---|
| zombie_empty_completion | 18 |
| all_tiers_exhausted | 4 |
| NVStream_IncompleteRead | 1 |

### 6h 按模型
| mapped_model | cnt | ok | err | sr_pct | avg_dur |
|---|---|---|---|---|---|
| glm5_2_nv | 107 | 85 | 22 | 79.4% | 21,086ms |
| dsv4p_nv | 5 | 4 | 1 | 80.0% | 51,182ms |

### 6h 按 upstream
| upstream_type | cnt | ok | err | avg_ttfb | avg_dur |
|---|---|---|---|---|---|
| nv_integrate | 99 | 81 | 18 | 18,085ms | 19,590ms |
| nvcf_pexec | 9 | 8 | 1 | 45,960ms | 45,961ms |
| (null) | 4 | 0 | 4 | 890ms | 39,756ms |

### 6h fallback
- fallback_occurred=f: 112 (100%) — 无 fallback 触发
- ms_gw: 8req/0OK — BrokenPipeError 模式

### 6h tier_attempts
- glm5_2_nv / IntegrateTimeout: 2, avg 90,804ms, max 91,140ms

### 6h 小时级 SR
| hour | total | ok | fail | sr_pct |
|---|---|---|---|---|
| 09:00 | 18 | 15 | 3 | 83.3% |
| 10:00 | 42 | 33 | 9 | 78.6% |
| 11:00 | 8 | 6 | 2 | 75.0% |
| 12:00 | 27 | 22 | 5 | 81.5% |
| 13:00 | 6 | 5 | 1 | 83.3% |
| 14:00 | 8 | 6 | 2 | 75.0% |
| 15:00 | 3 | 2 | 1 | 66.7% |

### 日志信号
- tier_chain=['glm5_2_nv'] (no fallback, 3model) — 预期
- NV-ZOMBIE-EMPTY 检测: 2 次 (最近 100 行)
- zombie_empty_completion: finish_reason=stop, content_chars=12 < 50, input_chars=171,799
- NV-PEER-FB: 0 条 — peer-fallback 未触发
- NV-MS-FB: 0 条 — ms_gw fallback 未触发 (BrokenPipeError 模式)
- ms_gw direct: 正常 (MS-OK-STREAM/MS-STREAM-DONE 多条, ZHIPUAI/GLM-5.2)

### 关键参数
- UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=210, TIER_COOLDOWN_S=15
- NVU_TIER_BUDGET_DSV4P_NV=72, NVU_TIER_BUDGET_GLM5_2_NV=96
- NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
- NVU_EMPTY_200_FASTBREAK=2 (R1031, 但 R1039 确认 pexec 路径不生效)
- NVU_MS_GW_FALLBACK_TIMEOUT=200, NVU_PEER_FALLBACK_TIMEOUT=66
- NVU_PEER_FB_SKIP_MODELS=空 (R1000), NVU_PEER_FALLBACK_ENABLED=1
- KEY_COOLDOWN_S=25, KEY_AUTHFAIL_COOLDOWN_S=60
- NV_INTEGRATE_KEY_COOLDOWN_S=0, MIN_OUTBOUND_INTERVAL_S=0

## 决策
**NOP — 零参数, 零 compose 变更, 零容器重启**

18/23 失败 = zombie_empty_completion (78.3%) — code-level zombie detection, NVCF content-filter stop+12chars, gateway detection+error-chunk 正确. 不可配置修复.

4/23 失败 = all_tiers_exhausted (17.4%) — ms_gw BrokenPipeError 模式 (ms_gw 8req/0OK via nv_gw→ms_gw path), streaming relay 同步缺陷. ms_gw direct 正常 (MS-OK-STREAM 多条), 证明 ms_gw 本身健康. BrokenPipeError 是 nv_gw→ms_gw relay 层面的缺陷. 不可配置修复.

1/23 失败 = NVStream_IncompleteRead (4.3%) — 网络瞬断, 不可配置修复.

所有参数在 floor/optimal. BUDGET=210 充裕. compose md5 连续 2 轮不变. 无 peer-fallback 或 ms_gw-fallback 触发 (无 ATE 触发 fallback 链). 数据与 R1247 高度一致 (79.5% vs 79.7% SR, 相同错误模式).

铁律: 只改 HM1 不改 HM2.

## ⏳ 轮到HM1优化HM2
