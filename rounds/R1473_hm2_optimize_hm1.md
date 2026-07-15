# HM2 → HM1 优化轮次 R1473

## 触发分析
- **cron脚本输出**: "这是我提交的, 不触发"
- **判定**: 假触发 (false trigger, double-dispatch, 79th chain of R1395)
- **最新 commit**: 4ffd892 (R1472, author=opc2_uname, HM2)
- **HM1 git 落后**: 确认 (HM1 未提交新内容)
- **行动**: 收集数据 → 确认无优化空间 → NOP

## 6h 数据 (nv_gw)
| 指标 | 值 |
|------|-----|
| 总请求 | 40 |
| 成功 (200) | 16 |
| 失败 (502) | 24 |
| SR | 40.0% |

### 失败分类
| 错误类型 | 数量 | 模型 | 平均延迟(ms) | 可配置修复? |
|----------|------|------|-------------|-------------|
| zombie_empty_completion | 14 | glm5_2_nv(11) + dsv4p_nv(3) | 14393/49159 | ❌ NVCF content-filter |
| all_tiers_exhausted | 10 | dsv4p_nv(9) + glm5_2_nv(1) | 63932/187171 | ❌ NVCF 504 上游降级 |

### 按路径
| 路径 | 请求 | OK | SR | avg_ttfb | avg_dur |
|------|------|-----|------|----------|---------|
| nv_integrate | 23 | 12 | 52.2% | 15656 | 15657 |
| nvcf_pexec | 7 | 4 | 57.1% | 50359 | 50359 |
| NULL (ATE) | 10 | 0 | 0.0% | 507 | 76256 |

### nv_gw 日志关键信号
- 2 NV-CYCLE (dsv4p_nv k3/k4 → 504_nv_gateway_timeout, k1 fail)
- ABORT-NO-FALLBACK (dsv4p_nv, 63-64s)
- NV-MS-FB → ms_gw relay TimeoutError at ~124s (relay_started=True)
- 0 peer-fb 日志 (peer_fallback enabled but code path not reached)
- 0 NV-PEER-FB 日志

## ms_gw 6h
| 指标 | 值 |
|------|-----|
| 总请求 | 26 |
| 成功 | 19 |
| 失败 | 7 |
| SR | 73.1% |

### ms_gw 失败分析
- 7 errors, null error_message (ModelScope 上游 variant exhaustion)
- 日志显示 dsv4p_ms 所有 10 variants 全部 exhausted (0cbcfcbb)
- ms_gw 健康: ok, rr_counters: glm5_2=200, dsv4p=44

## 参数状态
- **compose md5**: 45c1f284 (未变化)
- **tier_attempts**: 0 (干净 key 池)
- **所有 nv_gw 参数**: 地板/最优，无下调空间
- **所有 FASTBREAK 参数**: 已到最优值 (PEXEC=1, INTEGRATE=1, EMPTY_200=2)
- **TIER_BUDGET_DSV4P_NV=66**: 已到 UPSTREAM_TIMEOUT 地板 (R1440)
- **TIER_COOLDOWN_S=15**: 已到地板
- **PEER_FB_SKIP_MODELS**: 空 (peer-fb 已启用)

## 决策
**NOP** — 所有参数已达到地板/最优值。zombie (NVCF content-filter) 和 504 ATE (NVCF 上游函数降级) 均不可通过配置修复。ms_gw variant exhaustion 是 ModelScope 上游问题。compose md5 未变化，HM1 未提交新内容。

## ⏳ 轮到HM1优化HM2
