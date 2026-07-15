# HM2 Optimize HM1 — Round R1472

## 触发分析
- cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit: 5f46e1a (R1471, opc2_uname) — HM2自提交
- 判定: FALSE TRIGGER, double-dispatch (R1395→R1472 chain, 78th consecutive)
- HM1 git log: R1206 (266 rounds behind HM2)
- HM1 compose md5: 45c1f284 (unchanged since R1467 container restart)

## HM1 数据 (6h window, 2026-07-15T23:10 UTC)
- nv_gw restart: 2026-07-15T13:09:29Z (stable, 10h+ uptime)
- 6h requests: 40req/16OK/24err → 40.0% SR
- Hourly: 09:00 0/2, 10:00 2/6, 11:00 2/6, 12:00 3/7, 13:00 5/9, 14:00 3/7, 15:00 1/3
- Error breakdown: 14 zombie (NVCF content-filter), 10 ATE (NVCF 504 pexec timeout)
- Zombie detail: dsv4p_nv=3 (avg input 218K), glm5_2_nv=11 (avg input 217K) — NVCF content-filter stop+12chars
- ATE detail: dsv4p_nv=9 (avg 63932ms pexec 504), glm5_2_nv=1 (187171ms)
- 0 NVStream_IncompleteRead, 0 tier_attempts
- ms_gw: 26req/19OK 73.1% SR (healthy fallback)
- By model: glm5_2_nv 24req/12OK 50.0% SR, dsv4p_nv 16req/4OK 25.0% SR

## 决策: NOP
- 所有参数已在地板值: KEY_COOLDOWN_S=25, TIER_COOLDOWN_S=15, MIN_OUTBOUND_INTERVAL_S=0, UPSTREAM_TIMEOUT=66, NVU_CONNECT_RESERVE_S=0, NVU_EMPTY_200_FASTBREAK=2, NVU_SSLEOF_RETRY_DELAY_S=1.0, TIER_TIMEOUT_BUDGET_S=205
- NVU_FORCE_STREAM_UPGRADE=0, NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
- NVU_FALLBACK_HEALTH_THRESHOLD=0.05, KEY_AUTHFAIL_COOLDOWN_S=60
- 错误根因: NVCF upstream (pexec 504 timeout, content-filter zombie) — 非HM1配置可修复
- ms_gw healthy at 73.1% SR with EMPTY_200_FASTBREAK_THRESHOLD=3
- 零参数修改, 零compose修改, 零容器重启
- 铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
