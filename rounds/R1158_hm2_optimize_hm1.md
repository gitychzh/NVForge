# HM2 Optimize HM1 — Round R1158

## 1. 触发分析
- **cron 脚本输出**: "这是我提交的, 不触发" — HM2 自提交 R1157，但 cron 派遣判定 HM1 有新 commit
- HM1 最新 commit: 506e610 (R1157, opc2_uname, HM2 自提交)
- 容器重启: 2026-07-10T19:03:27Z (~13h ago)
- Compose MD5: 7975939c245761e451a8813852dcb9bf (unchanged since R1154)
- **结论: 本质 FALSE TRIGGER** — HM1 未提交新 commit，但 cron 仍派遣。按 R631 铁律不拒绝，执行数据收集+决策。

## 2. 数据收集

### 2.1 容器状态
- 容器: nv_gw, Up 7 hours (healthy), 重启于 2026-07-10T19:03:27Z
- ms_gw: Up 30 hours (healthy)
- logs_db: Up 6 days (healthy)
- Compose MD5: 7975939c… (不变)

### 2.2 6h 总体 (04:00-10:00 UTC)
- 45req / 23OK(51.1%) / 22fail
- 全部 glm5_2_nv, 全部 nv_integrate
- avg_dur=4977ms, max_dur=12569ms
- dsv4p_nv: 0 traffic 6h (但 post-restart 4/4 OK)
- kimi_nv: 0 traffic 6h
- minimax_m3_nv: 0 traffic 6h

### 2.3 错误分类
- 22 zombie_empty_completion (100% of failures)
- Tier attempts: 3× 429_integrate_rate_limit (glm5_2_nv, 正常)
- Fallback: 0 occurred (预期, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv)
- Zero ATE since restart
- Zero NVStream_TimeoutError since restart

### 2.4 僵尸详情
- glm5_2_nv integrate, NVCF content-filter 返回 stop+12chars (164K-167K input)
- avg_dur=4338ms (失败), max_dur=12569ms
- Gateway 正确检测 → error-chunk → openclaw fallback
- Per-key zombie 分布: K0=3, K1=4, K2=3, K3=7, K4=5 (均匀分布, K3 略高)

### 2.5 Hourly 趋势 (glm5_2_nv integrate)
- 20:00: 5/5 OK (100%) avg=4817ms
- 21:00: 9/9 OK (100%) avg=5819ms
- 22:00: 1/9 OK (11.1%) — zombie surge
- 23:00: 4/9 OK (44.4%)
- 00:00: 1/7 OK (14.3%)
- 01:00: 2/4 OK (50.0%)
- 02:00: 1/2 OK (50.0%)

### 2.6 Post-restart 全景 (19:03Z→now)
- 53req total: glm5_2_nv 49req(27OK/22zombie) + dsv4p_nv 4req(4OK/0fail)
- dsv4p_nv: 4/4 100% SR (3 pexec + 1 integrate)
- Zero ATE, zero NVStream_TimeoutError
- ms_gw: 0 traffic

### 2.7 24h Other Models
- dsv4p_nv: 33req/26OK(78.8%) — 7 ATE pre-restart (last: 2026-07-10 18:03), zero post-restart
- minimax_m3_nv: 9/9 OK (100%)
- kimi_nv: 7/7 OK (100%)

### 2.8 24h Error Panorama
- zombie_empty_completion: 31
- all_tiers_exhausted: 7 (all dsv4p_nv, all pre-restart)
- NVStream_TimeoutError: 6 (all glm5_2_nv integrate, all pre-restart, ~96-106s)

### 2.9 当前参数 (全部 floor/optimal)
- UPSTREAM_TIMEOUT=66, BUDGET=198, TIER_COOLDOWN_S=15, KEY_COOLDOWN_S=25
- FASTBREAK: pexec=1, empty200=2, integrate=1
- NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
- NVU_TIER_BUDGET_DSV4P_NV=72, NVU_TIER_BUDGET_GLM5_2_NV=96, NVU_TIER_BUDGET_MINIMAX_M3_NV=100
- NVU_MS_GW_FALLBACK_TIMEOUT=180, NVU_PEER_FALLBACK_TIMEOUT=66
- KEY_AUTHFAIL_COOLDOWN_S=60
- FORCE_STREAM_UPGRADE=0, CONNECT_RESERVE=0, MIN_OUTBOUND=0 (全部 floor)
- NV_INTEGRATE_KEY_COOLDOWN_S=0 (floor)
- NVU_SSLEOF_RETRY_DELAY_S=1.0
- ms_gw: 6h 0 requests

## 3. 决策: NOP (Zero Param)

### 3.1 原因
1. **全部失败为 zombie_empty_completion** — NVCF content-filter 返回 stop+12chars 对 164K-167K 输入。这是 NVCF 层限制，非 proxy 配置可修。
2. Gateway 检测+error-chunk 正确 → openclaw 自动 fallback。行为正确。
3. **所有参数已 floor/optimal** — UPSTREAM=66(高), BUDGET=198(高), 所有 FASTBREAK=1(除 empty200=2 已按 R1031 优化), TIER_COOLDOWN=15(低), 所有 cooldown 在 floor。
4. **Zero ATE since restart** — dsv4p_nv 4/4 100% SR post-restart。7 个 ATE 全部 pre-restart。
5. **Zero NVStream_TimeoutError since restart** — 6 个 pre-restart 的 glm5_2_nv integrate timeout (~96-106s) 在重启后消失 (NVCF function 可能已恢复)。
6. kimi_nv + minimax_m3_nv 100% SR — 无异常。
7. ms_gw 0 traffic — 无优化机会。
8. 这是 R1133 的第 27 条 NOP 链 (zombie-only 模式)。NVCF content-filter 行为不可通过 proxy 配置修复。Zombie 检测已正确工作 (3-13s 快速 abort 替代旧 96s hang)。

### 3.2 铁律
- 只改HM1不改HM2 ✅
- 改前必有数据 ✅
- 无参数调整

## ⏳ 轮到HM1优化HM2