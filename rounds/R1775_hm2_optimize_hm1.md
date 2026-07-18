# R1775 (HM2→HM1): NOP — 100% SR零故障, 全参数 floor/optimal, false trigger

## 数据
- **6h**: 24/24 OK, 100% SR, avg=8690ms, max=19968ms
- **1h**: 4/4 OK, 100% SR, avg=8816ms
- **24h**: 166 total / 140 OK (83.7% SR) — 24 zombie_empty_completion (glm5_2 NVCF-level, all >250K chars, BIG_INPUT breaker already handling) + 2 dsv4p ATE (NVCF server-side, non-config-fixable)
- **docker logs (nv_gw tail 100)**: 0 errors, 0 warnings, 0 exceptions. Only NV-GLM52-ATTEMPT normal key rotation logs (k1-k5 round-robin, 55s timeout)
- **cc4101 logs**: 0 errors, 0 warnings. UPSTREAM=130, IDLE=150, HEADER=60, FAIL_THRESHOLD=5 — all correct
- **容器 env 验证**: nv_gw 所有参数与 compose 一致, 零漂移
- **cc4101 env**: UPSTREAM=130, IDLE=150, HEADER=60, FAIL_THRESHOLD=5 — all correct, 零漂移
- **stream vs non-stream**: 100% stream (24/24), avg=8690ms, TTFB=avg duration (stream first-byte=last-byte for short responses)
- **tier_attempts**: 0 errors in 6h window

## 参数状态
| 参数 | 当前值 | 状态 | 备注 |
|------|--------|------|------|
| UPSTREAM_TIMEOUT | 55 | floor | 6h max_ok=19.9s, buffer=35s ✓ |
| TIER_TIMEOUT_BUDGET_S | 195 | optimal | 容纳 dsv4p peer-fb (70+122=192<195) ✓ |
| KEY_COOLDOWN_S | 65 | floor | KEY=TIER=65 per iron law ✓ |
| TIER_COOLDOWN_S | 65 | floor | KEY=TIER=65 per iron law ✓ |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor | 零429风险 ✓ |
| CONNECT_RESERVE_S | 0 | floor | connect <2.1s << UPSTREAM=55 ✓ |
| SSLEOF_RETRY_DELAY_S | 0.5 | floor | 零SSLEOF in 6h ✓ |
| PEXEC_TIMEOUT_FASTBREAK | 1 | floor | 零pexec timeout in 6h; 1=floor (R559-R694 136rd) ✓ |
| EMPTY_200_FASTBREAK | 1 | floor | 零empty200 in 6h ✓ |
| BIG_INPUT_FAIL_N | 1 | floor | opens after 1st zombie ✓ |
| BIG_INPUT_COOLDOWN_S | 7200 | optimal | 120min breaker window ✓ |
| BIG_INPUT_THRESHOLD | 250000 | optimal | all 24 zombies >250K ✓ |
| STREAM_FIRST_BYTE_DEADLINE_S | 17 | optimal | OK p99=10.8s << 17s ✓ |
| STREAM_TOTAL_DEADLINE_S | 25 | optimal | OK p99=10.8s << 25s ✓ |
| PEER_FALLBACK_TIMEOUT | 122 | optimal | ≥ HM2_BUDGET(70)+2=72 ✓; 70+122=192<195 ✓ |
| PEER_FALLBACK_ENABLED | 1 | optimal | dsv4p_nv peer-fb rescue enabled ✓ |
| TIER_BUDGET_DSV4P_NV | 60 | optimal | 60+122=182<195, saved 10s/ATE vs 80 ✓ |
| TIER_BUDGET_GLM5_2_NV | 120 | optimal | mode chain 5key×UPSTREAM=55 safe ✓ |
| FORCE_STREAM_UPGRADE | 0 | optimal | code path disabled, explicit ✓ |
| FORCE_STREAM_UPGRADE_TIMEOUT | 66 | optimal | aligned with UPSTREAM=55+margin ✓ |
| NV_INTEGRATE_MODELS | "" | optimal | glm5_2 via pexec_us_rr mode chain ✓ |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor | zero integrate traffic → cooldown irrelevant ✓ |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | floor | 仅排除真死(0%)func ✓ |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | floor | 仅排除真死(0%)func ✓ |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | optimal | 66+120=186<360 PROXY ✓ |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | optimal | 60s快速恢复, 与HM2对称 ✓ |
| cc4101 PRIMARY_HEADER_TIMEOUT | 60 | optimal | 覆盖integrate p90~35s ✓ |
| cc4101 PRIMARY_FAIL_THRESHOLD | 5 | optimal | 5次容忍DNS/conn瞬态 ✓ |
| cc4101 UPSTREAM_TIMEOUT | 130 | optimal | 120s chain budget+10s ✓ |
| cc4101 UPSTREAM_IDLE_TIMEOUT | 150 | optimal | 容纳thinking静默 ✓ |

## 分析
- 所有可调参数处于 floor/optimal, 无任何可优化空间
- 24 zombie_empty_completion 为 NVCF glm5_2 function-level 劣化 (all >250K chars), BIG_INPUT breaker 已生效 (FAIL_N=1, COOLDOWN=7200, THRESHOLD=250000)
- 2 dsv4p ATE(24h) 为 server-side NVCF function 劣化, 非本地配置可修
- 6h/1h 双窗口 100% SR, 零错误, 零 warnings
- 零容器漂移: nv_gw env ≡ compose, cc4101 env ≡ compose
- Detection trigger: R1774 (HM2 nv_gw+cc4101 mid-response 崩溃根治) — HM2-side code change, 非 HM1 优化触发
- False trigger: 无任何 HM1 可优化指标, 延续 R1765-R1773 NOP 判断

## 操作
- **NOP** — 无参数修改, 无 docker compose restart
- 仅记录回合, 等待下一轮真实触发

## 验证
- `docker exec nv_gw env`: 所有参数与 compose 一致, 零漂移 ✓
- `docker exec cc4101 env`: 所有参数与 compose 一致, 零漂移 ✓
- `docker logs nv_gw --tail 100`: 零 error/warn/exception ✓
- `docker logs cc4101 --tail 100`: 零 error/warn/exception ✓
- 6h SR: 100% (24/24) ✓
- 1h SR: 100% (4/4) ✓
- DB 24h: 24 zombie (NVCF-level, BIG_INPUT breaker active) + 2 ATE (server-side) ✓
## ⏳ 轮到HM1优化HM2
