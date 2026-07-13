# HM2 Optimize HM1 — Round R1268

## 1. 触发判定
- **cron 脚本输出**: `[2026-07-14 02:55:15] 这是我提交的, 不触发`
- **最新 commit**: `d510200 R1267: HM2→HM1 — NOP (false trigger, ...)` — author=opc2_uname (HM2)
- **HM1 本地 git log**: R1206 (61 轮落后 HM2 R1267)
- **判定**: **FALSE TRIGGER** — HM1 未提交新 commit，cron 脚本正确检测到自提交并标记 "不触发"

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
| zombie_empty_completion | 10 | glm5_2_nv | NVCF content-filter stop, avg 179K input→6-12 chars, avg 10.9s |
| all_tiers_exhausted | 3 | dsv4p_nv | 全部 pre-restart (R1265 修复前), avg 72s |
| NVStream_IncompleteRead | 1 | glm5_2_nv | pre-restart, 24s |

### 2.3 重启后分段 (container restart 2026-07-13T18:24:22Z)
| 时段 | 请求 | OK | 失败 | SR |
|------|------|-----|------|-----|
| post-restart | 4 | 3 | 1 | 75.0% |
| pre-restart | 64 | 51 | 13 | 79.7% |

**Post-restart 详情**: 1 zombie (glm5_2_nv, code-level), 2 glm5_2 OK (4318ms, 13593ms), 1 dsv4p_nv OK (4336ms, first-attempt pexec). 0 tier_attempts. 0 NV-TIER-FAIL.

### 2.4 按模型
| 模型 | 请求 | OK | 失败 | SR | avg_dur |
|------|------|-----|------|-----|---------|
| glm5_2_nv | 54 | 43 | 11 | 79.6% | 12193ms |
| dsv4p_nv | 14 | 11 | 3 | 78.6% | 37196ms |

### 2.5 实时日志
- 4× NV-INTEGRATE-SUCCESS (glm5_2_nv, k1/k2/k3, first-attempt)
- 1× NV-SUCCESS (dsv4p_nv, k3, first-attempt pexec)
- 1× NV-ZOMBIE-EMPTY (glm5_2_nv, 207621→12 chars, sent error SSE chunk)
- 0× NV-TIER-FAIL, 0× NV-EMPTY-FASTBREAK, 0× NV-MS-FB, 0× NV-PEER-FB
- ms_gw: MS-OK-STREAM/MS-STREAM-DONE normal (glm5.2 + dsv4, 23-373KB)

### 2.6 DB 状态
- nv_tier_attempts: 0 rows (post-restart clean)
- ms_gw: 4 total, 0 OK (modelscope queries)
- fallback 触发: 0
- 无 key_cycle_429s

### 2.7 容器配置
- 容器状态: nv_gw Up 34 minutes (healthy)
- compose md5: `0dff5e071f93fc571baa92c55a21becc`
- NVU_PEER_FB_SKIP_MODELS: "" (空 — all models enabled for peer-fb, R1000)
- NVU_MS_GW_FALLBACK_MODELMAP: "glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms" (dsv4p_nv removed per R1265)
- 核心参数: UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=210, TIER_COOLDOWN_S=15, KEY_COOLDOWN_S=25, FASTBREAK=1/1/1, NVU_TIER_BUDGET_DSV4P_NV=72, NVU_TIER_BUDGET_GLM5_2_NV=96
- 全部参数 floor/optimal

## 3. 决策: NOP

### 3.1 失败分析
- **10 zombie** (glm5_2_nv): NVCF content-filter stop → code-level, not config-fixable. Gateway detection+error-chunk 正确触发 openclaw fallback
- **3 ATE** (dsv4p_nv): 全部 pre-restart，R1265 修复 (dsv4p_nv 从 MODELMAP 移除 → peer-fb 优先) 已生效。Post-restart 0 ATE
- **1 IncompleteRead** (glm5_2_nv): pre-restart, transient stream-level error

### 3.2 R1265 验证
- dsv4p_nv 已从 MODELMAP 移除 ✓ (容器 env 确认: glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms)
- PEER_FB_SKIP_MODELS="" → dsv4p ATE 现在走 peer-fallback 而非 ms_gw ✓
- Post-restart: dsv4p_nv 1/1 first-attempt pexec success (4336ms), 0 tier_attempts
- 需要更多流量观察 peer-fb 效果

### 3.3 参数状态
- 全部参数 floor/optimal, 无优化空间
- compose md5 未变 (R1265 后稳定)
- 0 tier_attempts post-restart → 无 signal 需要调整

## 4. 结论
**NOP** — false trigger + 所有失败 code-level (zombie=NVCF content-filter, ATE=pre-restart 已修复)。Post-restart 数据清洁 (3/4 success, 0 tier_attempts)。全部参数 floor/optimal。零参数变更。铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2
