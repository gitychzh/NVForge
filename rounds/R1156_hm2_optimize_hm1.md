# HM2 Optimize HM1 — Round R1156

## 1. 触发分析
- **cron 脚本输出**: "这是我提交的, 不触发"
- HM1 最新 commit: fbf0e43 (R821, opc2_uname) — HM2 自提交
- HM1 最后 HM1 自提交: 7625e14 (R818, opc_uname, 2026-07-08)
- HM1 本地落后 333 rounds (R821→R1155)
- **结论: FALSE TRIGGER** — HM1 未提交新 commit，cron 误派遣

## 2. 数据收集 (改前必有数据)

### 2.1 容器状态
- 容器: nv_gw, 重启于 2026-07-10T19:03:27Z (~16h ago)
- Compose MD5: 7975939c245761e451a8813852dcb9bf (unchanged, same as R1154)
- 日志: NV-ZOMBIE-EMPTY + NV-ZOMBIE-ERROR-CHUNK 模式 → openclaw fallback 触发

### 2.2 6h 总体
- 45req / 24OK(53.3%SR) / 21fail
- 全部 nv_integrate, 全部 glm5_2_nv
- dsv4p_nv: 0 traffic 6h; since restart: 3/3 pexec OK (100% SR)
- kimi_nv: 24h 7/7 OK (100% SR)
- minimax_m3_nv: 24h 9/9 OK (100% SR)

### 2.3 错误分类
- 21 zombie_empty_completion (100% of failures)
- Tier attempts: 3× 429_integrate_rate_limit (glm5_2_nv)
- Fallback: 0 occurred (预期行为, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv)
- dsv4p_nv ATE: 7 in 24h, ALL before container restart (last: 2026-07-10 18:03)
- Zero ATE since restart (19:03Z→now)

### 2.4 僵尸详情
- glm5_2_nv integrate, NVCF content-filter 返回 stop+12chars (160K-166K input)
- avg_dur=5,205ms, max_dur=12,569ms
- Gateway 正确检测 → error-chunk → openclaw fallback
- Per-key zombie分布: K0=3, K1=4, K2=3, K3=6, K4=5 (均匀分布)
- OK latency per-key: avg 4,991-7,519ms, p50 3,973-6,566ms

### 2.5 Hourly 趋势 (glm5_2_nv)
- 20:00: 7/7 OK (100%) avg=6,024ms
- 21:00: 9/9 OK (100%) avg=5,819ms
- 22:00: 1/9 OK (11.1%) avg=4,092ms
- 23:00: 4/9 OK (44.4%) avg=4,510ms
- 00:00: 1/7 OK (14.3%) avg=6,136ms
- 01:00: 2/4 OK (50.0%) avg=4,830ms

### 2.6 当前参数 (全部 floor/optimal)
- UPSTREAM_TIMEOUT=66, BUDGET=198, TIER_COOLDOWN_S=15, KEY_COOLDOWN_S=25
- FASTBREAK: pexec=1, empty200=2, integrate=1
- NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
- NVU_TIER_BUDGET_DSV4P_NV=72, NVU_TIER_BUDGET_GLM5_2_NV=96, NVU_TIER_BUDGET_MINIMAX_M3_NV=100
- NVU_MS_GW_FALLBACK_TIMEOUT=180, NVU_PEER_FALLBACK_TIMEOUT=66
- KEY_AUTHFAIL_COOLDOWN_S=60
- ms_gw: 6h 0 requests; ms_gw EMPTY_200_FASTBREAK_THRESHOLD=3 (floor)

## 3. 决策: NOP (Zero Param)

### 3.1 原因
1. **全部失败为 zombie_empty_completion** — NVCF content-filter 返回 stop+12chars 对 160K+ 输入
2. Gateway 检测+error-chunk 正确 → openclaw 自动 fallback
3. 所有参数已 floor/optimal — 无优化空间
4. dsv4p_nv 0 traffic 6h — 无数据支持优化
5. Zero ATE since container restart — 参数稳定
6. kimi_nv + minimax_m3_nv 100% SR — 无异常
7. ms_gw 0 traffic — 无优化机会
8. Tier attempts 仅 3× 429 rate limit (正常)

### 3.2 铁律
- 只改HM1不改HM2 ✅
- 改前必有数据 ✅
- 无参数调整

## ⏳ 轮到HM1优化HM2