# R1482 (HM2→HM1): NOP — post-restart data insufficient (3 req, 8min)

## 决策: NOP (No-Operation)

R1480 变更（清空 `NVU_PEER_FB_SKIP_MODELS`，重新添加 `dsv4p_nv:dsv4p_ms`）部署后仅 8 分钟，仅 3 条 post-restart 请求。R1481 已 NOP，本轮同样无足够数据支撑优化。所有参数已在 floor/optimal 状态。

## 6h 数据 (post-restart + pre-restart 混合)

| 指标 | 值 |
|------|-----|
| 总请求 | 43 |
| 成功 | 21 (48.8%) |
| 失败 | 22 |
| 错误分布 | zombie_empty_completion: 16, all_tiers_exhausted: 7 |
| 按模型 | glm5_2_nv: 25/13 OK (52.0%), dsv4p_nv: 18/8 OK (44.4%) |
| ms_gw | 21/18 OK (85.7%) |
| tier_attempts | 0 (密钥池干净) |

## Post-restart 数据 (2026-07-15 16:58 UTC → now)

| 时间 | 模型 | 状态 | 延迟 | 错误 |
|------|------|------|------|------|
| 17:03:20 | glm5_2_nv | 200 | 7733ms | — |
| 17:03:28 | glm5_2_nv | 502 | 8345ms | zombie_empty_completion |
| 17:06:05 | dsv4p_nv | 200 | 42036ms | — |

- 3 请求 / 2 OK / 1 zombie
- No post-restart ATE
- No NV-MS-FB triggers (dsv4p_ms 未触发)
- No peer-fb triggers (零 dsv4p_nv ATE 触发 peer-fb)
- tier_chain 显示 `(no fallback, 3model)` — 符合 R832 设计预期（FALLBACK_GRAPH={}）

## HM1 当前配置

- `NVU_PEER_FB_SKIP_MODELS=` (空，所有模型启用 peer-fallback)
- `NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms`
- `NVU_TIER_BUDGET_DSV4P_NV=66`
- `NVU_TIER_BUDGET_GLM5_2_NV=96`
- `NVU_TIER_BUDGET_MINIMAX_M3_NV=100`
- `TIER_TIMEOUT_BUDGET_S=205`
- `UPSTREAM_TIMEOUT=66`
- `NVU_EMPTY_200_FASTBREAK=2`
- `NVU_PEXEC_TIMEOUT_FASTBREAK=1`
- `NVU_INTEGRATE_TIMEOUT_FASTBREAK=1`
- `TIER_COOLDOWN_S=15`
- `KEY_COOLDOWN_S=25`
- `NVU_FALLBACK_HEALTH_THRESHOLD=0.05`
- `NVU_MS_GW_FALLBACK_TIMEOUT=120`
- `NVU_PEER_FALLBACK_TIMEOUT=66`
- `NVU_PEER_FALLBACK_ENABLED=1`
- `NVU_SSLEOF_RETRY_DELAY_S=1.0`
- Compose MD5: `089a818e37299c1632ce56e44b326090`

## Zombie 分析 (16 条, NVCF content-filter, 不可修)

- dsv4p_nv: 4 条 zombie_empty_completion, avg 43,191ms
- glm5_2_nv: 12 条 zombie_empty_completion, avg 11,426ms
- 全部 pre-restart。NVCF content-filter 主动返回空内容 → 网关正确检测 zombie 并快速中止 → 触发 openclaw fallback
- 不可配置参数修复（R1107 确认: code-level feature, faster abort 优于旧 96s 超时）

## ATE 分析 (7 条, 全部 pre-restart)

- 6 条 `all_tiers_exhausted`, 1 条在 recent 10 中显示 status=200 但 error_type=all_tiers_exhausted
- 全部 pre-restart。R1480 变更旨在通过 peer-fb + ms_gw dsv4p_ms 减少 ATE
- Post-restart 零 ATE → 数据不足，无法验证 R1480 效果

## 评判

- NOP 是唯一正确决策。3 条 post-restart 请求无法支撑任何参数优化判断
- 所有参数已在 floor/optimal 状态（R1474-R1480 已验证）
- Zombie 是 NVCF content-filter 问题，不可配置修复
- R1480 变更（peer-fb + ms_gw dsv4p_ms）需要更多数据验证
- 铁律: 只改HM1不改HM2 ✅
## ⏳ 轮到HM1优化HM2
