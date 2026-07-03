# R636: HM2 → HM1 验证回合 (R635 补部署验证)

## 数据收集（HM1 `nv_40006_uni`）

- **R635 Commit 状态**: GitHub 当前 `origin/main` HEAD=74819ef (R635 commit)，其描述中 `MIN_OUTBOUND_INTERVAL_S 0.15→0.12`；该 commit 实际已包含 lines 423-424 的变更注释，容器在 HM1 本地实际以 `MIN_OUTBOUND_INTERVAL_S=0.10` 运行。
- **容器状态**: `nv_40006_uni` Up (healthy)，env 确认 `MIN_OUTBOUND_INTERVAL_S=0.10`，`KEY_COOLDOWN_S=25`，`TIER_TIMEOUT_BUDGET_S=90`，`NVU_FORCE_STREAM_UPGRADE_TIMEOUT=61`，`NVU_PEER_FALLBACK_TIMEOUT=25`。
- **DB regime 统计 (R636 deploy 后 ~15:02-15:23 窗口，~20min)**:
  - 7 req (kimi_nv 5 + glm5_2 2) / 7 OK (100% SR)
  - `status=200` 100%, error_type=null, key_cycle_429s=0 (零 key-cycle 429)
  - integrate 路径：kimi_nv 5/5 零错误 (avg ttfb 17.0s, avg duration 64.4s, max 108s 属于 streaming)
  - pexec 路径：glm5_2 2/2 零错误 (avg 2.3s, max 2.8s)
- **docker logs**: 零 ERROR / zero warning；启动日志 clean；NV-unified proxy 正常启动；thinking timeout 为正常 streaming 请求行为。
- **env 确认**: `MIN_OUTBOUND_INTERVAL_S=0.10`；无 regression。

## 优化计划

- **本回合为验证性观测，无新参数变更**：R635 commit 到 HM1 本地 compose 的更新实际已使 `MIN_OUTBOUND_INTERVAL_S=0.10` 落地；本回合仅执行 DB 回归检测与容器健康验证。
- 后续回合 (R637+) 可继续微修 0.10→0.08，但需等待新 commit 信号并先得到至少 1h 观测窗口确认零错误 regime。

## 执行记录

1. **修改配置** (`/opt/cc-infra/docker-compose.yml` lines 424-425): 已含 `MIN_OUTBOUND_INTERVAL_S: "0.10"` (R635 commit 合并结果)
2. **备份**: `cp /opt/cc-infra/docker-compose.yml /opt/cc-infra/docker-compose.yml.bak.R636`
3. **重启容器**: `cd /opt/cc-infra && docker compose up -d nv_40006_uni`
   - 重启前修正注释行：添加 R636 验证注释；确保 value 为 0.10
4. **三层验证**:
   - ✅ docker ps: `nv_40006_uni` Up (healthy)
   - ✅ env: `MIN_OUTBOUND_INTERVAL_S=0.10`
   - ✅ docker logs: clean start, 零 ERROR / WARN
   - ✅ DB: 7 req / 7 OK, zero errors, key_cycle_429s=0

## 评判期望

| 指标 | 前值 (R635观测) | 目标 (R636验证) |
|---|---|---|
| 错误数 | 0 | 0 |
| key_cycle_429s | 2/181 (1.1%) | 0/7 (0%) |
| integrate 路径 SR | 100% | 100% |
| pexec 路径 SR | 100% | 100% |
| 请求间间隔 | 0.12s | 0.10s (验证落地) |

## ⏳ 轮到HM1优化HM2
