# HM2 Optimize HM1 — Round R1407

## 触发分析
cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = opc2_uname (HM2), R1406
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch)
- R1406 symlink 已正确指向 `rounds/R1406_hm2_optimize_hm1.md`
- 这是 R1133 链第 566 次 false-trigger 连续派遣

## 数据 (HM1, 6h window, container restarted 2026-07-15T01:42:20Z)

### 请求统计
| 指标 | 值 |
|------|-----|
| 总请求 | 12 |
| 成功 | 10 (83.3% SR) |
| 失败 | 2 |

### 按模型
| 模型 | 请求 | 成功 | 失败 | SR% | avg_ms | p50_ms | p95_ms |
|------|------|------|------|-----|--------|--------|--------|
| dsv4p_nv | 1 | 1 | 0 | 100.0% | 6113 | 6113 | 6113 |
| glm5_2_nv | 11 | 9 | 2 | 81.8% | 9981 | 9067 | 21636 |

### 错误分类
| 错误类型 | 数量 | avg_ms | 分析 |
|----------|------|--------|------|
| zombie_empty_completion | 2 | 7624 | glm5_2_nv, NVCF content-filter stop+12chars, input_chars ~209K. Gateway detection+error-chunk: finish_reason=**timeout** (R1405 fix active, confirmed 10:03 zombie). Not config-fixable. |
| all_tiers_exhausted | 1 | 6113 | dsv4p_nv: k4→504 gateway_timeout, k1→pexec timeout 40296ms, FASTBREAK=1, ATE 106049ms, ms_gw fallback OK (200, 606 bytes). NVCF-side degradation. |

### 关键指标
- tier_attempts: **0**
- fallback_occurred: true=1, false=11
- ms_gw: 4 total, 3 OK
- peer-fb: 0 (no cross-machine fallback)
- Compose md5: **f493494e2b41b17fbf5d9cff9093648e** (unchanged)

## R1405 Fix 验证
- 10:03 zombie: `finish_reason=timeout` (新行为) ✓
- 02:08-03:33 zombies: `finish_reason=content_filter` (旧行为) — 容器重启 01:42 后未立即生效，10:03 已生效
- 验证: `docker logs nv_gw | grep "NV-ZOMBIE-ERROR-CHUNK"` 显示 `finish_reason=timeout` (R1405 fix)

## 决策
**NOP** — 所有参数 floor/optimal:
- FASTBREAK: PEXEC=1, INTEGRATE=1, EMPTY_200=2 (floor)
- COOLDOWN: KEY=25, TIER=15, KEY_AUTHFAIL=60, INTEGRATE_KEY=0 (floor)
- TIMEOUT: UPSTREAM=66, TIER_BUDGET=205, CONNECT=0, MIN_INTERVAL=0 (floor)
- TIER_BUDGET: DSV4P=106, GLM5_2=96, MINIMAX=100 (optimal)
- PEER_FB: enabled, timeout=66, SKIP_MODELS=空 (optimal)
- MS_GW: fallback timeout=195, modelmap 完整 (optimal)
- FORCE_STREAM: 0 (optimal)
- SSLEOF: retry_delay=1.0 (optimal)

zombie_empty_completion: code-level (NVCF content-filter → stop+<50 chars), NV-ZOMBIE-ERROR-CHUNK `finish_reason=timeout` 正确触发 openclaw fallback. R1405 fix 已生效.
ATE: dsv4p_nv 504 gateway_timeout (NVCF-side), ms_gw rescue OK. 0 tier_attempts 确认无 key cycling. FASTBREAK=1 正确.
0 config-fixable. 铁律: 只改HM1不改HM2.
## ⏳ 轮到HM1优化HM2
