# HM2 Optimize HM1 — Round R1408

## 触发分析
cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = opc2_uname (HM2), R1407
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch, 567th chain of R1133)
- R1407 symlink 已正确指向 `rounds/R1407_hm2_optimize_hm1.md`

## 数据 (HM1, 6h window, container restarted 2026-07-15T01:42:20Z)

### 请求统计
| 指标 | 值 |
|------|-----|
| 总请求 | 13 |
| 成功 | 10 (76.9% SR) |
| 失败 | 3 |

### 按模型
| 模型 | 请求 | 成功 | 失败 | SR% | avg_ms |
|------|------|------|------|-----|--------|
| glm5_2_nv | 11 | 9 | 2 | 81.8% | 9981 |
| dsv4p_nv | 2 | 1 | 1 | 50.0% | 56083 |

### 错误分类
| 错误类型 | 数量 | avg_ms | 模型 | 分析 |
|----------|------|--------|------|------|
| zombie_empty_completion | 2 | 7624 | glm5_2_nv | NVCF content-filter stop+<50chars, input_chars ~208K. Gateway detection+error-chunk. finish_reason=timeout (R1405 fix active at 10:03 JST). Not config-fixable. |
| all_tiers_exhausted | 1 | 106052 | dsv4p_nv | k4→504 gateway_timeout, k5→pexec timeout 40296ms, FASTBREAK=1, ms_gw relay failed after 198814ms TimeoutError (relay_started=True). R1103 BUDGET enforcement gap — relay exceeds NVU_MS_GW_FALLBACK_TIMEOUT=195. Second dsv4p_nv ATE (01:44 UTC) rescued by ms_gw (status=200, 6113ms). |

### 每小时 SR
| 小时 (UTC) | 请求 | OK | Fail | SR% |
|-----------|------|-----|------|-----|
| 00:00 | 4 | 4 | 0 | 100.0% |
| 01:00 | 6 | 5 | 1 | 83.3% |
| 02:00 | 3 | 1 | 2 | 33.3% |

### 关键指标
- tier_attempts: **0** (no key cycling)
- fallback_occurred: true=1, false=12
- ms_gw: 5req/4OK (1 fail — dsv4p_ms relay timeout 198814ms)
- peer-fb: 0
- Compose md5: **f493494e2b41b17fbf5d9cff9093648e** (unchanged)
- nv_gw log zombie events (last 200 lines): 18
- NV-ZOMBIE-ERROR-CHUNK: 5 events (latest: finish_reason=timeout at 10:03 JST ✓)

## R1405 Fix 验证
- 10:03 JST zombie: `finish_reason=timeout` (新行为) ✓
- 02:49, 03:33, 09:03 zombies: `finish_reason=content_filter` (旧行为, 容器重启 01:42 后未立即生效)
- 验证: `docker logs nv_gw | grep "NV-ZOMBIE-ERROR-CHUNK"` 显示 `finish_reason=timeout` 在 10:03 已出现

## 配置状态
所有参数 floor/optimal:
- FASTBREAK: PEXEC=1, INTEGRATE=1, EMPTY_200=2 (floor)
- COOLDOWN: KEY=25, TIER=15, KEY_AUTHFAIL=60, INTEGRATE_KEY=0 (floor)
- TIMEOUT: UPSTREAM=66, TIER_BUDGET=205, CONNECT=0, MIN_INTERVAL=0 (floor)
- TIER_BUDGET: DSV4P=106, GLM5_2=96, MINIMAX=100 (optimal)
- PEER_FB: enabled, timeout=66, SKIP_MODELS=空 (optimal)
- MS_GW: fallback timeout=195, modelmap 完整 (optimal)
- FORCE_STREAM: 0 (optimal)
- SSLEOF: retry_delay=1.0 (optimal)

## 决策
**NOP** — zero parameter change, zero compose change, zero container restart.

zombie_empty_completion: code-level (NVCF content-filter → stop+<50 chars), R1405 fix active (finish_reason=timeout triggers openclaw fallback). Not config-fixable.

dsv4p_nv ATE: NVCF-side 504 gateway_timeout + pexec timeout. FASTBREAK=1 correct. ms_gw rescue works for one ATE (01:44 UTC), relay timeout for another (R1103 BUDGET enforcement gap — 198814ms > MS_GW_FALLBACK_TIMEOUT=195, relay_started=True, streaming sync defect). Not config-fixable — BUDGET=205 already covers the timeout window.

0 tier_attempts 确认无 key cycling. 0 config-fixable. 铁律: 只改HM1不改HM2.
## ⏳ 轮到HM1优化HM2
