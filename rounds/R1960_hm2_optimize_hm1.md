# R1960 (HM2→HM1): ⏸️ NOP — zero post-deploy traffic, all params floor/optimal, 5 zombie all NVCF-level

## 数据
- 6h: 43 req, 38 OK (88.4% SR), 5 fail (status=502, zombie_empty_completion)
- Post-R1959 restart (2026-07-19 18:35:33 UTC): **0 req** in ~13min — zero post-deploy traffic
- dsv4p_nv: 10 req, 0 genuine OK, 6 peer-fb rescued (100% rescue success), 4 genuine OK (pexec, avg=18211ms)
- glm5_2_nv: 33 req, 12 genuine OK (avg=11238ms, max=26165ms), 16 peer-fb rescued, 5 zombie
- kimi_nv: 0 traffic (6h)
- integrator: 0 (NV_INTEGRATE_MODELS="")
- pexec: 21 (all glm5_2_nv + dsv4p_nv genuine OK)
- key_cycle_429s: 17 (normal rotation, no 429 errors)

## 错误分解
- 5× `zombie_empty_completion` (status=502), all glm5_2_nv
  - Timestamps: 13:03, 14:03, 15:03, 18:04, 18:33 UTC (~60min spacing)
  - Root cause: NVCF empty200 degradation (function-level, not HM1 config-fixable)
  - R1959 BIG_INPUT_COOLDOWN=86400 deployed but zero post-deploy data to evaluate
- 22× `all_tiers_exhausted` + status=200 (phantom ATE, all peer-fb rescued)
  - dsv4p_nv: 6 phantom ATE, avg=40524ms, all peer-fb rescued → OK
  - glm5_2_nv: 16 phantom ATE, avg=9539ms, all peer-fb rescued → OK
- 0 real ATE with status=502
- 0 SSLEOF, 0 pexec timeout, 0 ms_gw fallback
- 0 tier-level errors in nv_tier_attempts (only 17 pexec_success)
- 0 fallback_occurred=true

## 容器日志
- docker logs nv_gw --tail 100: **(no error/warn found)** — zero errors post-R1959 restart
- Container healthy, StartedAt 2026-07-19T18:35:33Z

## 决策: NOP — zero post-deploy traffic, all params floor/optimal

**候选参数穷举评估**:

| 参数 | 当前值 | floor | 评估 | 结论 |
|------|--------|-------|------|------|
| UPSTREAM_TIMEOUT | 30 | ~25s | R1904: 32→30. OK max=26.2s < 30s (3.8s margin). 30+122=152<153 BUDGET safe. | **否决**: 已达安全边界, 再降risk截断genuine OK |
| TIER_TIMEOUT_BUDGET_S | 153 | — | R1953: 152→153 break boundary fix. dsv4p peer-fb: 20+122=142<153✓. | **否决**: 刚调整, 需数据验证 |
| KEY_COOLDOWN_S | 60 | ~60s | R1893: 42→60. KEY=TIER=60 per iron law. NVCF rate-limit window ~60s. | **否决**: 已达NVCF边界, 再降risk 429 cascade |
| TIER_COOLDOWN_S | 60 | ~60s | Same as KEY_COOLDOWN. | **否决**: 已达边界 |
| NVU_PEER_FALLBACK_TIMEOUT | 122 | ≥72 | R1744: 124→122. dsv4p peer-fb 20+122=142<153. | **否决**: 只需2-3s margin, 再降无意义 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 1 | 1=floor. | **否决**: floor |
| NVU_EMPTY_200_FASTBREAK | 1 | 1 | 1=floor. | **否决**: floor |
| NVU_SSLEOF_RETRY_DELAY_S | 0.1 | 0.0 | R1823: 0.2→0.1. Zero SSLEOF in 6h. | **否决**: 零SSLEOF, 无优化空间 |
| NVU_BIG_INPUT_COOLDOWN_S | 86400 | — | R1959: 21600→86400. Zero post-deploy data. | **否决**: 刚部署, 需数据验证 |
| NVU_BIG_INPUT_FAIL_N | 1 | 1 | 1=floor. | **否决**: floor |
| NVU_BIG_INPUT_THRESHOLD | 115000 | — | R1876: 130000→115000. | **否决**: 已有数据验证, 维持 |
| NVU_TIER_BUDGET_DSV4P_NV | 20 | — | R1957: 25→20. dsv4p NVCF dead, 0 genuine OK. | **否决**: 刚调整, dsv4p全死不可修 |
| NVU_TIER_BUDGET_GLM5_2_NV | 28 | — | R1958: 30→28. glm5_2 OK max=26.2s < 28s (1.8s margin). 28+122=150<153✓. | **否决**: 刚调整, margin仅1.8s, 再降risk |
| NVU_STREAM_TOTAL_DEADLINE_S | 25 | — | R1915: 23→25. OK max=26.2s > 25 (barely). | **否决**: 已有数据验证, 维持 |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 15 | — | R1802: 17→15. OK p99 TTFB=10.8s << 15s. | **否决**: 已有数据验证, 维持 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | 0 | 0=floor. | **否决**: floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | 0 | 0=floor. | **否决**: floor |
| NVU_CONNECT_RESERVE_S | 0 | 0 | 0=floor. | **否决**: floor |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | 0.0 | R982: 0.05. | **否决**: 已达安全边界 |

**NOP判定**: 零 post-deploy 流量 + 5 zombie 全部 NVCF 级 + 22 ATE 全 peer-fb 救援成功 + 全部参数 floor/optimal。R1959 的 BIG_INPUT_COOLDOWN=86400 改动需等待下次流量窗口才能评估效果。任何改动都是无数据支撑的猜测。

**铁律**: 只改HM1不改HM2

## 参数变更
无。NOP 回合。

## 验证
- ✅ docker ps → nv_gw Up 6 minutes (healthy)
- ✅ docker exec nv_gw env → all params confirmed
- ✅ docker logs nv_gw --tail 100 → (no error/warn found)
- ✅ DB 6h: 43/38 OK (88.4% SR), 5 zombie all NVCF-level, 0 config-fixable errors
- ✅ Post-R1959: zero traffic, zero errors

## ⏳ 轮到HM1优化HM2
