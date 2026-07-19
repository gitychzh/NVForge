# R1911 (HM2→HM1): TIER_TIMEOUT_BUDGET_S 164→162 (-2s)

## 6h 数据 (R1910 部署后)
- **总请求**: 47 (34 OK / 13 fail, 72.3% SR) — 持平 R1910
- **错误**: 11 zombie_empty_completion + 2 real ATE (status=502)
- **Per-model**:
  - glm5_2_nv: 34req (25OK/9fail, avg 7813ms, p95 15181ms, max 35687ms)
  - dsv4p_nv: 13req (9OK/4fail, avg 8275ms, p95 16214ms, max 33734ms)
- **Zombie durations**: 3.6s–35.7s, 11 zombie (9 glm5_2_nv, 2 dsv4p_nv)
- **Real ATE**: 2 dsv4p_nv ATE status=502 (2-3s instant fail, FASTBREAK=1)
- **Phantom ATE**: status=200 (big_input breaker + empty-200 rescued)
- **OK max**: 19.6s (safe under current 30s UPSTREAM)
- **Fallback**: 0 触发 (all fallback_occurred=f)
- **Tier errors**: pexec_success 20 / pexec_429 2 / pexec_SSLEOFError 1 / pexec_timeout 1

## 分析
R1910 TIER_TIMEOUT_BUDGET_S 166→164 有效：SR 72.3% 稳定（R1908 72.3%→R1910 72.3%→R1911 72.3%），zombie 11 持平。OK max=19.6s << UPSTREAM=30s，安全。预算检查：UPSTREAM=30 + PEER=122 = 152 < 162（10s margin）。继续微缩 TIER_TIMEOUT_BUDGET_S：无成功路径误杀风险，仅压缩失败路径等待时间。

## 变更
- **TIER_TIMEOUT_BUDGET_S**: 164→162 (-2s)
- 预算检查: 30 (UPSTREAM) + 122 (PEER) = 152 < 162 (10s margin, safe)
- 预计效果: 压缩 ATE 失败路径等待时间 2s，成功路径无影响
- 单参数; 铁律: 只改HM1不改HM2

## 验证
- ✅ sed 修改 compose line 490
- ✅ `docker compose up -d nv_gw` 重启
- ✅ `docker exec nv_gw env` 确认 TIER_TIMEOUT_BUDGET_S=162
- ✅ `/health`: status=ok, proxy_role=passthrough, 3 tiers active
- ✅ 全参数验证: STREAM_TOTAL_DEADLINE_S=23, UPSTREAM=30, PEER_FALLBACK=122, PEER_FALLBACK_ENABLED=1
## ⏳ 轮到HM1优化HM2
