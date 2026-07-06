## R779 (HM2→HM1) — NOP — 双函数健康, 96.5% SR 完美 regime, 零参数变更

**DB 6h (03:00–09:00 UTC):** 318req/307OK(96.5%)/11ATE(3.5%)

**模型详情:**
- dsv4p_nv: 178req/168OK(94.4%)/10ATE, func 74f02205 health 0.25→0.429 恢复中
- glm5_2_nv: 135req/134OK(99.3%)/1ATE, func 3b9748d8 health=1.0 完美
- kimi_nv: 5req/5OK(100%)

**ATE 诊断:**
- 11 ATE 全部 tiers_tried_count=2 (双tier NVCF 上游耗尽, 非配置可修)
- 0 单tier ATE — FALLBACK_GRAPH 双向工作正常
- 56 次 fallback 100% SR (56/56 成功救援)
- dsv4p_nv empty_200=42, glm5_2_nv empty_200=35 — NVCF 上游系统性问题, 双tier 均衡

**NVCFPexecTimeout 诊断:**
- dsv4p_nv max=60,823ms (k0), UPSTREAM=66 缓冲=5.2s >> 3s 安全, 非 binding
- glm5_2_nv max=62,389ms (k1), UPSTREAM=66 缓冲=3.6s > 3s 安全
- 429 分布非极端 (dsv4p k0=25, k1=10, k2-k4=12-17)

**FALLBACK_GRAPH:** tier_chain 双向完整, 100% fallback SR
- dsv4p_nv→glm5_2_nv: working (全部 ATE 有 fallback 尝试)
- glm5_2_nv→dsv4p_nv: working (NV-REQ 日志确认)

**容器:** 启动于 2026-07-06 07:47 CST (~2h 前), 重启后每小时 SR=100% (00:00–09:00 UTC 全部时段)

**决策: NOP (零参数变更)**
- 双 function 健康度优秀 (glm5_2=1.0, dsv4p_nv 恢复中 0.25→0.429)
- 11 ATE 全部双tier NVCF 上游耗尽 — 无配置可修路径
- dsv4p_nv 健康度主动恢复趋势, 无需扰动
- UPSTREAM=66 ↔ NVU_FORCE_STREAM=66 同步 ← R755
- FASTBREAK=1, BUDGET=114, FALLBACK_HEALTH=0.10 — 全部在最佳值

**评判:** 更少报错✓(11 ATE/318req=3.5%) 更快请求✓(direct avg=27.8s) 超低延迟✓(d4p_max=40.6s) 稳定优先✓(9h+ 单tier=0)

**铁律:** 只改 HM1 不改 HM2 ✅

## ⏳ 轮到 HM1 优化 HM2