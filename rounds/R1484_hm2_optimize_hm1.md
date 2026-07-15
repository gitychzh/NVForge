# R1484: HM2→HM1 — NOP (container restart to apply R1474 compose fix)

## 数据收集
- **容器**: nv_gw Up 25min (restart: 2026-07-15 16:58:09 UTC)
- **compose md5**: 089a818e37299c1632ce56e44b326090
- **6h 全量**: 45req/22OK 48.9%SR, zombie 16, ATE 7
- **post-restart**: 4req/2OK 50.0%SR

## 失败分析
| 失败 | 模型 | 错误 | 根因 |
|------|------|------|------|
| 1 | glm5_2_nv | zombie_empty_completion | 代码级(content-filter, input 221K chars) |
| 1 | dsv4p_nv | all_tiers_exhausted | k1→504, cycle 5 keys, ms_gw TimeoutError 123s |

## 关键发现
- **容器 env 与 compose 不一致**: compose 已无 dsv4p_nv (R1474), 但容器 env 仍含 `dsv4p_nv:dsv4p_ms`
- dsv4p_nv ATE → ms_gw fallback → TimeoutError 123s (relay_started=True, all 10 variants exhausted)
- **peer-fb 被 ms_gw elif 阻塞** (R1474 pitfall)，从未触发
- Pre-restart 有 2/2 peer-fb 救援成功 (2595ms, 11887ms)
- ms_gw dsv4p_ms 6h: 0/0 (零成功)
- ms_gw glm5_2_ms: 18/21 OK (85.7%SR)

## 执行
- **操作**: 容器重启，使 R1474 compose 更改生效
- **变更**: 无参数变更 (compose 已被 R1474 修改，仅需重启)
- **结果**: MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms (无 dsv4p_nv)
- **预期**: dsv4p_nv ATE → 跳过 ms_gw → 直接 peer-fb (HM2 独立 key pool)
- **节省**: ~120s/ATE (ms_gw FALLBACK_TIMEOUT 被跳过)

## 当前参数 (全部 floor/optimal)
- UPSTREAM_TIMEOUT=66, TIER_COOLDOWN_S=15, KEY_COOLDOWN_S=25
- NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_EMPTY_200_FASTBREAK=2
- NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
- NVU_TIER_BUDGET_DSV4P_NV=66, NVU_TIER_BUDGET_GLM5_2_NV=96, NVU_TIER_BUDGET_MINIMAX_M3_NV=100
- NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms
- NVU_PEER_FB_SKIP_MODELS= (空)
- NVU_MS_GW_FALLBACK_TIMEOUT=120
- NVU_FALLBACK_HEALTH_THRESHOLD=0.05

铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
