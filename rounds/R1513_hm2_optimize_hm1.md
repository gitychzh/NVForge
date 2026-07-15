# R1513: HM2→HM1 — NOP (zero post-restart traffic, R1512 DNS fix untested)

## 诊断
- R1512 修复 host.docker.internal DNS 后容器重启 (06:33 UTC), 仅2条 post-restart 请求 (glm5_2_nv integrate OK)
- 6h 窗口: 71req/48OK/23fail = 67.6% SR — **全部为重启前旧数据, 无参考价值**
- 19 zombie_empty_completion (NVCF content-filter, 不可配置) — 全部在重启前
- 4 ATE (all_tiers_exhausted) — 全部在重启前: 2条 ProxyConnectionError (DNS fail, R1512 已修复), 2条 504/pexec timeout (BUDGET floor, 已 optimal)
- 2 tier_attempts: glm5_2_nv 429_integrate_rate_limit (transient, key-specific)
- ms_gw: 16/15 OK (93.8% SR, 1 client_disconnect on glm5_2 206s)
- DNS 验证: `getent hosts host.docker.internal` → 172.17.0.1 ✅
- RR counter: dsv4p=2514, glm5_2=289, kimi=83, minimax_m3=19, minimax_m3_nv=1

## 参数状态
- 所有参数 floor/optimal, 无需调整
- `NVU_TIER_BUDGET_DSV4P_NV=66` (UPSTREAM_TIMEOUT floor)
- `NVU_TIER_BUDGET_GLM5_2_NV=96` (integrate timeout 96s)
- `NVU_PEXEC_TIMEOUT_FASTBREAK=1` (function-level)
- `NVU_INTEGRATE_TIMEOUT_FASTBREAK=1` (function-level)
- `NVU_EMPTY_200_FASTBREAK=2` (key-specific, R1489 budget exhaustion known)
- `TIER_COOLDOWN_S=15` (R1103 revert)
- `TIER_TIMEOUT_BUDGET_S=205`
- `NVU_PEER_FB_SKIP_MODELS=` (空, peer-fb enabled)
- `NVU_MS_GW_FALLBACK_TIMEOUT=120`
- compose md5: 9fb97661 (R1512 未变)

## 决策: NOP
- 无有效 post-restart 流量, 无数据支撑任何参数调整
- 所有参数已 floor/optimal
- zombie=NVCF content-filter (不可配置, 无需响应)
- 等待流量积累验证 R1512 DNS 修复效果
## ⏳ 轮到HM1优化HM2
