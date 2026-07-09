# HM2 Optimize HM1 — Round R1027

> **NOP (false trigger, double-dispatch)**: 所有参数已在floor/optimal, 数据不支持任何变更.

## 1. 触发分析
cron脚本输出: "这是我提交的, 不触发"
- 最新commit author = opc2_uname (HM2自己提交的R1026)
- R1026 symlink已正确指向 `rounds/R1026_hm2_optimize_hm1.md`
- 本次为double-dispatch: cron在R1026已处理后又派遣了agent
- 判定: FALSE TRIGGER → 仍需收集数据, 但无参数变更

## 2. HM1容器状态
| 项目 | 值 |
|------|-----|
| nv_gw 重启时间 | 2026-07-09T19:14:28Z (~5.5h前) |
| ms_gw 状态 | 健康, 所有cooldown为空 |
| FALLBACK_GRAPH | {} (空, R832设计 — ms_gw同模型fallback) |
| tier_chain | 全部单模型 `(no fallback, 3model)` — 预期常态 |

## 3. HM1 nv_gw 关键参数 (全部floor/optimal)
| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | ─ |
| TIER_TIMEOUT_BUDGET_S | 110 | ─ |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 1 | floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| TIER_COOLDOWN_S | 18 | floor |
| KEY_COOLDOWN_S | 25 | floor |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | defensive |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.10 | floor |
| NVU_FORCE_STREAM_UPGRADE | 0 | disabled |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | ─ |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv,dsv4p_nv | defensive |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | ─ |

## 4. HM1 ms_gw 参数
| 参数 | 值 |
|------|-----|
| EMPTY_200_FASTBREAK_THRESHOLD | 3 |
| KEY_COOLDOWN_S | 60 |
| VARIANT_COOLDOWN_S | 30 |
| ALL_EXHAUSTED_COOLDOWN_S | 30 |
| MIN_OUTBOUND_INTERVAL_S | 1.0 |
| UPSTREAM_TIMEOUT | 300 |

## 5. 6h DB数据
| 指标 | 值 |
|------|-----|
| 总请求 | 419 |
| 成功 (200) | 390 (93.1%) |
| 失败 | 29 (6.9%) |

### 5.1 按路径分组
| 路径 | 请求数 | 成功 | SR |
|------|--------|------|-----|
| nv_integrate | 277 | 271 | 97.8% |
| nvcf_pexec | 113 | 113 | **100%** |
| NULL (ATE) | 29 | 6 | 20.7% |

### 5.2 错误分布 (6h)
| 错误类型 | 数量 |
|----------|------|
| all_tiers_exhausted | 23 |
| NVStream_TimeoutError | 3 |
| stream_total_deadline | 3 |

### 5.3 24h错误全景
| 错误类型 | 数量 |
|----------|------|
| all_tiers_exhausted | 40 |
| NVStream_TimeoutError | 3 |
| stream_total_deadline | 3 |

### 5.4 ATE详情 (tiers_tried_count)
全部29个ATE均为 `tiers_tried_count=1` (单tier耗尽), `fallback_actually_attempted=false`

### 5.5 Tier Attempts (6h)
仅1条: `minimax_m3_nv` IntegrateTimeout 90,762ms

### 5.6 按小时SR
| 小时 (UTC) | 总请求 | 成功 | ATE | SR |
|-----------|--------|------|-----|-----|
| 14:00 | 4 | 3 | 1 | 75.0% |
| 15:00 | 19 | 18 | 1 | 94.7% |
| 16:00 | 47 | 43 | 4 | 91.5% |
| 17:00 | 65 | 59 | 6 | 90.8% |
| 18:00 | 62 | 55 | 7 | 88.7% |
| 19:00 | 211 | 203 | 8 | 96.2% |
| 20:00 | 11 | 9 | 2 | 81.8% |

## 6. nv_gw 日志关键事件
- `tier_chain=['glm5_2_nv'] (no fallback, 3model)` — 预期常态 (R832 FALLBACK_GRAPH={})
- `tier_chain=['dsv4p_nv'] (no fallback, 3model)` — 预期常态
- glm5_2_nv integrate: 全部一次成功 (k1-k5轮转), 零timeout
- 1次 dsv4p_nv ATE: all 5 keys failed (empty200=1, 61,244ms) → ms_gw fallback BrokenPipeError
- 1次 NVStream_TimeoutError: glm5_2_nv integrate 94,359ms后超时
- ms_gw: 全部 MS-OK-STREAM / MS-STREAM-DONE, 1次 MS-RELAY-ERR BrokenPipe (瞬时)

## 7. 决策: NOP — 零参数变更
- nvcf_pexec 100% SR (113/113), 零NVCFPexecTimeout → UPSTREAM_TIMEOUT未binding
- 所有FASTBREAK=1 (floor) → 无法再降低
- 所有cooldown参数在floor → 无法再降低
- MIN_OUTBOUND_INTERVAL_S=0 → floor
- 23个ATE均为NVCF upstream function-level问题, 非config-fixable
- 3个NVStreamTimeout + 3个stream_deadline为streaming层问题, 非config-fixable
- ms_gw健康, 无优化空间
- 铁律: 只改HM1不改HM2 — 无可改参数

## ⏳ 轮到HM1优化HM2
