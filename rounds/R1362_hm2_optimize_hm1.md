# HM2 Optimize HM1 — Round R1362 (NOP, false trigger, double-dispatch)

## 触发分析
- cron脚本输出: "这是我提交的, 不触发"
- 最新commit: d0f89e8 (R1361, author=opc2_uname, HM2)
- **判定: false trigger → double-dispatch (522nd chain of R1133)**
- R1361 pre-run script已提交NOP, symlink已正确 → 本轮double-dispatch
- HM1 git log无新提交, R1361已是最新

## 数据收集 (改前必有数据 — 2026-07-14 21:25 UTC)

### 6h 总体统计
| 指标 | 数值 |
|------|------|
| 总请求 | 28 |
| 成功(200) | 20 |
| 失败(502) | 8 |
| SR | 71.4% |

### 错误分类
| 错误类型 | 数量 |
|----------|------|
| zombie_empty_completion | 8 |
| all_tiers_exhausted | 0 |
| 其他 | 0 |

### 按模型统计
| 模型 | 请求 | OK | 失败 | SR | 平均延迟 |
|------|------|-----|------|------|---------|
| glm5_2_nv | 28 | 20 | 8 | 71.4% | 11,300ms |

### 按路径统计
| 路径 | 请求 | OK | 失败 |
|------|------|-----|------|
| nv_integrate | 28 | 20 | 8 |

### 每小时SR趋势
| 小时 (UTC) | 请求 | OK | 失败 | SR |
|------------|------|-----|------|-----|
| 07:00 | 2 | 1 | 1 | 50.0% |
| 08:00 | 5 | 4 | 1 | 80.0% |
| 09:00 | 5 | 4 | 1 | 80.0% |
| 10:00 | 4 | 3 | 1 | 75.0% |
| 11:00 | 5 | 4 | 1 | 80.0% |
| 12:00 | 4 | 2 | 2 | 50.0% |
| 13:00 | 3 | 2 | 1 | 66.7% |

### 最近10条请求
| ts | mapped_model | status | duration_ms | error_type | total_input_chars | output_tokens |
|----|-------------|--------|-------------|------------|-------------------|---------------|
| 13:03:37 | glm5_2_nv | 502 | 14667 | zombie_empty_completion | 191519 | 20 |
| 13:03:28 | glm5_2_nv | 200 | 9076 | - | 190827 | 58 |
| 13:03:20 | glm5_2_nv | 200 | 7462 | - | 190321 | 75 |
| 12:33:31 | glm5_2_nv | 502 | 6418 | zombie_empty_completion | 190234 | 6 |
| 12:33:20 | glm5_2_nv | 200 | 10400 | - | 189690 | 77 |
| 12:03:25 | glm5_2_nv | 502 | 5370 | zombie_empty_completion | 190234 | 6 |
| 12:03:20 | glm5_2_nv | 200 | 4944 | - | 189690 | 77 |
| 11:33:46 | glm5_2_nv | 200 | 7482 | - | 188806 | 21 |
| 11:33:34 | glm5_2_nv | 200 | 11324 | - | 188050 | 65 |
| 11:33:20 | glm5_2_nv | 200 | 14342 | - | 187538 | 77 |

### Zombie 详情
- 8 zombie_empty_completion, 全部 glm5_2_nv integrate
- 平均 input_chars: 188,110 (典型 ~190K)
- 平均 duration: 10,921ms
- 0 ATE, 0 timeout, 0 empty_200, 0 tier_attempts, 0 fallback
- 0 dsv4p_nv, 0 kimi_nv, 0 minimax_m3_nv traffic
- ms_gw: 0/0
- nv_gw日志: NV-ZOMBIE-EMPTY + NV-ZOMBIE-ERROR-CHUNK 正常触发，每次zombie在~3-15s内检测并返回502

### 容器env (关键参数)
| 参数 | 值 |
|------|-----|
| UPSTREAM_TIMEOUT | 66 |
| TIER_TIMEOUT_BUDGET_S | 205 |
| TIER_COOLDOWN_S | 15 |
| KEY_COOLDOWN_S | 25 |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 |
| NVU_TIER_BUDGET_DSV4P_NV | 94 |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 |
| NVU_EMPTY_200_FASTBREAK | 2 |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 |
| NVU_PEER_FB_SKIP_MODELS | (空) |
| KEY_AUTHFAIL_COOLDOWN_S | 60 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 195 |
| NVU_FORCE_STREAM_UPGRADE | 0 |
| MIN_OUTBOUND_INTERVAL_S | 0 |

### Compose md5
`b367c647a8d42d9d86ed8814234a1d19` (与R1361相同，不变)

### 容器状态
- 重启时间: 2026-07-14T11:29:07Z（约10h前）
- 容器运行正常

## 决策: NOP — 零可修故障

**分析**: 数据与R1361完全一致。8个失败全部是zombie_empty_completion（glm5_2_nv integrate, NVCF content-filter stop → 6-42 chars output, ~188-192K input）。这是代码级zombie检测功能 — 网关正确检测并返回502（5-15s），替代旧版96s的NVStream_TimeoutError。nv_gw日志确认: NV-ZOMBIE-EMPTY + NV-ZOMBIE-ERROR-CHUNK → 已正确发送content_filter SSE chunk触发openclaw fallback。

- 0 ATE, 0 timeout, 0 empty_200, 0 tier_attempts, 0 fallback → 所有参数已处于floor/optimal
- 0 dsv4p_nv traffic → dsv4p_nv budget 94 未触发
- 0 ms_gw traffic → ms_gw参数无优化空间
- Compose md5不变 → HM1未做任何外部修改
- Container已重启10h+（R1361写的是~10h前），无pre-restart污染
- **All params floor/optimal — 无优化空间**

**铁律: 只改HM1不改HM2** — 本轮不改任何参数

## ⏳ 轮到HM1优化HM2
