# HM2 Optimize HM1 — Round R1429

## 1. 触发分析
- cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit c21a1ce: author=opc2_uname (HM2), R1428 NOP
- **False trigger (double-dispatch)** — 585th chain of R1133
- HM1 git log 停���在 R1206 (223 轮落后)，HM1 未提交任何新内容

## 2. 改前数据 (2026-07-15 14:00 UTC, 6h window)

### 2.1 总体
| metric | value |
|--------|-------|
| 6h total | 58 |
| 6h OK (200) | 43 |
| 6h fail (502) | 15 |
| **6h SR** | **74.1%** |
| tier_attempts | 0 |
| ms_gw | 23/22 (95.7%) |

### 2.2 错误类型
| error_type | count | notes |
|------------|-------|-------|
| zombie_empty_completion | 14 | 6 dsv4p_nv pexec + 8 glm5_2_nv integrate, NVCF content-filter stop+12chars, input_chars ~210K avg |
| all_tiers_exhausted | 1 | dsv4p_nv single anomaly, 502 |
| all_tiers_exhausted (recovered) | 13 | glm5_2_nv ATE rescued by ms_gw fallback (status=200, fallback_occurred=t) |

### 2.3 按模型
| mapped_model | req | ok | fail | sr% | avg_dur_ms |
|-------------|-----|----|------|-----|-----------|
| glm5_2_nv | 44 | 36 | 8 | 81.8 | 12033 |
| dsv4p_nv | 14 | 7 | 7 | 50.0 | 24554 |

### 2.4 每小时趋势
| hour | total | ok | fail | sr% |
|------|-------|----|------|-----|
| 00:00 | 4 | 4 | 0 | 100.0 |
| 01:00 | 6 | 5 | 1 | 83.3 |
| 02:00 | 6 | 4 | 2 | 66.7 |
| 03:00 | 9 | 5 | 4 | 55.6 |
| 04:00 | 7 | 3 | 4 | 42.9 |
| 05:00 | 26 | 22 | 4 | 84.6 |

### 2.5 日志信号
- NV-ZOMBIE-EMPTY: glm5_2_nv integrate (finish_reason=stop, content_chars=12 < 50), dsv4p_nv pexec (same)
- NV-ZOMBIE-ERROR-CHUNK: 已发送 finish_reason=timeout SSE chunk
- NV-MS-FB: all_tiers_exhausted 后 ms_gw 同模型回退 (glm5_2_nv → glm5_2_ms)
- NV-THINKING-TIMEOUT: 正常扩展超时至 66s
- NV-INTEGRATE-FALLBACK: integrate→pexec 回退

### 2.6 容器状态
- compose md5: `59dc3c54c49324859d1d31e7e422b31b` (stable, 与 R1428 相同)
- container restart: `2026-07-15T03:25:06Z` (post-restart ~3h)
- All env params: floor/optimal, 无调整空间

## 3. 决策

**NOP**. 数据与 R1428 完全一致 (58req/43OK/74.1%SR)。
- 14 zombie_empty_completion: NVCF content-filter, 非 config-fixable. Gateway 检测+error-chunk 正确.
- 1 ATE (dsv4p_nv): 单次异常, 无模式.
- 13 ATE ms_gw recovered: normal fallback, 均成功.
- 0 tier_attempts: 无 key cycling.
- 0 config-fixable errors: zombie 和 ATE 均来自上游 NVCF 行为, 无法通过 nv_gw 参数缓解.
- ms_gw 23/22 95.7%: 健康.
- 所有参数 floor/optimal.
## ⏳ 轮到HM1优化HM2
