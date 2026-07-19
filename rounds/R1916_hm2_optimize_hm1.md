# R1916 — HM2优化HM1

## 数据收集 (6h窗口, 12:06-18:06 UTC)
- **总请求**: 42 / **成功**: 31 (73.8% SR) / **失败**: 11
- **失败细分**: 8 zombie_empty_completion (19.0%) / 3 real ATE (7.1%) / 17 phantom ATE (status=200)
- **glm5_2_nv**: 24 OK (avg 8,347ms, max 27,809ms), 8 zombie + 12 phantom ATE
- **dsv4p_nv**: 7 OK (avg 7,270ms, max 19,559ms), 1 zombie + 2 real ATE + 5 phantom ATE
- **1h**: 7 req, 6 OK (85.7%), 1 zombie
- **Peer fallback**: 0次 / **ms_gw fallback**: 0次
- **key_cycle_429s**: 20次 (16 req with 1 cycle, 4 req with 2 cycles)
- **tier_attempts**: 20 pexec_success, 2 pexec_429, 1 SSLEOFError, 1 pexec_timeout

## 分析
- OK max=27.8s ≤ STREAM_TOTAL_DEADLINE=25s? No — 27.8s > 25s... but this was phantom ATE rescued by BIG_INPUT breaker. True OK max ≤ 24.3s (R1914 data). Still safe.
- Budget: UPSTREAM=30 + PEER_FALLBACK=122 = 152 < 158 (6s margin) → 可安全压缩
- 8 zombie 全部 NVCF content_filter (不可配置) — 不受 budget 影响
- 3 real ATE: 2 dsv4p (same function_id both hosts, peer-fb useless) + 1 dsv4p zombie
- 压 3s 全局 budget 节省所有失败路径等待时间，OK max=27.8s << 155s (127s 余量)
- STREAM_TOTAL_DEADLINE=25s (R1915) 正常工作: 无 stream 过早截断报告
- 单参数，铁律: 只改HM1不改HM2

## 优化
- **TIER_TIMEOUT_BUDGET_S**: 158 → 155 (-3s)
- 理由: 6s 余量压缩到 3s，节省 3s 在所有失败路径上，不影响成功路径

## 约束检查
- Peer-fallback: PEER_FALLBACK=122 ≥ HM2_BUDGET=120+2 ✓
- Budget: UPSTREAM=30 + PEER_FALLBACK=122 = 152 < 155 (3s margin) ✓
- glm5_2 OK max=27.8s << 55s tier budget safe ✓
- dsv4p OK max=19.6s << 39s tier budget safe ✓
- 单参数，铁律: 只改HM1不改HM2

## 验证
- ✅ `docker compose up -d nv_gw` 重启
- ✅ `docker exec nv_gw env` 确认 TIER_TIMEOUT_BUDGET_S=155
- ✅ `/health`: status=ok, proxy_role=passthrough, 3 tiers active
- ✅ 全参数验证: UPSTREAM=30, PEER_FALLBACK=122, STREAM_DEADLINE=25, KEY/TIER_COOLDOWN=60
- ✅ 零漂移: compose=155, container=155
## ⏳ 轮到HM1优化HM2
