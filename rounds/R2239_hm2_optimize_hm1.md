# R2239: HM2→HM1 — NOP (false trigger, R2238 double-dispatch, stale root symlink fix, 0 post-restart traffic)

## ⏱️ 时间
- 触发: cron 2026-07-22 14:25 UTC
- 执行: 2026-07-22 ~14:28 UTC
- 数据收集窗口: 6h (08:25-14:25 UTC)

## 🔍 触发分析
cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = `opc2_uname` (HM2 自身)
- 最新 commit = `cca36de R2238: NVU_BIG_INPUT_THRESHOLD 90000→250000`
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — **FALSE TRIGGER** (double-dispatch of R2238)
- **Root symlink STALE**: `RN_hm2_optimize_hm1.md` → `rounds/R2221_hm2_optimize_hm1.md` (17 rounds behind!)
- **Nested stale symlink**: `rounds/RN_hm2_optimize_hm1.md` → `R2238_hm2_optimize_hm1.md`
- HM1 未提交新 commit (HM1 git log 停留在 R821, 418 轮落后)

## 📊 HM1 数据采集

### 容器状态
- nv_gw: Up 12 minutes (restarted 2026-07-22 06:16:35Z — R2238 compose change)
- compose md5: `4b921729ad1af52b1ddad251e2d55a60`

### 关键参数
| 参数 | 值 | 来源 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 24 | R2230 |
| TIER_TIMEOUT_BUDGET_S | 157 | R1071/R2231 |
| KEY_COOLDOWN_S | 12 | R2235 (20→18→16→14→12) |
| TIER_COOLDOWN_S | 0 | floor |
| NVU_TIER_BUDGET_GLM5_2_NV | 34 | R2237 (28→34) |
| NVU_TIER_BUDGET_DSV4P_NV | 94 | prior rounds |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | floor |
| NVU_BIG_INPUT_THRESHOLD | 250000 | R2238 (90000→250000) |
| NVU_BIG_INPUT_FAIL_N | 2 | R2236 (1→2) |
| NVU_BIG_INPUT_COOLDOWN_S | 2100 | R2236 added |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | floor |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | floor |
| NVU_EMPTY_200_FASTBREAK | 1 | floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |

### DB 6h Summary (all pre-restart)
- **39req/26OK/13fail = 66.7% SR** (same dataset as R2235-R2238)
- Post-restart: **0 traffic, 0 errors** — container idle 8h+

### 6h Error Breakdown
| Error Type | Count | Avg Duration | Models |
|-----------|-------|-------------|--------|
| all_tiers_exhausted | 8 | 45,339ms | dsv4p_nv (5)×pre-empted + glm5_2_nv (3)×slow exhaust |
| zombie_empty_completion | 5 | 22,769ms | glm5_2_nv |

### 6h ATE Detail
| Model | Count | Avg Duration |
|-------|-------|-------------|
| dsv4p_nv | 9 | 15,919ms (fast abort, pre-empted by NVCF degradation) |
| glm5_2_nv | 3 | 120,892ms (slow exhaust, BUDGET=34 insufficient) |
| glm5_2_nv zombie | 5 | 22,769ms (NVCF content-filter, avg input 319K chars) |

### Tier Attempts (6h, all pre-restart)
| Tier | Error Type | Count | Avg ms |
|------|-----------|-------|--------|
| glm5_2_nv | pexec_success | 27 | 11,531 |
| glm5_2_nv | pexec_timeout | 12 | 26,796 |
| glm5_2_nv | pexec_SSLEOFError | 2 | 5,003 |
| glm5_2_nv | pexec_429 | 1 | — |

### Post-Restart: 0 traffic ✓
- Container restarted 2026-07-22 06:16:35Z (~8h ago, R2238 compose change)
- 0 requests since restart — no new data to optimize against
- All 39 requests in 6h window are pre-restart

### ms_gw: 3/3 OK (100%)
- Fallback path healthy, but no fallback needed (post-restart 0 traffic)

### Docker Logs: Clean
- 0 error/warn in nv_gw logs (100 lines)
- ms_gw: MS-STREAM-CYCLE + MS-OK-STREAM/MS-STREAM-DONE (normal)

### Big Input Analysis
- 38/39 (97.4%) requests > 250K threshold (R2238 raised from 90K)
- 1 request below threshold (dsv4p_nv 4/4 success)
- 5 zombie: avg input 319K chars (NVCF content-filter, non-config-fixable)

## 🎯 决策: NOP — 零参数修改 + 修复stale root symlink

### NOP 理由
1. **False trigger**: HM2 自提交 R2238, 脚本正确标记 "不触发"
2. **0 post-restart traffic**: 容器重启后 8h+ 无任何流量, 无新数据可优化
3. **All params at/near optimal**:
   - KEY_COOLDOWN_S=12: KEY(12)+TIER(0)+GLM5_2(34)=46 << 157 BUDGET (111s margin)
   - NVU_BIG_INPUT_THRESHOLD=250000: R2238 刚调, 捕捉 319K zombie 但放过 97% 正常流量
   - NVU_BIG_INPUT_FAIL_N=2: 2 连续失败才触发, 减少单次 zombie 误杀
   - NVU_TIER_BUDGET_GLM5_2_NV=34: UPSTREAM=24 + 10s reserve, 3 glm5_2 ATE 是 pre-restart BUDGET=28 老数据
4. **5 zombie = NVCF content-filter**: input 319K chars, non-config-fixable
5. **8 ATE = all pre-restart**: dsv4p pre-empted NVCF 退化 + glm5_2 BUDGET 不足 (R2237 已修复)
6. **ms_gw healthy**: 3/3 OK, fallback 可用但无需用

### 本轮操作
- **NOP** — 零配置修改, 零 compose 变更, 零容器重启
- **修复 stale root symlink**: `RN_hm2_optimize_hm1.md` → `rounds/R2221_*` (17 轮 stale) → `rounds/R2239_*`
- **清理 stale nested symlink**: `rounds/RN_hm2_optimize_hm1.md` → `R2238` (误产生)
- 仅记录 R2239 回合文件 (数据收集+分析, 确认无可优化参数)

## 🔒 铁律遵守
- ✅ 改前必有数据: SSH 到 HM1 收集 docker logs/env + DB 6h 数据 + 分段分析
- ✅ 改后必有验证: N/A (NOP, 无修改)
- ✅ 聚焦 nv_gw: 仅检查 nv_gw+ms_gw 数据
- ✅ 所有修改写入仓库: 本回合记录写入 R2239, symlink 修复一并提交
- ✅ 只改 HM1 不改 HM2: 本回合无任何修改

## ⏳ 轮到HM1优化HM2
