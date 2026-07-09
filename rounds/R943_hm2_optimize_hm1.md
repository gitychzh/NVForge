# HM2 → HM1 优化回合 R943

**Timestamp**: 2026-07-09 08:20 UTC  
**Trigger**: 误触发 (false trigger, 60th consecutive)  
**Commit**: e976231 (R942: HM2→HM1 — NOP, 59th consecutive)  
**Author of triggering commit**: opc2_uname (HM2) — script output: `"这是我提交的, 不触发"`

## 1. 触发分析

- cron 脚本输出: `"这是我提交的, 不触发"` — HM2自提交，不应触发
- 最新commit author = `opc2_uname` (HM2)，不是 `opc_uname` (HM1)
- R942 已由 pre-run script 提交为 NOP
- 本次为双派遣 (double-dispatch) — cron 在 pre-run script 已处理完毕后再次派遣 agent
- HM1 本地 git log 仍停留在 R821 (122 轮落后) — 无新提交

## 2. 改前数据 — nv_gw (端口 40006)

### 6h 总体统计
| 指标 | 值 |
|------|-----|
| 总请求 | 39 |
| 成功 (200) | 39 |
| 失败 | 0 |
| 成功率 | **100%** |
| avg_ttfb | 7401 ms |
| avg_duration | 7402 ms |
| p50_ttfb | 4850 ms |
| p99_ttfb | 47862 ms |
| max_duration | 67241 ms |
| min_ttfb | 1916 ms |

### 错误分布 (6h)
零错误 — `error_type` 全部为空。

### 上游路径 (6h)
| upstream_type | cnt | ok | avg_ttfb | avg_dur |
|---|---|---|---|---|
| nvcf_pexec | 39 | 39 | 7401 | 7402 |

全部请求走 nvcf_pexec，无 integrate。

### 模型分布 (6h)
| request_model | cnt | avg_ttfb | avg_dur | 成功率 |
|---|---|---|---|---|
| glm5_2_nv | 39 | 7401 | 7402 | 100% |

全部为 openclaw 的 glm5_2_nv 请求。

### Key 分布 (6h)
| nv_key_idx | cnt | avg_ttfb | fails |
|---|---|---|---|
| 0 (K1) | 8 | 5235 | 0 |
| 1 (K2) | 8 | 6279 | 0 |
| 2 (K3) | 8 | 13526 | 0 |
| 3 (K4) | 7 | 4217 | 0 |
| 4 (K5) | 8 | 7350 | 0 |

5 个 key 全部健康，分布均匀 (7-8 req each)，K3 延迟略高但无错误。

### Fallback (6h)
零 fallback — 全部请求首 tier 首 key 直接成功。

### 24h ATE 全景
| error_type | cnt | first_seen | last_seen |
|---|---|---|---|
| all_tiers_exhausted | 1 | 2026-07-08 13:21 UTC | 2026-07-08 13:21 UTC |

**单次 ATE 详情**:
- ts: 2026-07-08 13:21:01 UTC
- request_model: glm5_2_nv
- mapped_model: glm5_2_nv (fallback 链未生效)
- start_tier_idx: 2 (glm5_2_nv)
- tiers_tried: 2 ({glm5_2_nv, dsv4p_nv})
- fallback_occurred: false (⚠️ 两个 tier 都试了但 fallback_occurred=false — FALLBACK_GRAPH 瞬时消失)
- duration: 121075 ms (~2 min)
- key_cycle_429s: 0

与 R906–R942 模式一致：24h 内恰好 1 次 identical ATE (同时间窗，NVCF 上游瞬时事件，FALLBACK_GRAPH 消失)。

### nv_tier_attempts (24h, 仅失败尝试)
| tier | error_type | cnt | avg_ms | max_ms |
|---|---|---|---|---|
| dsv4p_nv | NVCFPexecTimeout | 1 | 52849 | 52849 |
| dsv4p_nv | empty_200 | 1 | — | — |
| glm5_2_nv | 504_nv_gateway_timeout | 8 | — | — |
| glm5_2_nv | empty_200 | 6 | — | — |
| glm5_2_nv | NVCFPexecTimeout | 1 | 51475 | 51475 |

Tier attempts 总失败数 (17) 远超实际 ATE 数 (1)。原因：tier_attempts 记录的是尝试级别失败（含 empty_200 fastbreak、504 gateway timeout 等），但成功 fallback 到另一 tier 后最终请求仍返回 200，不进入 ATE 计数。

### 容器日志 (最近 100 行)
全部为 `[NV-SUCCESS] tier=glm5_2_nv kX succeeded on first attempt`，零 error/warn/traceback。tier_chain 双向健康: `['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={...})`。运行干净。

## 3. 改前数据 — ms_gw (端口 40007)

### 6h 统计
| total | ok | fail |
|---|---|---|
| 0 | 0 | 0 |

ms_gw 完全空闲，无请求。

### ms_gw 容器 env (关键参数)
- EMPTY_200_FASTBREAK_THRESHOLD=3 (已调优至最低)
- KEY_COOLDOWN_S=60 (HM1 在 ms_gw 用 60s，比 HM2 更保守)
- MIN_OUTBOUND_INTERVAL_S=1.0
- UPSTREAM_TIMEOUT=300

ms_gw 处于健康空闲状态，无优化空间。

## 4. nv_gw 容器环境 (HM1 当前参数)

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 64 | ⚠️ floor |
| TIER_TIMEOUT_BUDGET_S | 114 | ✅ |
| MIN_OUTBOUND_INTERVAL_S | 0 | ✅ floor |
| KEY_COOLDOWN_S | 25 | ✅ floor |
| TIER_COOLDOWN_S | 25 | ✅ floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | ✅ floor |
| NVU_CONNECT_RESERVE_S | 0 | ✅ floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | ✅ floor |
| NVU_EMPTY_200_FASTBREAK | 3 | ✅ floor |
| NVU_FORCE_STREAM_UPGRADE | 0 | ✅ disabled |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 | ✅ (同步 UPSTREAM_TIMEOUT) |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | ✅ (R922 added) |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv,dsv4p_nv | ✅ (R923 added) |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | ✅ |
| NVU_PEER_FALLBACK_ENABLED | 1 | ✅ |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | ✅ |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | ✅ |

**所有参数已在地板值**，无可进一步降低的空间 (MIN_OUTBOUND_S=0, KEY_COOLDOWN_S=25, FASTBREAK=3, PEXEC_TIMEOUT_FASTBREAK=1)。

## 5. 优化决策

**NOP** — 无优化空间，理由：
1. ✅ 6h 100% SR, 零错误, 零 ATE — 已完美运行
2. ✅ 所有 nv_gw 参数在地板值 — 无法进一步降低 (已是 0/25/1/3)
3. ✅ ms_gw 空闲 (0 请求) — 无优化需求，已在地板 (FASTBREAK=3)
4. ✅ 24h 仅 1 次 ATE (NVCF 上游瞬时事件，FALLBACK_GRAPH 消失模式) — 不可修复 (上游问题)
5. ✅ 容器日志干净，所有请求首 key 成功
6. ✅ 5 个 key 全部健康，均匀分布
7. ✅ tier_chain 双向健康 — `['glm5_2_nv', 'dsv4p_nv']` 双 fallback 完整
8. ✅ 无新请求模型或上游路径变化

**对比 R942**: 数据完全一致 (39/39 100% SR, identical ATE pattern, all params at floor)。无退化，无优化机会。

## 6. 铁律检查

- ✅ 改前必有数据 — SSH + DB 查询完整收集 (6h SR, 24h ATE, tier attempts, key dist, container env, logs)
- ✅ 只改 HM1 不改 HM2 — 本次无修改
- ✅ 回合文件写入仓库

## ⏳ 轮到HM1优化HM2