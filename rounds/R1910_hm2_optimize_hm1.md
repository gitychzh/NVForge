# R1910 (HM2→HM1): TIER_TIMEOUT_BUDGET_S 166→164 (-2s)

## 6h 数据 (R1908 部署后)
- **总请求**: 47 (34 OK / 13 fail, 72.3% SR)
- **错误**: 11 zombie_empty_completion + 2 real ATE (status=502)
- **Per-model**:
  - glm5_2_nv: 34req (25OK/9fail, avg 6990ms, p95 15181ms, max 16462ms)
  - dsv4p_nv: 13req (9OK/4fail, avg 7596ms, p95 16214ms, max 19559ms)
- **Zombie durations**: 3.6s–35.7s, 11 zombie (9 glm5_2_nv, 2 dsv4p_nv)
- **Real ATE**: 2 dsv4p_nv ATE status=502 (2-3s instant fail, FASTBREAK=1)
- **Phantom ATE**: 23 status=200 (empty-200 rescued, egress空)
- **OK max**: 19.6s (safe under current 23s STREAM deadline)
- **Fallback**: 0 触发 (all fallback_occurred=f)
- **Tier errors**: pexec_success 20 / pexec_429 2 / pexec_SSLEOFError 1 / pexec_timeout 1

## 分析
R1908 STREAM_TOTAL_DEADLINE_S 25→23 有效：SR 72.3% 持平（R1907 65.2%→R1908 72.3%→R1910 72.3%），zombie 13→11→11。
OK max=19.6s << UPSTREAM=30s，安全。预算检查：UPSTREAM=30 + PEER=122 = 152 < 164（12s margin）。
继续微缩 TIER_TIMEOUT_BUDGET_S：无成功路径误杀风险，仅压缩失败路径等待时间。

## 变更
- **TIER_TIMEOUT_BUDGET_S**: 166→164 (-2s)
- 预算检查: 30 (UPSTREAM) + 122 (PEER) = 152 < 164 (12s margin, safe)
- 预计效果: 压缩 ATE 失败路径等待时间 2s，成功路径无影响
- 单参数; 铁律: 只改HM1不改HM2

## 验证
- ✅ python scp 修改 compose line 490
- ✅ `docker compose up -d nv_gw` 重启
- ✅ `docker exec nv_gw env` 确认 TIER_TIMEOUT_BUDGET_S=164
- ✅ `/health`: status=ok, proxy_role=passthrough, 3 tiers active
- ✅ 全参数验证: STREAM_TOTAL_DEADLINE_S=23, UPSTREAM=30, PEER_FALLBACK=122, PEER_FALLBACK_ENABLED=1
## ⏳ 轮到HM1优化HM2
