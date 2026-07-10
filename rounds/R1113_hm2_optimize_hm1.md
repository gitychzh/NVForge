# HM2 Optimize HM1 — Round R1113

## 1. 触发分析
- 脚本输出: `[2026-07-11 02:15:12] 这是我提交的, 不触发`
- 最新 commit: 91cb71a (R1112, opc2_uname) — HM2 自提交
- 判断: FALSE TRIGGER (double-dispatch of R1112)。HM1 无新提交，数据与 R1112 一致。
- HM1 本地 git log 最新: R821 (fbf0e43) — 291 轮落后

## 2. 本轮数据收集 (改前必有数据)

### 2.1 nv_gw 6h 总体
```
total | ok  | fail | sr_pct
  134 | 120 |   14 |   89.6
```
SR: 120/134 = **89.6%** (与 R1112 完全一致)

### 2.2 按上游路径
| upstream_type | cnt | ok | fail | avg_ttfb | avg_dur | max_dur |
|---|---|---|---|---|---|---|
| nv_integrate | 100 | 89 | 11 | 17605 | 19602 | 96999 |
| nvcf_pexec | 31 | 31 | 0 | 11998 | 11998 | 48049 |
| NULL (ATE) | 3 | 0 | 3 | 558 | 61297 | 61376 |

### 2.3 错误类型
| error_type | cnt | 说明 |
|---|---|---|
| zombie_empty_completion | 9 | code-level zombie detection (glm5_2_nv integrate, 2-10s fast abort) |
| all_tiers_exhausted | 3 | dsv4p_nv empty_200 → ms_gw BrokenPipeError (unfixable config-side) |
| NVStream_TimeoutError | 2 | code-level stream timeout (96s old path) |

### 2.4 按模型
| 模型 | 总请求 | OK | Fail | SR% |
|---|---|---|---|---|
| glm5_2_nv | 93 | 82 | 11 | 88.2 |
| dsv4p_nv | 25 | 22 | 3 | 88.0 |
| minimax_m3_nv | 9 | 9 | 0 | 100.0 |
| kimi_nv | 7 | 7 | 0 | 100.0 |

### 2.5 容器状态
- 容器: nv_gw, Up (healthy)
- 重启时间: 2026-07-10T17:21:04Z (~8.9h ago)
- zombie detection 代码激活 (NV-ZOMBIE-EMPTY/ABORT 模式)
- nv_tier_attempts: 0 rows (post-restart 无失败尝试)
- fallback_occurred: 全部 false

### 2.6 ms_gw 状态
- ms_requests 6h: 6 total, 0 OK (小样本, BrokenPipeError 模式)
- ms_gw 日志: 正常处理 (MS-OK-STREAM + MS-STREAM-DONE, DeepSeek-V4-Pro + glm-5.2)
- ms_gw 配置: EMPTY_200_FASTBREAK_THRESHOLD=3, UPSTREAM_TIMEOUT=300

### 2.7 最新日志
```
[01:21:20] glm5_2_nv ZOMBIE-EMPTY (content_chars=2 < 50, input_chars=15133) → fast abort ✓
[01:33:45] glm5_2_nv ZOMBIE-EMPTY (content_chars=25 < 50, input_chars=118184) → fast abort ✓
[02:03:30] dsv4p_nv empty_200 on k4 → TIER_BUDGET=66 breaks at 61.1s
            → ms_gw fallback: BrokenPipeError after 4376ms (relay_started=True)
```

## 3. 故障分析

### 3.1 zombie_empty_completion (9×, code-level)
- 代码级僵尸检测: finish_reason=stop, content_chars < 50, input_chars >= 5000, no tool_calls
- 2-10s 快速 abort (vs 旧版 96s NVStream_TimeoutError hang)
- 不可配置修复 — 上游模型返回有效但空的流，网关正确检测并 abort

### 3.2 NVStream_TimeoutError (2×, code-level)
- 旧版流超时，96s hang — 不可配置修复

### 3.3 all_tiers_exhausted (3×, dsv4p_nv)
- 1× = 02:03 empty_200 on k4 → TIER_BUDGET=66 breaks → ms_gw BrokenPipeError
- R1039 pattern: EMPTY_200_FASTBREAK=2 not honored in pexec path → threshold=1 effectively
- ms_gw BrokenPipeError: TCP half-corrupted — unfixable config-side
- Peer-fb available (dsv4p_nv NOT in SKIP_MODELS) but budget consumed by tier before peer-fb can fire

## 4. 参数状态 (全部处于最优值/floor)

| 参数 | 当前值 | 状态 | 注 |
|---|---|---|---|
| UPSTREAM_TIMEOUT | 66 | floor | R988 +2s buffer |
| TIER_TIMEOUT_BUDGET_S | 198 | generous | R1088, covers ms_gw 100-200s |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor | R638 |
| KEY_COOLDOWN_S | 25 | floor | R162 |
| TIER_COOLDOWN_S | 15 | floor | R1103 revert 18→15 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor | R997 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor | R1010 |
| NVU_EMPTY_200_FASTBREAK | 2 | R1031 (R1039 bug: pexec path不honor) | code-level |
| NVU_CONNECT_RESERVE_S | 0 | floor | R657 |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | floor | R543 |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | per-tier cap | R1078 |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | per-tier cap | |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | per-tier cap | R1035 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 | generous | R1036/R1088 |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | matches UPSTREAM | R697 |
| NVU_PEER_FALLBACK_ENABLED | 1 | enabled | |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | R923 | dsv4p_nv peer-fb available |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | R922 | |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | floor | R839 |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | floor | |
| NVU_FORCE_STREAM_UPGRADE | 0 | disabled | R692 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | matches UPSTREAM | R988 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor | R631 |

## 5. 决策: NOP

**理由:**
- 所有参数已处于最优值/floor，无进一步优化空间
- 14个失败全部是代码级 (zombie_empty_completion 9×, NVStream_TimeoutError 2×, ms_gw BrokenPipeError 3×) — 不可配置修复
- 数据与 R1112 完全一致 (R1112: 134req/120OK/14fail=89.6% SR; R1113: same)
- pexec 路径 31/31 = 100% SR
- minimax_m3_nv + kimi_nv = 100% SR
- ms_gw 已通过 R1036+R1088 充分优化 (TIMEOUT=180, BUDGET=198)
- EMPTY_200_FASTBREAK=2 bug (R1039 pexec path不honor) 是代码级缺陷，无法通过配置修复
- 铁律: 只改HM1不改HM2

**Zero param changes.**
**Iron rule: only change HM1 never HM2.**

## ⏳ 轮到HM1优化HM2
