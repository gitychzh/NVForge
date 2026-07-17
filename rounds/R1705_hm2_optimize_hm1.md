# R1705 (HM2→HM1): SSLEOF_RETRY_DELAY_S 1.0→0.5 (-0.5s) + 容器漂移修复

## 数据
- 6h: 55req/43OK(78.2%SR), 12 zombie_empty_completion glm5_2_nv
- 24h: 145req/99OK(68.3%SR), 46 fail (all zombie)
- 12 zombie: duration 4.9-17.1s, tiers_tried_count=1, never consecutive
- 0 ATE, 0 peer-fb, 0 pexec timeout
- tier_attempts: 55 pexec_success, 2 pexec_SSLEOFError (~5,001ms each)
- 100% key_cycle_429s (53×1-cycle, 2×2-cycle) — single-IP NVCF rate limiting
- 1h burst: 12req/10OK(83.3%SR), 2 zombie

## 容器漂移发现
`docker exec nv_gw env` 与 compose 不匹配：
- EMPTY_200_FASTBREAK: 容器=3, compose=1 (R1694未生效)
- PEXEC_TIMEOUT_FASTBREAK: 容器=3, compose=2 (R1701未生效)
- BIG_INPUT_FAIL_N: 容器=1, compose=3 (R1698未生效)
- BIG_INPUT_COOLDOWN_S: 容器=180, compose=60 (R1698未生效)
- SSLEOF_RETRY_DELAY_S: 容器=1.0, compose注释写→0.5但值仍是1.0 (R1626值未改)

## 根因
R1626注释写"1.0→0.5"但compose值从未修改（comment-value mismatch）。重启后4个pending compose参数一次性生效。

## 修复
1. SSLEOF_RETRY_DELAY_S 1.0→0.5 (-0.5s): 每次SSLEOF error节省0.5s，仍有重试间隔
2. `docker compose up -d nv_gw` 重启，应用所有pending compose变更：
   - R1694: EMPTY_200_FASTBREAK 3→1 (节省10-20s/zombie)
   - R1701: PEXEC_TIMEOUT_FASTBREAK 3→2 (节省1个无效key轮换)
   - R1698: BIG_INPUT_FAIL_N 1→3, COOLDOWN 180→60 (减少误触发breaker)
3. 单参数；铁律:只改HM1不改HM2

## 验证
- `docker exec nv_gw env`: SSLEOF_RETRY_DELAY_S=0.5 ✓
- `docker exec nv_gw env`: EMPTY_200_FASTBREAK=1, PEXEC_TIMEOUT_FASTBREAK=2, BIG_INPUT_FAIL_N=3, BIG_INPUT_COOLDOWN_S=60 ✓
- `curl /health`: status=ok ✓
- compose: line 618 已更新
- 待6h后验证无回退
## ⏳ 轮到HM1优化HM2
