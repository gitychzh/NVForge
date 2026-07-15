# R1481 (HM2→HM1): NOP — container just restarted, zero post-restart data

## 决策: NOP (No-Operation)

R1480 变更刚部署（容器重启于 2026-07-15 16:58 UTC），6h DB 窗口全是 pre-restart 数据，零 post-restart 流量。无优化依据。

## 6h 数据 (pre-restart, 全窗口)

| 指标 | 值 |
|------|-----|
| 总请求 | 44 |
| 成功 | 21 (47.7%) |
| 失败 | 23 |
| 错误分布 | zombie_empty_completion: 16, all_tiers_exhausted: 7 |
| 按模型 | glm5_2_nv: 25/13 OK (52.0%), dsv4p_nv: 19/8 OK (42.1%) |
| ms_gw | 21/18 OK (85.7%) |

## R1480 变更 (HM1 当前配置)

- `NVU_PEER_FB_SKIP_MODELS=` (空，所有模型启用 peer-fallback)
- `NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms` (重新添加 dsv4p_nv:dsv4p_ms)
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
- `NVU_FORCE_STREAM_UPGRADE=0`
- `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66`
- `NVU_STREAM_FIRST_BYTE_DEADLINE_S=20`
- `NVU_STREAM_TOTAL_DEADLINE_S=42`
- `MIN_OUTBOUND_INTERVAL_S=0`
- `NVU_CONNECT_RESERVE_S=0`
- `NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006`
- Compose MD5: `43deeaa1a05a7dd41d788382c67f8291`

## 容器状态

- `nv_gw`: Up 3 minutes (healthy) — 刚重启
- `ms_gw`: Up 17 hours (healthy)
- `logs_db`: Up 17 hours (healthy)
- 无 tier_attempts (密钥池干净)
- 无 NV-ZOMBIE 日志
- 无 error/warn 日志

## R1480 验证

R1480 变更: 清空 `NVU_PEER_FB_SKIP_MODELS`（从 `glm5_2_nv,dsv4p_nv` 变为空），重新添加 `dsv4p_nv:dsv4p_ms` 到 MODELMAP。容器已重启并运行，env 确认变更生效。但零 post-restart 流量，无法验证效果。

## 预期

下一轮（R1482）应积累足够 post-restart 流量来验证 peer-fb + ms_gw dsv4p_ms 救援是否工作。如果 dsv4p_nv ATE 减少（peer-fb 到 HM2 的独立密钥池救援），则 R1480 变更生效。

## 评判

无数据，无变更。NOP 是唯一正确决策。
## ⏳ 轮到HM1优化HM2
