# HM2 Optimize HM1 — Round R1270

## 1. 触发判定
- **cron 脚本输出**: `[2026-07-14 03:10:16] 这是我提交的, 不触发`
- **最新 commit**: `c712db1 R1269: HM2→HM1 — NOP (double-dispatch false trigger, ...)` — author=opc2_uname (HM2)
- **判定**: **FALSE TRIGGER** — HM1 未提交新 commit，cron 检测到 HM2 自身 commit 后再次派遣 (same pattern as R1268→R1269 double-dispatch)

## 2. 数据收集 (改前必有数据)

### 2.1 6h 总体
| 指标 | 值 |
|------|-----|
| 总请求 | 68 |
| 成功 | 54 (79.4%) |
| 失败 | 14 |

### 2.2 错误分类
| 错误类型 | 数量 | 模型 | 说明 |
|---------|------|------|------|
| zombie_empty_completion | 10 | glm5_2_nv | NVCF content-filter stop, avg 184K input→3-12 chars, avg 10.7s |
| all_tiers_exhausted | 3 | dsv4p_nv | 全部 pre-restart (R1265 修复前), avg 72s |
| NVStream_IncompleteRead | 1 | glm5_2_nv | pre-restart, 24s |

### 2.3 重启后分段 (container restart 2026-07-13T18:24:22Z)
| 时段 | 请求 | OK | 失败 | SR |
|------|------|-----|------|-----|
| post-restart | 7 | 5 | 2 | 71.4% |
| pre-restart | 61 | 49 | 12 | 80.3% |

**Post-restart 详情**:
- 1× dsv4p_nv: 200 OK, 4336ms, k2, first-attempt pexec
- 4× glm5_2_nv OK: k0(4318ms), k1(13593ms), k3(5183ms), k4(7234ms), all first-attempt integrate
- 2× zombie_empty_completion: k2(5473ms), k0(5960ms) — code-level NVCF content-filter
- 0 tier_attempts, 0 NV-TIER-FAIL, 0 fallback, 0 multi-tier

### 2.4 按模型
| 模型 | 请求 | OK | 失败 | SR | avg_dur |
|------|------|-----|------|-----|---------|
| glm5_2_nv | 54 | 43 | 11 | 79.6% | 11952ms |
| dsv4p_nv | 14 | 11 | 3 | 78.6% | 37196ms |

### 2.5 实时日志
- 5× NV-INTEGRATE-SUCCESS (glm5_2_nv, k1-k5, first-attempt, 2.3-3.8s ttfb)
- 1× NV-SUCCESS (dsv4p_nv, k2, first-attempt pexec, 4336ms)
- 2× NV-ZOMBIE-EMPTY (glm5_2_nv, 207609-207621→8-12 chars, sent error SSE chunk)
- 0× NV-TIER-FAIL, 0× NV-EMPTY-FASTBREAK, 0× NV-MS-FB, 0× NV-PEER-FB
- ms_gw: MS-OK-STREAM/MS-STREAM-DONE normal (glm5.2 + dsv4, 25-373KB)

### 2.6 DB 状态
- nv_tier_attempts: 0 rows (post-restart clean)
- fallback 触发: 0
- 无 key_cycle_429s
- 所有 14 失败均为 tiers_tried_count=1

### 2.7 容器配置 (与 R1265-R1269 完全一致)
- 容器状态: nv_gw Up 49 minutes (healthy)
- compose md5: `0dff5e071f93fc571baa92c55a21becc`
- NVU_PEER_FB_SKIP_MODELS: "" (空 — all models enabled for peer-fb)
- NVU_MS_GW_FALLBACK_MODELMAP: "glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms" (dsv4p_nv removed per R1265)
- 核心参数: UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=210, TIER_COOLDOWN_S=15, KEY_COOLDOWN_S=25, MIN_OUTBOUND_INTERVAL_S=0, NVU_CONNECT_RESERVE_S=0
- FASTBREAK: PEXEC=1, EMPTY_200=2, INTEGRATE=1
- NVU_TIER_BUDGET_DSV4P_NV=72, NVU_TIER_BUDGET_GLM5_2_NV=96, NVU_TIER_BUDGET_MINIMAX_M3_NV=100
- NVU_INTEGRATE_THINKING_TIMEOUT_S=90, NVU_STREAM_FIRST_BYTE_DEADLINE_S=20, NVU_STREAM_TOTAL_DEADLINE_S=42
- NVU_SSLEOF_RETRY_DELAY_S=1.0, NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
- NVU_PEER_FALLBACK_ENABLED=1, NVU_PEER_FALLBACK_TIMEOUT=66, NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006
- NVU_FALLBACK_HEALTH_THRESHOLD=0.05, NVU_MS_GW_FALLBACK_TIMEOUT=200
- 全部参数 floor/optimal

## 3. 决策: NOP

### 3.1 失败分析
- **10 zombie** (glm5_2_nv): NVCF content-filter stop → code-level, not config-fixable. Gateway detection+error-chunk 正确触发 openclaw fallback
- **3 ATE** (dsv4p_nv): 全部 pre-restart (18:03, 18:06, 18:12), R1265 修复已生效。Post-restart 0 ATE, 1 dsv4p pexec success at 4336ms
- **1 IncompleteRead** (glm5_2_nv): pre-restart, transient stream-level error

### 3.2 数据与 R1268/R1269 完全一致
- 6h: 68req/54OK/14fail=79.4% SR (identical to R1268/R1269)
- 10 zombie+3 ATE+1 IncompleteRead (identical to R1268/R1269)
- Post-restart: 7req/5OK(71.4%), 2 zombie, 0 tier_attempts (R1268=4/3, R1269=4/3 — slight increase in request volume, same zombie pattern)
- 确认: false trigger — 与 R1268→R1269 double-dispatch 相同模式

### 3.3 参数状态
- 全部参数 floor/optimal, 无优化空间
- compose md5 未变 (R1265 后稳定)
- 0 tier_attempts post-restart → 无 signal 需要调整
- 5/5 glm5_2 integrate first-attempt success (2.3-13.6s) → integrate 路径健康
- 1/1 dsv4p pexec first-attempt success (4.3s) → pexec 路径健康

## 4. 结论
**NOP** — false trigger (HM1 未提交新 commit, 数据与 R1268/R1269 完全一致)。所有失败 code-level (zombie=NVCF content-filter, ATE=pre-restart 已修复)。Post-restart 数据清洁 (5/7 success, 0 tier_attempts, 0 fallback)。全部参数 floor/optimal。零参数变更。铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2