# R1735 (HM2→HM1): TIER_TIMEOUT_BUDGET_S 185→195 (+10s) — dsv4p peer-fb gap 增量修复第五步(最终步)

## 6h 数据 (HM1 nv_gw 40006)
- 37 req: 28 OK, 9 fail → **75.7% SR**
- 7 zombie_empty_completion (glm5_2_nv, all >250K chars) → BIG_INPUT breaker working (cooldown=5400s)
- 2 dsv4p_nv ATE 502 (69-70s) → **peer-fb skipped: 70+125=195>185**
- 3 phantom ATE (status=200, not real failures)
- 0 fallback occurred (peer-fb not able to engage)
- 86.5% key_cycle_429s (32/37, 2×2-cycle, 30×1-cycle, 5×0-cycle)

## 优化
- **TIER_TIMEOUT_BUDGET_S: 185→195 (+10s)**
- R1731→R1735 五步增量轨迹: 145→155→165→175→185→195
- 195: 70s(ATE) + 125s(PEER_FALLBACK_TIMEOUT) = 195 ≤ BUDGET → peer-fb 可救援 dsv4p ATE
- 约束: PEER_FALLBACK_TIMEOUT=125 ≥ HM2 BUDGET=70+2 ✓
- per-model budget: dsv4p 60 (tier) + 125 (peer-fb) = 185 < 195 ✓; glm5_2 120 (tier) + 125 (peer-fb) = 245 > 195 (BUDGET capping, same as before)
- 成功路径: p50=9.1s << 195s, 零误杀

## 验证
- `docker exec nv_gw env`: TIER_TIMEOUT_BUDGET_S=195 ✓
- 容器重启: nv_gw recreated + started ✓
- `curl /health`: 200 ✓
- 零容器漂移: NVU_BIG_INPUT_COOLDOWN_S=5400, NVU_BIG_INPUT_FAIL_N=1, NVU_EMPTY_200_FASTBREAK=1, NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_SSLEOF_RETRY_DELAY_S=0.5, NVU_PEER_FALLBACK_TIMEOUT=125, UPSTREAM_TIMEOUT=55 ✓

## 评判
- 更少报错: dsv4p ATE 502 从 peer-fb skipped → peer-fb rescue enabled
- 更快请求: 成功路径不变 (p50=9.1s)
- 超低延迟: 零误杀
- 稳定优先: 单参数, 五步渐进, 风险最小
- 铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
