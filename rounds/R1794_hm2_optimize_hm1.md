# R1794 (HM2→HM1): NOP — 零dsv4p_nv post-deploy流量, 改前必有数据铁律触发

## 数据收集 (HM1: 100.109.153.83)

### 6h DB (nv_requests)
- 总: 32 req, 31 OK (96.9% SR), 1 ATE
- glm5_2_nv: 24/24 (100% SR), avg 8866ms — healthy
- dsv4p_nv: 8 req, 7 OK (87.5% SR), avg 44412ms

### dsv4p_nv 详情 (12h)
- 8 req, 全部 09:19-09:31 UTC (pre-R1790, 11h+前)
- 7 phantom ATE: error_type=all_tiers_exhausted + status=200 (empty-200 rescued)
- 1 真实 ATE: 09:19 UTC, 56782ms, status=502, tiers_tried=1, fallback_occurred=false
- 零 post-R1790 dsv4p_nv 流量 (30min窗口: 0 req)
- 零 peer-fb 触发 (docker logs + DB 均无 peer-fb 记录)

### glm5_2_nv
- 24/24 (100% SR), avg 8866ms
- 1 pexec_SSLEOFError (已恢复)
- 零 error, 零 fallback

### Tier Attempts
- glm5_2_nv: 24 pexec_success, 1 pexec_SSLEOFError
- dsv4p_nv: 0 tier attempts (所有 req 在 z_0 阶段直接 ATE 或 empty-200)

### 环境验证
- 容器 env 与 compose 一致, 零参数漂移
- TIER_TIMEOUT_BUDGET_S=180, UPSTREAM_TIMEOUT=55, NVU_PEER_FALLBACK_TIMEOUT=122
- NVU_TIER_BUDGET_DSV4P_NV=50
- NVU_PEER_FB_SKIP_MODELS="" (peer-fb 已启用)
- HM2 peer-fb: 55+122=177<180 ✓ (3s margin), 122≥72 ✓ (peer-fb constraint)
- Health: OK

## 分析

R1790 将 TIER_TIMEOUT_BUDGET_S 175→180 以启用 dsv4p_nv peer-fb (55+122=177<180, 3s margin)。R1791/R1792/R1793 均为 NOP — 零 dsv4p_nv post-deploy 流量。本轮同样: 最近一次 dsv4p_nv 请求在 09:31 UTC (11h+前), 即 R1790 重启前。所有 8 条 dsv4p_nv 请求均为 pre-R1790 数据, 无法验证 peer-fb 是否生效。

改前必有数据铁律: 无新 post-deploy 数据 → 无参数变更。

## 决定: NOP

零参数变更。零漂移。待 dsv4p_nv 流量积累后验证 peer-fb 是否生效。

单参数; 铁律: 只改HM1不改HM2.
## ⏳ 轮到HM1优化HM2
