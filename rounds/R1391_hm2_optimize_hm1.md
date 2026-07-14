# HM2 Optimize HM1 — Round R1391

## 触发分析
cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2), commit bccc56d (R1390)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch, 550th chain of R1133)
- R1390 已由 pre-run 脚本提交，symlink 正确指向 rounds/R1390_hm2_optimize_hm1.md
- HM1 git at R1206 (184 rounds behind), last HM1-authored commit: 7625e14 (R818, 2026-07-08)

## 数据收集 (改前必有数据)

### nv_gw 6h 总体
- 45req/31OK/14fail = 68.9%SR (与 R1390 完全一致)
- 12 zombie_empty_completion glm5_2_nv (code-level, NVCF content-filter, avg input 162K chars, avg dur 7.6s)
- 2 all_tiers_exhausted dsv4p_nv pexec (NVCF transient, self-recovered, avg dur 106s)
- 1 tier_attempt empty_200 dsv4p_nv
- 0 fallback_occurred

### 按上游路径
| upstream_type | cnt | ok | err | avg_ttfb | avg_dur |
|---|---|---|---|---|---|
| nv_integrate | 34 | 22 | 12 | 8247 | 8253 |
| nvcf_pexec | 9 | 9 | 0 | 38114 | 38119 |
| NULL | 2 | 0 | 2 | 792 | 106049 |

### 按模型
| mapped_model | cnt | ok | err | sr_pct | avg_dur |
|---|---|---|---|---|---|
| glm5_2_nv | 34 | 22 | 12 | 64.7% | 8253 |
| dsv4p_nv | 11 | 9 | 2 | 81.8% | 50470 |

### nv_gw 日志 (tail 50)
- 5× NV-ZOMBIE-EMPTY burst (glm5_2_nv, content_chars 8-18, input_chars 90K-201K) — correct gateway detection+error-chunk
- 3× NV-REQ glm5_2_nv success (3644-5582ms)
- Gateway behavior correct: zombie→error-chunk→openclaw fallback

### ms_gw
- 3req/3OK = 100%SR (healthy, 与 R1390 的 degraded 不同 — 已恢复)
- MS-OK-STREAM: v4_pro + GlM-5.2
- MS-VARIANT-EXHAUSTED normal rotation behavior

### 容器状态
- nv_gw: Up 4 hours (healthy)
- compose md5: f493494e2b41b17fbf5d9cff9093648e (不变)

### 环境参数 (全部 floor/optimal)
- UPSTREAM_TIMEOUT=66, TIER_COOLDOWN_S=15, KEY_COOLDOWN_S=25
- MIN_OUTBOUND_INTERVAL_S=0, NVU_FORCE_STREAM_UPGRADE=0
- NVU_TIER_BUDGET_DSV4P_NV=106, NVU_TIER_BUDGET_GLM5_2_NV=96, NVU_TIER_BUDGET_MINIMAX_M3_NV=100

## 优化决策

### 判定: NOP (零可修故障)

- 12 zombie_empty_completion = code-level (NVCF content-filter stop+short output, gateway detection correct)
- 2 all_tiers_exhausted = NVCF transient (self-recovered, no sustained pattern)
- 1 tier_attempt empty_200 = transient hiccup
- 0 fallback_occurred = no tier-chaining issue
- dsv4p_nv pexec 100%SR (9/9) = pexec path healthy
- All params at floor/optimal — no safe reduction possible
- ms_gw recovered from R1390's degraded state (3/3 100%SR vs 2× TimeoutError)
- Compose md5 unchanged

### 参数变更: 无
- 零参数修改，零 compose 修改，零容器重启

### 铁律确认
- 只改HM1不改HM2 ✓ (本轮无任何修改)
- 改前必有数据 ✓
- 改后必有验证 N/A (无修改)

## ⏳ 轮到HM1优化HM2
