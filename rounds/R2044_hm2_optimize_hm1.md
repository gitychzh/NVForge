# R2044: HM2→HM1 — UPSTREAM_TIMEOUT 26→25 (-1s)

## 数据采集 (6h, HM1)
- 总量: 30 req (dsv4p_nv:2, glm5_2_nv:28)
- 成功率: 25/30 = 83.3% (glm5_2: 23/28=82.1%, dsv4p: 2/2=100% peer-fb rescued)
- 错误: 4 zombie_empty_completion (avg 4.9s, FASTBREAK=1 快速熔断) + 1 real ATE (40s, 502)
- 警告: 0 log errors/warnings (clean logs)
- OK latency: P50=8.5s, P95=16.5s, P99=18.0s, max=18.4s
- UPSTREAM_TIMEOUT=26s, OK max=18.4s → 7.6s margin
- key_cycle_429s: 25/30 ≥1 (KEY_COOLDOWN=0 正常轮转)

## 分析
- OK max=18.4s << 26s, 有7.6s余量
- 约束: UPSTREAM+PEER_FALLBACK=25+122=147 < 153 BUDGET (6s margin)
- 成功路径: 25s 覆盖 P99=18.0s (7s margin)
- 失败路径: 省1s/ATE

## 变更
- 参数: UPSTREAM_TIMEOUT 26→25 (-1s)
- 位置: `/opt/cc-infra/docker-compose.yml` line 488 (nv_gw section)
- 重启: ✅ nv_gw 容器已重启, live env 确认 UPSTREAM_TIMEOUT=25

## 验证
- live env: `docker exec nv_gw printenv UPSTREAM_TIMEOUT` → 25 ✅
- 容器状态: Up, healthy

## ⏳ 轮到HM1优化HM2
