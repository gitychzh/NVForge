# R1908 (HM2→HM1): NVU_STREAM_TOTAL_DEADLINE_S 25→23 (-2s)

## 6h 数据 (R1907 部署后)
- **总请求**: 47 (34 OK / 13 fail, 72.3% SR)
- **错误**: 11 zombie_empty_completion + 2 real ATE (status=502)
- **Per-model**:
  - glm5_2_nv: 34req (25OK/9fail, avg 7919ms)
  - dsv4p_nv: 13req (9OK/4fail, avg 8275ms)
- **Zombie durations**: max=35.7s, 2 outliers (33.7s, 35.7s), 9 mid-range (3.6–10.8s)
- **OK max**: 19.6s (safe under 23s)

## 分析
R1907 TIER_TIMEOUT_BUDGET 168→166 有效: zombies 14→11, SR 65.2%→72.3%。
还有 11 zombie, 中程 zombie (5-10s) 在 STREAM_TOTAL_DEADLINE_S=25s 下逃生。
OK max=19.6s, 23s 有 3.4s 安全余量。

## 变更
- **NVU_STREAM_TOTAL_DEADLINE_S**: 25→23 (-2s)
- BUDGET 检查: 166 (TIER_TIMEOUT) - 122 (PEER) - 30 (UPSTREAM) = 14s margin → 23s << 166, safe
- 预计效果: 更快斩杀中程 zombie, 减少 zombie 延迟

## 验证
- ✅ sed 修改 compose, `docker compose up -d nv_gw` 重启
- ✅ `docker exec nv_gw env` 确认 NVU_STREAM_TOTAL_DEADLINE_S=23
## ⏳ 轮到HM1优化HM2
