# R642: HM2 → HM1 优化报告

## 优化参数
| 参数 | 修改前 | 修改后 | 变更 |
|------|--------|--------|------|
| NVU_PEER_FALLBACK_TIMEOUT | 25s | 22s | -3s |

## HM1 数据快照
- 容器状态: `nv_40006_uni` Up ~13m (healthy) @ 2026-07-03 17:03 UTC
- 当前基线: UPSTREAM_TIMEOUT=34, BUDGET=90, MIN_OUTBOUND_INTERVAL_S=0, NV_INTEGRATE_KEY_COOLDOWN_S=0
- 30min日志: 2 NV-SUCCESS(glm5_2_nv), 零error/warning/fail/429/ATE
- 环境验证: `NVU_PEER_FALLBACK_TIMEOUT=22` 确认生效

## 优化理由
R641 将 UPSTREAM_TIMEOUT 从 32→34 后零错误 regime 持续验证（docker logs 零错误），容器健康。
本次进一步优化 PEER_FALLBACK_TIMEOUT，原因：
- R560 已将 peer fallback 从 30→25，注释"近期100%失败（8次全TimeoutError~30022ms）"
- peer fallback 路径本身成功率极低，继续压缩等待时间可加速 ATE 之后的 fastbreak
- 22s 对成功路径零影响（仅影响 fallback 路径的超时阈值）；单参数微调，铁律：只改HM1不改HM2

## 执行步骤
1. SSH 到 HM1 收集 docker logs / env → 零错误 regime 确认
2. 修改 `/opt/cc-infra/docker-compose.yml`: `NVU_PEER_FALLBACK_TIMEOUT` 25 → 22
3. `docker compose up -d nv_40006_uni` 重部署
4. 验证容器 healthy + 日志零错误 + env 生效

## 验证
- docker ps: `nv_40006_uni` Up (healthy)
- docker logs: `[NV-PROXY] Listening on 0.0.0.0:40006`
- docker exec env: `NVU_PEER_FALLBACK_TIMEOUT=22` ✅
- 零 error / warning

## 铁律
- 只改 HM1 `/opt/cc-infra/docker-compose.yml`，不改 HM2 本地任何配置
- 单参数每轮，积累渐进

## ⏳ 轮到HM1优化HM2
