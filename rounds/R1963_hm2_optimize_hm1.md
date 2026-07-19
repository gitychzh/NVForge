# R1963 (HM2→HM1): ⏸️ NOP — near-zero post-deploy traffic (41min), all params floor/optimal, 5 zombie all NVCF-level

## 数据
- 6h: 41 req, 36 OK (87.8% SR), 5 fail (status=502, zombie_empty_completion)
- Post-R1961 restart (2026-07-19 18:35:33 UTC): **2 req** in ~41min — near-zero post-deploy traffic
- 1h burst: 4 req, 2 OK, 2 zombie (50% SR — tiny sample, statistically meaningless)
- dsv4p_nv: 10 req, 4 genuine OK (avg=21344ms, max=24784ms), 6 phantom ATE peer-fb rescued (avg=40525ms, 100% rescue)
- glm5_2_nv: 31 req, 10 genuine OK (avg=9954ms, max=26165ms), 16 phantom ATE peer-fb rescued (avg=9539ms), 5 zombie
- kimi_nv: 0 traffic (6h)
- integrator: 0 (NV_INTEGRATE_MODELS="")
- pexec: 15 (all glm5_2_nv pexec_success in tier_attempts)
- key_cycle_429s: 15 (all glm5_2_nv, all 1 cycle, normal rotation)
- 0 ms_gw fallback, 0 fallback_occurred=true

## 错误分解
- 5× `zombie_empty_completion` (status=502), all glm5_2_nv
  - Timestamps: 15:03, 18:04, 18:33, 19:03, 19:03 UTC (~60min spacing)
  - Root cause: NVCF empty200 degradation (function-level, not HM1 config-fixable)
- 22× `all_tiers_exhausted` + status=200 (phantom ATE, all peer-fb rescued)
  - dsv4p_nv: 6 phantom ATE, avg=40525ms, all peer-fb rescued → OK
  - glm5_2_nv: 16 phantom ATE, avg=9539ms, all peer-fb rescued → OK
- 0 real ATE with status=502
- 0 SSLEOF, 0 pexec timeout, 0 ms_gw fallback
- 0 tier-level errors in nv_tier_attempts (only 15 pexec_success)

## 容器日志
- docker logs nv_gw --tail 100: 1 zombie event (NV-ZOMBIE-EMPTY glm5_2_nv, input_chars=152998, content_chars=11), no other errors
- Container healthy, StartedAt 2026-07-19T18:35:33Z, Up 41 minutes
- No error/warn found in logs besides zombie

## 决策: NOP — near-zero post-deploy traffic, all params floor/optimal

**参数穷举评估**:

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
| NVU_BIG_INPUT_COOLDOWN_S | 86400 | — | R1959: 21600→86400. Near-zero post-deploy data. | **否决**: 刚部署, 需数据验证 |
| NVU_BIG_INPUT_FAIL_N | 1 | 1 | 1=floor. | **否决**: floor |
| NVU_BIG_INPUT_THRESHOLD | 115000 | — | R1876: 130000→115000. | **否决**: 已有数据验证, 维持 |
| NVU_TIER_BUDGET_DSV4P_NV | 20 | — | R1957: 25→20. dsv4p NVCF dead, 0 genuine OK post-restart dsv4p. | **否决**: 刚调整, dsv4p全死不可修 |
| NVU_TIER_BUDGET_GLM5_2_NV | 28 | — | R1958: 30→28. glm5_2 OK max=26.2s < 28s (1.8s margin). 28+122=150<153✓. | **否决**: 刚调整, margin仅1.8s, 再降risk |
| NVU_STREAM_TOTAL_DEADLINE_S | 25 | — | R1915: 23→25. OK max=26.2s > 25 (barely). | **否决**: 已有数据验证, 维持 |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 15 | — | R1802: 17→15. OK p99 TTFB=10.8s << 15s. | **否决**: 已有数据验证, 维持 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | 0 | 0=floor. | **否决**: floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | 0 | 0=floor. | **否决**: floor |
| NVU_CONNECT_RESERVE_S | 0 | 0 | 0=floor. | **否决**: floor |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | 0.0 | R982: 0.05. | **否决**: 已达安全边界 |

**NOP判定**: 与 R1960/R1961/R1962 一致 — 近零 post-deploy 流量 + 5 zombie 全部 NVCF 级 + 22 ATE 全 peer-fb 救援成功 + 全部参数 floor/optimal。R1959 的 BIG_INPUT_COOLDOWN=86400 改动需等待下次流量窗口才能评估效果。任何改动都是无数据支撑的猜测。

**铁律**: 只改HM1不改HM2

## 参数变更
无。NOP 回合。

## 验证
- ✅ docker ps → nv_gw Up 41 minutes (healthy)
- ✅ docker exec nv_gw env → all params confirmed (no drift)
- ✅ docker logs nv_gw --tail 100 → 1 zombie event, no other error/warn
- ✅ DB 6h: 41/36 OK (87.8% SR), 5 zombie all NVCF-level, 0 config-fixable errors
- ✅ Post-R1961: near-zero traffic (2 req), zero config-fixable errors
- ✅ 22 phantom ATE all peer-fb rescued (100% rescue success)
- ✅ Health: {"status": "ok", "proxy_role": "passthrough"}
## ⏳ 轮到HM1优化HM2
