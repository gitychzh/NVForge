# HM2 Optimize HM1 — Round R963

## 触发类型: DOUBLE-DISPATCH (自提交误触发, 第二次派遣)

- cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit: `e13c903 R962: HM2→HM1 — NOP (false trigger, 29/29 100% 6h SR, ...)`
- Author: opc2_uname (HM2) → 脚本正确检测到自提交
- R962 已由 pre-run script 在 12:35 UTC 提交并推送
- Symlink 已指向 R962 (正确) → 本次是同一触发器的第二次派遣 (double-dispatch)
- 创建 R963 作为新 NOP 轮次

## 1. 改前数据 (2026-07-09 12:35 UTC)

### 容器状态
- 容器: `nv_gw` (Up 17 minutes, healthy)
- R961 部署后运行 17min, 健康: healthy ✓
- 零 ERROR/WARN/exception

### 当前配置 (从容器 env)
| 参数 | 值 | 状态 |
|------|-----|------|
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor (R961) |
| UPSTREAM_TIMEOUT | 64 | |
| TIER_TIMEOUT_BUDGET_S | 114 | |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NV_INTEGRATE_MODELS | "" | 空 |
| TIER_COOLDOWN_S | 25 | |
| KEY_COOLDOWN_S | 25 | |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | |
| NVU_PEER_FALLBACK_ENABLED | 1 | |
| NVU_FORCE_STREAM_UPGRADE | 0 | 禁用 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 | 对齐 UPSTREAM |
| NVU_EMPTY_200_FASTBREAK | 3 | |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | |

### 6h Regime
| 指标 | 值 |
|------|-----|
| 6h 总请求 | 27 |
| 6h 成功 | 27 (100.0% SR) |
| 6h 失败 | 0 |
| 6h ATE | 0 |
| avg_ok_ms | 43,812ms |
| max_ok_ms | 173,278ms |
| pexec_cnt | 27 (全部 pexec) |
| integrate_cnt | 0 (INTEGRATE_MODELS="") |
| key_cycle_429s | 11 total |
| 零错误: ERROR/WARN/exception | 0 |

### Per-Model 6h
| Model | Total | OK | Fail | avg_ok_ms | max_ok_ms |
|-------|-------|-----|------|-----------|-----------|
| glm5_2_nv | 27 | 27 | 0 | 43,812 | 173,278 |

### Fallback 统计 (6h)
| 指标 | 值 |
|------|-----|
| Fallback 发生 | 5 |
| Fallback 成功 | 5 (100%) |
| Fallback 失败 | 0 |
| fb_avg_ms | 140,746ms |

全部为 tier 链 fallback: `glm5_2_nv → dsv4p_nv` (peer_fb_skip 包含两模型, peer fallback 未被触发)

### Tier Attempts 6h (失败尝试, 非最终结果)
| Tier | Error Type | Count | avg_elapsed_ms | max_elapsed_ms |
|------|-----------|-------|----------------|----------------|
| glm5_2_nv | 504_nv_gateway_timeout | 4 | - | - |
| glm5_2_nv | NVCFPexecTimeout | 4 | 51,538 | 51,796 |
| glm5_2_nv | empty_200 | 2 | - | - |
| glm5_2_nv | budget_exhausted_after_connect | 1 | 51,838 | 51,838 |

**关键**: 所有 tier attempts 是 per-attempt 失败, 但最终请求全部成功 (fallback 到 dsv4p_nv)。
NVCFPexecTimeout max=51,796ms << UPSTREAM=64s (gap=12.2s, 远 >3s) → 非绑定, FASTBREAK=1 正确。

### 最近 10 条请求 (3h)
| Time (UTC) | Model | Status | Duration | Key Cycles |
|------------|-------|--------|----------|------------|
| 04:33 | glm5_2_nv | 200 | 59,288ms | 0 |
| 04:03 | glm5_2_nv | 200 | 126,524ms | 2 |
| 03:33 | glm5_2_nv | 200 | 173,278ms | 2 |
| 03:33 | glm5_2_nv | 200 | 10,352ms | 0 |
| 03:03 | glm5_2_nv | 200 | 132,580ms | 2 |
| 02:33 | glm5_2_nv | 200 | 127,397ms | 2 |
| 02:33 | glm5_2_nv | 200 | 8,805ms | 0 |
| 02:03 | glm5_2_nv | 200 | 143,949ms | 2 |

全 OK, 零错误。延迟从 8.8s 到 173.3s, 正常 thinking 请求波动。

### ms_gw 6h (二次优化机会检查)
| 指标 | 值 |
|------|-----|
| 6h 总请求 | 5 |
| 6h 成功 | 5 (100.0%) |
| 6h 失败 | 0 |
| avg_ok_ms | 9,889ms |

ms_gw 同样 100% SR, 无优化空间。

## 2. 候选评估

| 参数 | 当前值 | 候选 | 评估 | 决策 |
|------|--------|------|------|------|
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor | 绝对 floor, 27/27 100% SR 验证正确 | ❌ |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor | 绝对 floor | ❌ |
| NVU_CONNECT_RESERVE_S | 0 | floor | 绝对 floor | ❌ |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor, INTEGRATE_MODELS="" | 无效参数 | ❌ |
| UPSTREAM_TIMEOUT | 64 | 62(-2s) | NVCFPexecTimeout max=51.8s, gap=12.2s; 但 100% SR 无证据回调 | ❌ |
| TIER_TIMEOUT_BUDGET_S | 114 | 110(-4s) | FASTBREAK=1, 1×64=64<<110; 但 100% SR 无证据, 且 max_ok=173s>114(已fallback) | ❌ |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | 40(-5s) | peer_fb_skip 包含两模型, peer fb 未触发; 无数据支撑 | ❌ |
| NVU_EMPTY_200_FASTBREAK | 3 | 2(-1) | 仅 2 empty_200 tier attempts (6h), 无数据支撑 | ❌ |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | 0.03(-0.02) | 0.05 已与 ms_gw 对齐, 无证据调整 | ❌ |

**结论**: 所有参数达到最优或 floor, 六小时 100% SR, 零错误, 零 ATE。NOP。

## 3. 决策: NOP

- 27/27 100% SR (6h), 零 ATE, 零错误
- FASTBREAK=1 正确: NVCFPexecTimeout 函数级 ~52s << UPSTREAM=64, 2nd key 无益
- Fallback dsv4p_nv 5/5 100% SR, 可靠救援路径
- 所有非 floor 参数无数据支撑调整
- ms_gw 同样 100% SR, 无二次优化机会
- 等待信号: NVCF function 健康度变化 or 新模型到达

## 4. 评判

- 更少报错: 6h 0 错误, 0 ATE ✓
- 更快请求: 失败路径省 ~52s (FASTBREAK=1 vs 2) ✓
- 超低延迟: 直接成功 avg 8.8-59.3s, 无变化 ✓
- 稳定优先: 100% SR, 零变更, 等待信号 ✓

## 5. 触发分析

- cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit: `e13c903 R962: HM2→HM1 — NOP (false trigger, ...)` (author=opc2_uname, HM2)
- R962 已于 12:35 UTC 由 pre-run script 提交并推送
- Symlink 已正确指向 `rounds/R962_hm2_optimize_hm1.md`
- 本次为同一触发器的第二次派遣 (double-dispatch)
- 创建 R963 保持轮次连续性

## ⏳ 轮到HM1优化HM2