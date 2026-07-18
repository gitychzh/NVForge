# R1777 (HM2→HM1): NOP — 100% SR零故障, 全参数 floor/optimal, false trigger

## 数据
- **6h**: 24/24 OK, 100% SR, avg=~8500ms, max=19968ms
- **30min**: 2/2 OK, 100% SR
- **24h**: 140/166 = 84.3% SR (26 failures, all >6h ago, 当前6h完美)
- **docker logs (nv_gw tail 100)**: 0 errors, 0 warnings, 0 exceptions. 全glm5_2_nv pexec_us_rr 5-key RR, 仅1次k4 KF→k5成功, 无影响
- **cc4101 logs**: 0 errors, 0 warnings
- **容器 env 验证**: nv_gw 所有参数与 compose 一致, 零漂移
- **cc4101 env**: UPSTREAM=130, IDLE=150, HEADER=60, FAIL_THRESHOLD=5 — 全部 correct, 零漂移
- **tier_attempts**: 24 pexec_success + 1 pexec_500 (glm5_2_nv, 被key retry吸收, 请求级无影响)
- **6h 错误**: 0 rows — 完全零故障

## 参数状态
| 参数 | 当前值 | 状态 | 备注 |
|------|--------|------|------|
| UPSTREAM_TIMEOUT | 55 | floor | 6h max=19.9s, buffer=35s ✓ |
| TIER_TIMEOUT_BUDGET_S | 195 | optimal | 容纳 dsv4p peer-fb (70+122=192<195) ✓ |
| KEY_COOLDOWN_S | 65 | floor | KEY=TIER=65 per iron law ✓ |
| TIER_COOLDOWN_S | 65 | floor | KEY=TIER=65 per iron law ✓ |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor | 零429风险 ✓ |
| CONNECT_RESERVE_S | 0 | floor | connect <2.1s << UPSTREAM=55 ✓ |
| SSLEOF_RETRY_DELAY_S | 0.5 | floor | 零SSLEOF in 6h ✓ |
| PEXEC_TIMEOUT_FASTBREAK | 1 | floor | 零pexec timeout in 6h ✓ |
| EMPTY_200_FASTBREAK | 1 | floor | 零empty200 in 6h ✓ |
| BIG_INPUT_FAIL_N | 1 | floor | opens after 1st zombie ✓ |
| BIG_INPUT_COOLDOWN_S | 7200 | optimal | 120min breaker window ✓ |
| BIG_INPUT_THRESHOLD | 250000 | optimal | 无zombie in 6h ✓ |
| STREAM_FIRST_BYTE_DEADLINE_S | 17 | optimal | OK p99<17s ✓ |
| STREAM_TOTAL_DEADLINE_S | 25 | optimal | OK p99<25s ✓ |
| PEER_FALLBACK_TIMEOUT | 122 | optimal | ≥ HM2_BUDGET(70)+2=72 ✓; 70+122=192<195 ✓ |
| PEER_FALLBACK_ENABLED | 1 | optimal | dsv4p_nv peer-fb rescue enabled ✓ |
| TIER_BUDGET_DSV4P_NV | 60 | optimal | 60+122=182<195 ✓ |
| TIER_BUDGET_GLM5_2_NV | 120 | optimal | mode chain 5key×UPSTREAM=55 safe ✓ |
| FORCE_STREAM_UPGRADE | 0 | optimal | code path disabled ✓ |
| FORCE_STREAM_UPGRADE_TIMEOUT | 66 | optimal | aligned with UPSTREAM=55+margin ✓ |
| NV_INTEGRATE_MODELS | "" | optimal | glm5_2 via pexec_us_rr mode chain ✓ |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor | zero integrate traffic ✓ |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | floor | 仅排除真死(0%)func ✓ |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | floor | 仅排除真死(0%)func ✓ |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | optimal | 66+120=186<360 PROXY ✓ |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | optimal | 60s快速恢复 ✓ |
| cc4101 PRIMARY_HEADER_TIMEOUT | 60 | optimal | 覆盖integrate p90~35s ✓ |
| cc4101 PRIMARY_FAIL_THRESHOLD | 5 | optimal | 5次容忍DNS/conn瞬态 ✓ |
| cc4101 UPSTREAM_TIMEOUT | 130 | optimal | 120s chain budget+10s ✓ |
| cc4101 UPSTREAM_IDLE_TIMEOUT | 150 | optimal | 容纳thinking静默 ✓ |

## 分析
- 所有可调参数处于 floor/optimal, 无任何可优化空间
- 6h/30min 双窗口 100% SR, 零错误, 零 warnings
- 24h 26 failures 全部 >6h 前, 当前6h完美无瑕
- 零容器漂移: nv_gw env ≡ compose, cc4101 env ≡ compose
- 仅1次 tier_attempts pexec_500 (glm5_2_nv), 被key retry吸收, 请求级无影响
- Detection trigger: HM1新commit (R1776 HM2 cc2巡检轮) — HM1本地提交, 非HM1优化触发
- False trigger: 无任何 HM1 可优化指标, 延续 R1773/R1775 NOP 判断

## 操作
- **NOP** — 无参数修改, 无 docker compose restart
- 仅记录回合, 等待下一轮真实触发

## 验证
- `docker exec nv_gw env`: 所有参数与 compose 一致, 零漂移 ✓
- `docker exec cc4101 env`: 所有参数与 compose 一致, 零漂移 ✓
- `docker logs nv_gw --tail 100`: 零 error/warn/exception ✓
- `docker logs cc4101 --tail 50`: 零 error/warn/exception ✓
- 6h SR: 100% (24/24) ✓
- 30min SR: 100% (2/2) ✓
- DB 6h: 0 failures, 24 tier_attempts pexec_success + 1 pexec_500 (absorbed) ✓
## ⏳ 轮到HM1优化HM2
