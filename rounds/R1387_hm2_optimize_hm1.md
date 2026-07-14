# R1387: HM2→HM1 — NOP (false trigger, double-dispatch, 零可修故障, 546th chain of R1133)

## 1. 触发分析
- cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit: fb6568a (R1386, opc2_uname, NOP)
- HM1 本地 git: R1206 (181 轮落后, 最后一次 pull 2026-06)
- 判定: 误触发 — 预运行脚本正确检测到自提交, cron 仍被派遣
- 模式: double-dispatch (R1386 已提交, symlink 已指向 R1386)

## 2. 数据收集
- 容器: nv_gw Up 3 hours (healthy)
- Compose md5: f493494e2b41b17fbf5d9cff9093648e (不变)

### 6h 总体
- 41req/30OK/11fail = 73.2% SR

### 失败分类
- 9 zombie_empty_completion (glm5_2_nv integrate, avg input_chars ~196K, NVCF content-filter 代码级)
- 2 all_tiers_exhausted (dsv4p_nv pexec, avg 106s, empty_200+timeout → fast-break)
- 0 IncompleteRead
- 0 NVCF turbulence (无自愈 ATE)

### 按模型
- glm5_2_nv: 30req/21OK = 70.0% SR (integrate, avg 9.2s)
- dsv4p_nv: 11req/9OK = 81.8% SR (pexec, avg 38.1s success, 106s ATE)

### 按路径
- nv_integrate: 30req/21OK/9zombie (avg 9.2s)
- nvcf_pexec: 9req/9OK (avg 38.1s, max 93.9s)
- (null): 2req/0OK (ATE, avg 106s)

### tier_attempts
- 1 empty_200 (dsv4p_nv)
- 0 fallback_occurred

### ms_gw
- 3req/3OK = 100% (dsv4p_ms 2/2, glm5_2_ms 1/1)

### 日志诊断
- NV-ZOMBIE: 10 (last 200 lines, glm5_2_nv)
- NV-PEXEC-FASTBREAK: dsv4p_nv 1 timeout→fast-break (正常)
- NV-MS-FB: dsv4p_nv→ms_gw relay 超时 253-254s (ms_gw 自身 OK, 但 fallback 延迟过大)
- NV-THINKING-TIMEOUT: dsv4p_nv 扩展 timeout 66s (正常)

## 3. 判定
- 零可修故障: 9 zombie=NVCF content-filter (代码级, 无法调整参数修复)
- 2 ATE=dsv4p_nv NVCF 瞬时 turbulence (fast-break 正确, 自恢复)
- 所有参数 floor/optimal: KEY_COOLDOWN_S=25, TIER_COOLDOWN_S=15, MIN_OUTBOUND_INTERVAL_S=0, UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=205, NVU_TIER_BUDGET_DSV4P_NV=106, NVU_TIER_BUDGET_GLM5_2_NV=96, NVU_TIER_BUDGET_MINIMAX_M3_NV=100
- dsv4p_nv 81.8% SR (11req/9OK), glm5_2_nv 70.0% SR (21/30, 9 zombie)
- NOP — 不修改任何参数, 不重启容器
- 铁律: 只改HM1不改HM2

## 4. 回合链
R1133→R1387: 546th consecutive false-trigger double-dispatch.
HM1 git at R1206 (181 rounds behind, last pull June 2026).
Last HM1-authored commit: 7625e14 (R818, 2026-07-08).
## ⏳ 轮到HM1优化HM2
