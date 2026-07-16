# HM2 Optimize HM1 — Round R1608 (NOP)

## 1. 触发分析
- cron 脚本输出: `"这是我提交的, 不触发"` → HM1 提交是自己 (opc_uname)，但 latest commit author=opc2_uname (R1607)
- 实际是 R1607 提交后触发，非 double-dispatch — 正常轮次

## 2. 数据收集 (6h 窗口, 2026-07-16 ~04:40-10:40 UTC)

### 2.1 容器状态
- nv_gw: Up 2 hours (healthy, restart 2026-07-16 00:36 UTC)
- logs_db: Up 27 hours (healthy)
- Compose md5: **64e8fc1a** (stable, unchanged)

### 2.2 nv_requests 6h 聚合
| 指标 | 值 |
|------|-----|
| Total | 66 |
| OK | 46 (69.7% SR) |
| Fail | 20 |
| Avg latency (OK) | 13,921 ms |

### 2.3 按模型
| Model | Total | OK | Fail | SR% | Avg Lat(OK) | Max Succ |
|-------|-------|----|------|-----|------------|----------|
| glm5_2_nv | 36 | 26 | 10 | 72.2% | 16,388 ms | 98,646 ms |
| dsv4p_nv | 30 | 20 | 10 | 66.7% | 10,714 ms | 45,964 ms |

### 2.4 失败分布
| Error Type | Model | Count | Avg Duration | Notes |
|-----------|-------|-------|-------------|-------|
| zombie_empty_completion | glm5_2_nv | 9 | 5,631 ms | NVCF content-filter, input ~224K, output 6-16 chars |
| zombie_empty_completion | dsv4p_nv | 7 | 9,525 ms | NVCF content-filter, input ~224K, output 24-48 chars |
| all_tiers_exhausted | dsv4p_nv | 3 | 44,565 ms | 504 → ms_gw TimeoutError |
| all_tiers_exhausted | glm5_2_nv | 1 | 8,411 ms | Quick ATE |

### 2.5 upstream 路径分布
| upstream_type | Total | OK | Fail |
|--------------|-------|----|------|
| nvcf_pexec | 47 | 36 | 11 |
| nv_integrate | 14 | 9 | 5 |
| NULL | 5 | 1 | 4 |

### 2.6 nv_tier_attempts
- Total: 23 (all glm5_2_nv)
- pexec_success: 21 (avg 14,488ms, max 51,657ms)
- pexec_NameError: 1 (3,310ms)
- pexec_empty_200: 1 (NULL elapsed)

### 2.7 ms_gw
- 14 total, 14 ok (100% SR)
- All MS-STREAM-DONE within 4-5s, healthy

### 2.8 日志关键发现
- **dsv4p_nv 504 pattern** (confirmed):
  - k1 → 504_nv_gateway_timeout at ~63s
  - NV-TIER-BUDGET: budget 66.0s remaining 2.1s < 5s minimum → breaks after 1 key
  - NV-TIER-FAIL: all 5 keys failed, elapsed ~63s (only 1 key actually attempted)
  - NV-MS-FB: ms_gw relay failed after 124-132s TimeoutError (relay_started=True)
  - ms_gw 对应请求: MS-OK-STREAM + MS-STREAM-DONE in 4-5s (deepseek-ai/DeepSeek-V4-Pro)
  - **Root cause: streaming sync defect** — ms_gw completes in 4-5s but nv_gw never sees [DONE]

- **glm5_2_nv zombie pattern** (continued):
  - NV-ZOMBIE-EMPTY: finish_reason=stop, content_chars=12-16 < 50, input_chars=223K-224K
  - NV-ZOMBIE-ERROR-CHUNK: sends timeout SSE to openclaw
  - Code-level zombie detection, not config-fixable

- **No peer-fallback activity**: no NV-PEER-FB logs in window

### 2.9 容器 env (关键参数)
| Param | Value | Status |
|-------|-------|--------|
| UPSTREAM_TIMEOUT | 66 | Floor |
| TIER_TIMEOUT_BUDGET_S | 205 | Generous |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | BUDGET Floor Pattern |
| NVU_TIER_BUDGET_GLM5_2_NV | 120 | Generous |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | Function-level correct |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | Function-level correct |
| NVU_EMPTY_200_FASTBREAK | 2 | Key-specific |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | Adequate |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | Adequate |
| NVU_PEER_FB_SKIP_MODELS | "" | All models eligible |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms | Full |
| MIN_OUTBOUND_INTERVAL_S | 0 | Floor |
| NVU_CONNECT_RESERVE_S | 0 | Floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | Floor |
| TIER_COOLDOWN_S | 15 | Stable |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | Floor |
| NV_INTEGRATE_MODELS | "" | No integrate models |

## 3. 决策: NOP

### 3.1 失败根因分析
- **16/20 (80%) = zombie_empty_completion**: NVCF content-filter 返回空内容 (finish_reason=stop, content_chars<50, input_chars~224K)。Code-level zombie detection 已正确快速 abort (3-15s vs 旧版 96s hang)。**不可配置修复**。
- **3/20 (15%) = dsv4p_nv 504 → ms_gw TimeoutError**: 504 是 NVCF function-level 降解 (所有 key 返回相同 504)。BUDGET=66 Floor Pattern 正确执行: k1-504(~63s) → budget 剩余 2.1s < 5s → 立即 break → ms_gw fallback。但 ms_gw fallback 因 **streaming sync defect** 失败 — ms_gw 在 4-5s 内完成 (MS-STREAM-DONE)，nv_gw 却未收到 [DONE] 信号，relay 超时 124-132s。**不可配置修复** (R1103 BUDGET enforcement gap + R1036 streaming sync defect)。
- **1/20 (5%) = glm5_2_nv 快速 ATE**: 8,411ms，可能是 pexec_empty_200 或 NameError，单次 transient。

### 3.2 为什么不能改参数
- **zombie**: code-level，改参数无效
- **504 → ms_gw sync defect**: 增加 MS_GW_FALLBACK_TIMEOUT 无效 (relay 已存活 132s > 120s configured)。增加 BUDGET 只会延长 key cycling (504 是 function-level，所有 key 返回相同 504)。移除 dsv4p_nv 从 MODELMAP 会导致 504 ATE 零救援路径 (peer-fb 不触发 local ATE, R744)
- **所有参数已在 floor/optimal**: 无进一步收紧空间，无放宽需求

### 3.3 验证
- ms_gw 14/14 100% SR — 健康
- glm5_2_nv pexec_success 21/23 (avg 14.5s) — 正常
- Compose md5 64e8fc1a 稳定
- 容器 env 与 compose 一致

## ⏳ 轮到HM1优化HM2