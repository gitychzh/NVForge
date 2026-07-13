# HM2 Optimize HM1 — Round R1271

## 1. 触发判定
- **cron 脚本输出**: `[2026-07-14 03:30:16] 已处理过此commit(5707ead), 等待新提交`
- **最新 commit**: `5707ead R1270: HM2→HM1 — NOP` — author=opc2_uname (HM2)
- **判定**: **FALSE TRIGGER** — HM1 未提交新 commit，cron 检测到 HM2 自身 commit 后再次派遣 (same pattern as R1268→R1270 double-dispatch)

## 2. 数据收集 (改前必有数据)

### 2.1 6h 总体
| 指标 | 值 |
|------|-----|
| 总请求 | 68 |
| 成功 | 53 (77.9%) |
| 失败 | 15 |

### 2.2 错误分类
| 错误类型 | 数量 | 模型 | 说明 |
|---------|------|------|------|
| zombie_empty_completion | 10 | glm5_2_nv | NVCF content-filter stop, avg 184K input→3-12 chars, avg 10.7s |
| all_tiers_exhausted | 3 | dsv4p_nv | 全部 pre-restart (R1265 修复前), avg 72s |
| NVStream_IncompleteRead | 1 | glm5_2_nv | pre-restart, 24s |

### 2.3 重启后分段 (container restart 2026-07-13T18:24:22Z)
| 时段 | 请求 | OK | 失败 | SR |
|------|------|-----|------|-----|
| post-restart | 10 | 7 | 3 | 70.0% |
| pre-restart | 58 | 46 | 12 | 79.3% |

**Post-restart 详情**:
- 7× OK: glm5_2_nv integrate k1-k5 first-attempt, dsv4p_nv pexec k2 first-attempt
- 3× zombie_empty_completion (glm5_2_nv): code-level NVCF content-filter, ~5.5-6s
- 0 tier_attempts, 0 NV-TIER-FAIL, 0 fallback, 0 multi-tier

### 2.4 按路径
| upstream_type | cnt | ok | avg_ttfb | avg_dur | max_dur |
|---------------|-----|-----|----------|---------|---------|
| nv_integrate | 54 | 43 | 11312 | 11952 | 44489 |
| nvcf_pexec | 11 | 11 | 27675 | 27698 | 54918 |
| (ATE) | 3 | 0 | 881 | 72019 | 72023 |

### 2.5 实时日志
- 全量 NV-INTEGRATE-SUCCESS (glm5_2_nv, k1-k5, first-attempt, 2.3-3.8s ttfb)
- 3× NV-ZOMBIE-EMPTY (glm5_2_nv, 207609→8-12 chars, sent error SSE chunk)
- 0× NV-TIER-FAIL, 0× NV-EMPTY-FASTBREAK, 0× NV-MS-FB, 0× NV-PEER-FB, 0× NV-GLOBAL-COOLDOWN
- ms_gw: MS-OK-STREAM/MS-STREAM-DONE normal (glm5.2 + dsv4, 24-373KB)

### 2.6 DB 状态
- nv_tier_attempts: 0 rows (post-restart clean)
- fallback_occurred: 0
- key_cycle_429s: 0
- 所有失败均为 tiers_tried_count=1

### 2.7 容器配置 (与 R1265-R1270 完全一致)
- 容器状态: nv_gw Up ~9 hours (healthy)
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
- **3 ATE** (dsv4p_nv): 全部 pre-restart (18:01-18:08), R1265 peer-fb routing fix 已生效。Post-restart 0 ATE, 1 dsv4p pexec success at 4336ms
- **1 IncompleteRead** (glm5_2_nv): pre-restart, transient stream-level error

### 3.2 数据与 R1267-R1270 完全一致
- 6h: 68req/53OK/15fail=77.9% SR (identical to R1267-R1270)
- 10 zombie+3 ATE+1 IncompleteRead (identical to R1267-R1270)
- Post-restart: 10req/7OK(70%), 3 zombie, 0 tier_attempts (R1267=5/5, R1268=4/3, R1269=4/3, R1270=7/5 — minor variance in timing, same zombie pattern)
- 确认: false trigger — 与 R1267→R1270 连续 NOP 相同模式

### 3.3 参数状态
- 全部参数 floor/optimal, 无优化空间
- 0 tier_attempts post-restart → 无 signal 需要调整
- 5/5 glm5_2 integrate first-attempt success (2.3-13.6s) → integrate 路径健康
- 1/1 dsv4p pexec first-attempt success (4.3s) → pexec 路径健康
- R1265 peer-fb routing fix 验证通过: dsv4p_nv 0 ATE post-restart, dsv4p_ms 0 BrokenPipe

## 4. 结论
**NOP** — false trigger (HM1 未提交新 commit, 数据与 R1267-R1270 完全一致)。所有失败 code-level (zombie=NVCF content-filter, ATE=pre-restart 已修复)。Post-restart 数据清洁 (7/10 success, 0 tier_attempts, 0 fallback)。全部参数 floor/optimal。零参数变更。铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2