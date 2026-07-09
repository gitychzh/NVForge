# HM2 Optimize HM1 — Round R962

## 触发类型: FALSE TRIGGER (自提交误触发)

- cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit: `a797b25 R961: HM2→HM1 — NVU_PEXEC_TIMEOUT_FASTBREAK 2→1`
- Author: opc2_uname (HM2) → 脚本正确检测到自提交
- 但 cron 仍被派遣 → 误触发
- Symlink: 之前指向 R959 (stale), 本轮修复 → R961

## 1. 改前数据 (2026-07-09 12:25 UTC)

### 容器状态
- 容器: `nv_gw` (Up 6 minutes, healthy)
- R961 部署后, 新 regime 运行 ~6min
- 容器健康: healthy ✓

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
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv,dsv4p_nv | |
| NVU_FORCE_STREAM_UPGRADE | 0 | 禁用 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 | 对齐 UPSTREAM |
| NVU_EMPTY_200_FASTBREAK | 3 | |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | |

### 6h Regime (容器重启后 ~6min, 实际包含旧 regime 数据)
| 指标 | 值 |
|------|-----|
| 6h 总请求 | 29 |
| 6h 成功 | 29 (100.0% SR) |
| 6h 失败 | 0 |
| 6h ATE | 0 |
| avg_ok_ms | 39,236ms |
| max_ok_ms | 173,278ms |
| pexec_cnt | 29 (全部 pexec) |
| integrate_cnt | 0 (INTEGRATE_MODELS="") |
| key_cycle_429s | 11 total (6 req with 429) |
| 零错误: ERROR/WARN/exception | 0 |

### Per-Model 6h
| Model | Total | OK | Fail | avg_ok_ms | max_ok_ms |
|-------|-------|-----|------|-----------|-----------|
| glm5_2_nv | 29 | 29 | 0 | 39,236 | 173,278 |

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

### 小时级趋势 (6h)
| Hour (UTC) | Total | OK | Fail | avg_ok_ms |
|-----------|-------|-----|------|-----------|
| 22:00 (Jul 8) | 3 | 3 | 0 | 4,735 |
| 23:00 | 6 | 6 | 0 | 14,431 |
| 00:00 | 6 | 6 | 0 | 6,041 |
| 01:00 | 7 | 7 | 0 | 39,701 |
| 02:00 | 3 | 3 | 0 | 93,384 |
| 03:00 | 3 | 3 | 0 | 105,403 |
| 04:00 | 1 | 1 | 0 | 126,524 |

全小时 100% SR, 零错误。延迟从 4.7s 到 126.5s, 正常 thinking 请求波动。

## 2. 候选评估

| 参数 | 当前值 | 候选 | 评估 | 决策 |
|------|--------|------|------|------|
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor | 绝对 floor, 29/29 100% SR 验证正确 | ❌ |
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

- 29/29 100% SR (6h), 零 ATE, 零错误
- FASTBREAK=1 正确: NVCFPexecTimeout 函数级 ~52s << UPSTREAM=64, 2nd key 无益
- Fallback dsv4p_nv 5/5 100% SR, 可靠救援路径
- 所有非 floor 参数无数据支撑调整
- 等待信号: NVCF function 健康度变化 or 新模型到达

## 4. 评判

- 更少报错: 6h 0 错误, 0 ATE ✓
- 更快请求: 失败路径省 ~52s (FASTBREAK=1 vs 2) ✓
- 超低延迟: 直接成功 avg 4.7-39.7s (小时级), 无变化 ✓
- 稳定优先: 100% SR, 零变更, 等待信号 ✓

## 5. 触发分析

- cron 脚本输出: `"这是我提交的, 不触发"` + `"已处理过此commit(a797b25...), 等待新提交"`
- 最新 commit: `a797b25 R961` (author=opc2_uname, HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 → 误触发 (false trigger)
- Symlink 修复: `RN_hm2_optimize_hm1.md` → `rounds/R961_hm2_optimize_hm1.md` (之前 stale → R959)

## ⏳ 轮到HM1优化HM2
