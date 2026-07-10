# HM2 Optimize HM1 — Round R1111

## 1. 触发分析
- 脚本输出: `[2026-07-11 01:55:12] 这是我提交的, 不触发`
- 最新 commit: R1110 (opc2_uname/NOP) — 预运行脚本已提交
- 判断: FALSE TRIGGER (double-dispatch)。R1110 已正确标记 NOP，symlink 已指向 R1110，cron 再次派遣同一触发。

## 2. 本轮数据收集 (改前必有数据)

### 2.1 nv_gw 6h 总体
```
total | ok  | err | sr_pct
  129 | 116 |  13 |   89.9
```

### 2.2 按上游路径
| upstream_type | cnt | ok | err | avg_ttfb | avg_dur | max_dur |
|---|---|---|---|---|---|---|
| nv_integrate | 100 | 89 | 11 | 17468 | 19407 | 96999 |
| nvcf_pexec | 27 | 27 | 0 | 11696 | 11696 | 48049 |
| NULL | 2 | 0 | 2 | 501 | 61375 | 61376 |

### 2.3 错误类型
| error_type | cnt |
|---|---|
| zombie_empty_completion | 9 |
| NVStream_TimeoutError | 2 |
| all_tiers_exhausted | 2 |

### 2.4 按模型
| mapped_model | cnt | ok | err | sr_pct | avg_dur |
|---|---|---|---|---|---|
| glm5_2_nv | 94 | 83 | 11 | 88.3 | 19615 |
| dsv4p_nv | 19 | 17 | 2 | 89.5 | 19990 |
| minimax_m3_nv | 9 | 9 | 0 | 100.0 | 14483 |
| kimi_nv | 7 | 7 | 0 | 100.0 | 3605 |

### 2.5 fallback
fallback_occurred=f: 129 (ALL — no fallback triggered)

### 2.6 nv_tier_attempts
0 rows — zombie detection happens before key exhaustion, no tier cycling.

### 2.7 容器状态
- 重启时间: 2026-07-10T17:21:04Z (~8.5h ago)
- tier_chain: `['glm5_2_nv'] (no fallback, 3model)` — expected (FALLBACK_GRAPH={})

### 2.8 ms_gw 状态
- EMPTY_200_FASTBREAK_THRESHOLD=3 (R900 floor)
- 200行日志: 74 cycle/FASTBREAK/VARIANT-EXHAUSTED, 46 stream_no_data_lines, 9 BrokenPipeError/FAIL
- 大部分 cycle 来自 dsv4p_ms (DeepSeek stream_no_data_lines → FASTBREAK=3 → variant切换 → 成功)
- 0 TimeoutError, 健康

## 3. 故障分析

### 3.1 zombie_empty_completion (9×, code-level)
- 代码级僵尸检测功能: finish_reason=stop, content_chars < 50, input_chars >= 5000, no tool_calls
- 2-10s 快速 abort (vs 旧版 96s NVStream_TimeoutError hang)
- 日志: `[NV-ZOMBIE-EMPTY]` + `[NV-ZOMBIE-ERROR-CHUNK]` → 触发 openclaw fallback
- 不可配置修复 — 上游模型返回有效但空的流，网关正确检测并 abort

### 3.2 NVStream_TimeoutError (2×, code-level)
- 旧版流超时，96s hang
- 不可配置修复

### 3.3 all_tiers_exhausted (2×, NULL upstream_type)
- duration ~61s, 可能是 pre-restart 残留或 NVCF 上游全耗尽
- NVU_PEER_FB_SKIP_MODELS=glm5_2_nv (glm5_2 走 peer-fb)
- dsv4p_nv 不在 SKIP_MODELS → peer-fb 已启用 → ms_gw fallback TIMEOUT=180 充裕

## 4. 参数状态 (全部处于最优值)

| 参数 | 当前值 | 状态 |
|---|---|---|
| UPSTREAM_TIMEOUT | 66 | floor |
| TIER_TIMEOUT_BUDGET_S | 198 | generous (覆盖 ms_gw fallback) |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| KEY_COOLDOWN_S | 25 | floor |
| TIER_COOLDOWN_S | 15 | floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | R1031 (R1039 bug: pexec path不honor) |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | floor |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | per-tier cap |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | per-tier cap |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | per-tier cap |
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 | generous |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | matches UPSTREAM |
| NVU_PEER_FALLBACK_ENABLED | 1 | enabled |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | R923 |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | R922 |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | floor |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | floor |
| NVU_FORCE_STREAM_UPGRADE | 0 | disabled |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | matches UPSTREAM |
| ms_gw: EMPTY_200_FASTBREAK_THRESHOLD | 3 | R900 floor |
| ms_gw: KEY_COOLDOWN_S | 60 | default |
| ms_gw: VARIANT_COOLDOWN_S | 30 | default |
| ms_gw: ALL_EXHAUSTED_COOLDOWN_S | 30 | default |

## 5. 决策: NOP

**理由:**
- 所有参数已处于最优值/floor，无优化空间
- 13个失败全部是代码级 (zombie_empty_completion, NVStream_TimeoutError) 或上游耗尽 (all_tiers_exhausted)
- 数据与 R1110 完全一致 (129req/116OK/13fail=89.9% SR)
- ms_gw 已在 floor (FASTBREAK=3)，无进一步优化空间
- pexec 路径 27/27 = 100% SR
- minimax_m3_nv + kimi_nv = 100% SR
- 铁律: 只改HM1不改HM2

**Zero param changes.**
**Iron rule: only change HM1 never HM2.**

## ⏳ 轮到HM1优化HM2
