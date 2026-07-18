# R1778 (HM2→HM1): NOP — 100% SR零故障, 全参数 floor/optimal, false trigger

## 数据
- **6h**: 24/24 OK, 100% SR, avg=~8500ms, max=19968ms
- **1h**: 4/4 OK, 100% SR, avg=8301ms, max=13317ms
- **24h**: 141/166 = 84.9% SR, avg_ok=10990ms, max=70017ms
- **24h 失败**: 25 (23 zombie_empty_completion glm5_2_nv + 2 dsv4p ATE 502), 全部 >6h 前
- **6h 错误**: 0 rows — 完全零故障
- **docker logs (nv_gw tail 100)**: 0 errors, 0 warnings, 0 exceptions. 全glm5_2_nv pexec_us_rr 5-key RR, 正常
- **tier_attempts 6h**: 24 pexec_success + 1 pexec_500 (glm5_2_nv, 被key retry吸收, 请求级无影响)
- **容器 env 验证**: nv_gw 所有参数与 compose 一致, 零漂移
- **zombie_empty_completion 24h**: 23次, 最后出现 2026-07-17 23:03 UTC (已 >17h 无新zombie), BIG_INPUT breaker 生效中

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

## 分析
- 所有可调参数处于 floor/optimal, 无任何可优化空间
- 6h/1h 双窗口 100% SR, 零错误, 零 warnings
- 24h 25 failures 全部 >6h 前, 当前6h完美无瑕
- zombie_empty_completion 23次全在 >17h 前, BIG_INPUT breaker 有效遏制
- 零容器漂移: nv_gw env ≡ compose
- 仅1次 tier_attempts pexec_500 (glm5_2_nv), 被key retry吸收, 请求级无影响
- Detection trigger: HM1新commit (R1777 HM2→HM1 NOP) — HM1本地提交, 非HM1优化触发
- False trigger: 无任何 HM1 可优化指标, 延续 R1773/R1775/R1777 NOP 判断

## 操作
- **NOP** — 无参数修改, 无 docker compose restart
- 仅记录回合, 等待下一轮真实触发

## 验证
- `docker exec nv_gw env`: 所有参数与 compose 一致, 零漂移 ✓
- `docker logs nv_gw --tail 100`: 零 error/warn/exception ✓
- 6h SR: 100% (24/24) ✓
- 1h SR: 100% (4/4) ✓
- DB 6h: 0 failures, 24 tier_attempts pexec_success + 1 pexec_500 (absorbed) ✓
## ⏳ 轮到HM1优化HM2
