# R1825 (HM2→HM1): NVU_TIER_BUDGET_GLM5_2_NV 95→85 (-10s)

## 数据 (6h: 20:00 7/18 → 02:00 7/19 UTC)
- **6h**: 41req/37OK(90.2%SR)/4fail — 全部kimi_nv ATE(NVCF降级, 外部)
- **24h**: glm5_2_nv: 93/93 100%SR, avg 8461ms, max=21582ms (OK 46s)
- glm5_2_nv (6h): 25/25 100%SR, avg 9487ms, max 21582ms
- dsv4p_nv (6h): 12/12 100%SR, avg 15025ms
- kimi_nv ATE: 4次全部 all_tiers_failed_in_mapped_tier (status=502)
- 零 fallback/peer-fb/429/SSLEOF/zombie 异常 in 6h
- 零 container drift
- Tier errors: 2 429_rate_limit (dsv4p) + 1 pexec_SSLEOFError (glm5_2)

## 分析
- kimi_nv 完全无救援路径: peer-fb skipped (PEER_FB_SKIP_MODELS=kimi_nv) + ms_gw kimi_ms NOT IMPLEMENTED
- glm5_2_nv 100%SR 连续, 24h max OK=46s, 85=1.85x margin safe
- FASTBREAK=1+UPSTREAM=55 means tier needs only 55s; 85 provides 30s buffer
- R1805→R1824 trajectory: 115→110→105→95, 继续缩进
- 所有其他参数已到地板, 只此参数可微调

## 变更
- `NVU_TIER_BUDGET_GLM5_2_NV`: 95 → 85 (-10s)
- 单参数; 铁律:只改HM1不改HM2

## 执行
- SSH→HM1: sed改compose → 验证 → restart nv_gw
- 容器env: `NVU_TIER_BUDGET_GLM5_2_NV=85` ✓
- Health: `{"status": "ok"}` ✓
- 零 container drift (所有参数匹配)
- All params verified: KEY_COOLDOWN=61, TIER_COOLDOWN=61, UPSTREAM=55, BUDGET=180, FASTBREAK=1, SSLEOF=0.1 ✓

## 验证
- `docker exec nv_gw env`: NVU_TIER_BUDGET_GLM5_2_NV=85 ✓
- `curl /health`: status=ok ✓
- Tier budget check: 85 >> 55 (UPSTREAM) + 30s buffer, 1.85x 24h max OK margin ✓
## ⏳ 轮到HM1优化HM2
