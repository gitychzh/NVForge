# R1915 — HM2优化HM1

## 数据收集 (6h窗口)
- **总请求**: 44 / **成功**: 32 (72.7% SR) / **失败**: 12
- **失败细分**: 10 zombie (22.7%) / 2 real ATE (4.5%) / 21 phantom ATE
- **glm5_2_nv**: 31 req, 23 OK (74.2%), 8 zombie, max_ok=24.3s, 17x 429 cycles
- **dsv4p_nv**: 13 req, 9 OK (69.2%), 2 zombie + 2 ATE, max_ok=19.6s
- **Peer fallback**: 0次 / **ms_gw fallback**: 0次
- **NVU_STREAM_TOTAL_DEADLINE_S**: 23s (R1908: 25→23)

## 分析
- 最大OK延迟24.3s > 23s deadline → 正常流被截断产生zombie
- 10 zombie占22.7%，是主要失败来源
- 23s→25s回到之前值，OK max=24.3s < 25s safe，< UPSTREAM=30s

## 优化
- **NVU_STREAM_TOTAL_DEADLINE_S**: 23 → 25 (+2s)
- 理由: OK max=24.3s超过23s deadline，延长到25s既覆盖max又保持<30s上游安全
- 验证: docker exec确认=25，容器重启完成

## 结果预期
- zombie率下降 (stream不再被提前截断)
- SR提升 (减少误杀)
- 429 cycle不变 (此参数不影响出站)

## ⏳ 轮到HM1优化HM2
