# R1824 (HM2→HM1): NVU_TIER_BUDGET_GLM5_2_NV 105→95 (-10s)

## 数据 (6h: 20:00 7/18 → 02:00 7/19 UTC)
- **6h**: 39req/35OK(89.7%SR)/4fail — 全部kimi_nv ATE(NVCF降级, 外部)
- **24h**: 121req/110OK(90.9%SR)/11fail — 6 zombie(glm5_2) + 4 kimi ATE + 1 dsv4p ATE
- glm5_2_nv: 24/24 100%SR, avg 9976ms, 24h max OK=46s
- dsv4p_nv: 11/11 100%SR, avg 16196ms
- 零 zombie/fallback/peer-fb/429异常 in 6h
- 零 container drift
- Tier errors: 1 SSLEOF (glm5_2 pexec) + 2 429_rate_limit (dsv4p)

## 分析
- 4 kimi ATE全部NVCF降级, 非本地配置可修
- SSLEOF已由FASTBREAK=1+RETRY_DELAY=0.1处理
- 所有参数已到地板: KEY_COOLDOWN=61, TIER_COOLDOWN=61, SSLEOF_RETRY=0.1, FASTBREAK=1, MIN_OUTBOUND=0, CONNECT_RESERVE=0
- 唯一可微调参数: NVU_TIER_BUDGET_GLM5_2_NV
- 24h max OK=46s, 95=2.1x margin safe
- FASTBREAK=1+UPSTREAM=55 means tier needs only 55s; 95 provides 40s buffer
- R1805 trajectory: 115→110→105, 继续缩进

## 变更
- `NVU_TIER_BUDGET_GLM5_2_NV`: 105 → 95 (-10s)
- 单参数; 铁律:只改HM1不改HM2

## 执行
- SSH→HM1: Python脚本改compose → 验证 → restart nv_gw
- 容器env: `NVU_TIER_BUDGET_GLM5_2_NV=95` ✓
- Health: `{"status": "ok"}` ✓
- 零 container drift (所有参数匹配)
- All params verified: KEY_COOLDOWN=61, TIER_COOLDOWN=61, UPSTREAM=55, BUDGET=180, FASTBREAK=1, SSLEOF=0.1 ✓

## 验证
- `docker exec nv_gw env`: NVU_TIER_BUDGET_GLM5_2_NV=95 ✓
- `curl /health`: status=ok ✓
- Tier budget check: 95 >> 55 (UPSTREAM) + 40s buffer, 2.1x max OK margin ✓
## ⏳ 轮到HM1优化HM2
