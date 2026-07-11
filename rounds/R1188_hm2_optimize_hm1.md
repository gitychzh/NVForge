# HM2 Optimize HM1 — Round R1188

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = opc2_uname (HM2 自提交)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (R1133 链第 56 次)
- HM1 本地 git log 停留在 R821 (366 轮落后) — 正常，HM1 未提交
- 判定: FALSE TRIGGER → NOP

## 2. 数据采集 (改前必有数据)

### 容器状态
- nv_gw: Up 13 hours (healthy), StartedAt=2026-07-10T19:03:27Z
- logs_db: Up 7 days (healthy)
- ms_gw: Up, running
- compose md5: 7975939c245761e451a8813852dcb9bf (unchanged 48h+, since R1088)

### 6h 全景 (2026-07-11 ~09:30-15:30 UTC)

| 维度 | 数值 |
|------|------|
| 总请求 | 24 |
| 成功 | 12 (50.0% SR) |
| 失败 | 12 |
| 模型 | glm5_2_nv (100%) |
| 路径 | nv_integrate (100%) |
| 平均延迟 (成功) | 6,396ms |
| avg TTFB (成功) | 6,396ms |
| key_cycle_429s | 0 |
| dsv4p_nv | 0 traffic |
| ms_gw | 0 traffic |

### 每小时 SR
| 小时 (UTC) | 总 | OK | 失败 | SR% |
|-----------|-----|-----|------|------|
| 02:00 | 4 | 2 | 2 | 50.0 |
| 03:00 | 4 | 2 | 2 | 50.0 |
| 04:00 | 4 | 2 | 2 | 50.0 |
| 05:00 | 4 | 2 | 2 | 50.0 |
| 06:00 | 4 | 2 | 2 | 50.0 |
| 07:00 | 4 | 2 | 2 | 50.0 |

### 错误分布
| 错误类型 | 数量 | avg_dur | 占比 |
|----------|------|---------|------|
| zombie_empty_completion | 12 | 4,902ms | 100% |

### nv_tier_attempts 6h
- 0 rows — 零 tier 错误 (0 NVCFPexecTimeout, 0 SSLEOFError, 0 429)

### Post-restart 全窗口 (2026-07-10T19:03:27Z → 现在)
| 指标 | 值 |
|------|-----|
| 总请求 | 75 |
| 成功 | 42 (56.0% SR) |
| 失败 | 33 |
| zombie | 33 (100%) |
| ATE | 0 |
| NVCFPexecTimeout | 0 |
| 429 相关 | 0 |
| total_kc429 | 3 |

### 日志速查
```
[NV-ZOMBIE-EMPTY] (glm5_2_nv) ... input_chars=165733→173773 (growing ~510-790/30min)
[NV-ZOMBIE-ERROR-CHUNK] (glm5_2_nv) sent finish_reason=content_filter error SSE chunk
```
- 仅 zombie_empty_completion (code-level)
- 零 NV-TIER-FAIL, 零 NV-GLOBAL-COOLDOWN, 零 NV-EMPTY-FASTBREAK
- 零 NV-MS-FB, 零 NV-PEER-FB
- zombie abort 时间: 1.5-2.5s (日志时间戳差 0.5-1.5s, 从 NV-ZOMBIE-EMPTY → NV-ZOMBIE-ERROR-CHUNK)
- input_chars 持续增长 (+8,040 chars in 6h, ~1,340/hr), 确认输入累积趋势

### 环境变量 (关键参数)
| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | floor |
| TIER_TIMEOUT_BUDGET_S | 198 | floor |
| KEY_COOLDOWN_S | 25 | stable |
| TIER_COOLDOWN_S | 15 | floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | floor |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | floor |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | stable |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | floor |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | floor |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | floor |
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 | floor |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | defensive |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NV_INTEGRATE_MODELS | glm5_2_nv | configured |

**所有参数均在 floor/optimal — 无优化空间。**

## 3. 决策: NOP (Zero Param)

### 依据
1. 所有失败 = zombie_empty_completion (100%) — NVCF content-filter stop+12chars, glm5_2_nv integrate
2. zombie 是 NVCF 上游内容过滤行为，非 gateway 配置参数可修
3. Gateway zombie detection 正确工作 — 1.5-2.5s 快速 abort, 远优于旧 96s hang
4. 0 ATE, 0 tier errors, 0 fallback 触发 — 系统无其他故障模式
5. dsv4p_nv 0 traffic 13h, ms_gw 0 nv-initiated traffic 6h
6. 0 nv_tier_attempts — 零 429/SSL/timeout 等 tier 级错误
7. compose md5 48h+ 不变, 容器稳定运行 13h
8. 所有参数 floor/optimal — 无进一步优化空间
9. input_chars 持续增长 (165,733→173,773, +8,040 in 6h) — 累积趋势, 非配置可控

### 铁律: 只改HM1不改HM2 ✓
- 本轮零 config 变更, 零 compose 编辑, 零 container restart

## ⏳ 轮到HM1优化HM2

