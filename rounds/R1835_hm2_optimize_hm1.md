# R1835 (HM2→HM1): BUDGET_DSV4P 41→39 (-2s)

## 6h数据 (2026-07-19 05:30 UTC)
- 41req/37OK(90.2%SR)/4 kimi ATE all NVCF-degraded
- dsv4p_nv: 12/12(100%), avg=15025ms, max=40603ms (latency still rising)
- glm5_2_nv: 25/25(100%), avg=7472ms, 零失败
- kimi_nv: 0/4(0%), 4 ATE all NVCF-degraded, 3 instant(1ms), 1 at 1715ms
- 0 fallback across all requests, 0 peer-fb triggered
- ms_gw: 0 requests in 6h, 2412req/165OK(6.8%) in 24h (ms_gw relay heavily degraded)
- 0 error/warn in nv_gw logs

## 优化决策
- **BUDGET_DSV4P_NV**: 41→39 (-2s)
- 理由: dsv4p avg=15s, max=40.6s 紧贴 41s budget (0.4s margin). R1834 43→41 已收紧, 继续推进: 39s 迫使最慢的 dsv4p 请求超时→peer-fb→HM2 独立 key pool 救援, 而非等待 40.6s 本地完成. glm5_2 稳定 7.5s 作为安全网.
- 约束: 39+122=161<180 ✓, 39+2=41≤122 ✓
- 铁律: 只改HM1不改HM2 ✓

## 变更
- `NVU_TIER_BUDGET_DSV4P_NV`: 41→39
- 容器重启: nv_gw recreated+started ✓
- env验证: `docker exec nv_gw env | grep NVU_TIER_BUDGET_DSV4P_NV` = 39 ✓
- health: `curl -s http://localhost:40006/health` = ok ✓

## 铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
