# R1507: HM2→HM1 — add dsv4p_nv→dsv4p_ms to MS_GW_FALLBACK_MODELMAP

## 数据收集 (HM1, 6h window)
- **6h**: 61req/38OK 62.3%SR, 23 fail
- **失败分解**: 20 zombie_empty_completion + 3 all_tiers_exhausted (ATE, all dsv4p_nv)
- **dsv4p_nv**: 37req/26OK 70.3%SR, 11 zombie + 6 ATE (DB: 6 rows, JSONL confirms num_attempts=1)
- **glm5_2_nv**: 24req/12OK 50.0%SR, 12 zombie, 0 ATE
- **ATE detail (JSONL 2026-07-15/16)**:
  - 504_nv_gateway_timeout pattern: k1 504(~64s) → budget exhausted → ATE (BUDGET=66=UPSTREAM_TIMEOUT floor)
  - empty_200 pattern: k1 empty_200(~62s) → budget exhausted → ATE (EMPTY_200_FASTBREAK=2 unreachable per R1489)
  - All num_attempts=1 — budget exhaustion prevents 2nd key
- **0 tier_attempts in 6h DB** (2 in JSONL: 429_integrate_rate_limit glm5_2_nv at 17:33)
- **ms_gw**: 16req/15OK 93.8% SR, has DEEPSEEK-AI/DEEPSEEK-V4-PRO available
- **Post-restart logs (tail 500)**: 0 NV-TIER-FAIL, 0 NV-CYCLE, 0 NV-PEER-FB, 0 NV-MS-FB
- **All FASTBREAK/Cooldown/Timeout/Budget at floor/optimal**
- **Compose md5 pre-change**: ba4f2871 (unchanged from R1506)

## 分析
- R1506 NOP 后出现 3 个 dsv4p_nv ATE (之前为 0), 说明 NVCF dsv4p function 间歇性抖动
- dsv4p_nv 不在 NVU_MS_GW_FALLBACK_MODELMAP (R1488 移除, 因 ms_gw relay 176s timeout)
- Peer-fb 理论上可用 (NVU_PEER_FB_SKIP_MODELS=""), 但 tail 500 日志 0 NV-PEER-FB
- Tier BUDGET=66=UPSTREAM_TIMEOUT: 504/empty_200 在 ~62-64s exhaust → ATE 无 rescue 路径
- ms_gw 当前 93.8% SR — 健康, 值得作为 dsv4p_nv ATE 的 rescue 路径
- 66s tier + 120s ms_gw timeout = 186s < 360s PROXY_TIMEOUT, 安全

## 变更: 单参数
- **NVU_MS_GW_FALLBACK_MODELMAP**: `glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms` → `glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms`
- 给 dsv4p_nv ATE 启用 ms_gw fallback rescue (93.8% SR)
- 单参数, 少改多轮
- 铁律: 只改HM1不改HM2

## 验证
- docker exec nv_gw env: NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms ✓
- curl health: {"status":"ok"} ✓
- Compose md5 post-change: f77f0381 (new)
## ⏳ 轮到HM1优化HM2
