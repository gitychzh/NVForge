# R1611: HM2→HM1 — NVU_TIER_BUDGET_DSV4P_NV 66→72 (+6s, EMPTY_200_FASTBREAK=2 unblock)

**决策**: BUDGET 66→72 (+6s). 66s=UPSTREAM 导致 EMPTY_200_FASTBREAK=2 被 budget 5s min 截断无法生效 (3.5s<5s). +6s→72 给 k1 62.5s 后留 9.5s 尝试 k2.

## 数据摘要

### 容器状态
- 重启时间: 2026-07-16T11:03 UTC (≈20min uptime, 被 R1610 或本轮重启)
- nv_gw: Up 9 seconds (healthy, 本轮重启)
- ms_gw: Up 28 hours (healthy)
- logs_db: Up 28 hours (healthy)
- compose md5: f81f01c6bc7cfe87f237390c19105e7d (与 R1610 不同 — R1610 compose md5 是 ba4f2871... 说明 HM1 compose 在 R1603 后已变更)

### 窗口数据 (nv_gw 重启后 ~6min)
| 指标 | 值 |
|------|-----|
| 总请求 | 4 |
| 成功 | 2 (50.0%) |
| 失败 | 2 (50.0%) |
| 失败原因 | 全部 dsv4p_nv ATE (peer-fb 全部救援) |

### 按模型
| 模型 | 请求 | OK | 失败 | SR | 备注 |
|------|------|-----|------|-----|------|
| glm5_2_nv | 2 | 2 | 0 | 100% | 1 zombie_empty_completion (NVCF content-filter) |
| dsv4p_nv | 2 | 0 | 2 | 0% | 2 ATE, peer-fb 2/2 100% SR |

### 关键发现: EMPTY_200_FASTBREAK=2 被 budget floor 截断
```
[11:07:09.5] [NV-EMPTY-200] k2 (dsv4p_nv) → 200 Content-Length:0 (stream)
[11:07:09.5] [NV-TIER-BUDGET] tier=dsv4p_nv budget 66.0s remaining 3.5s < 5s minimum, breaking
[11:07:09.5] [NV-TIER-FAIL] tier=dsv4p_nv all 5 keys failed: 429=0, empty200=1, timeout=0, other=0, elapsed=62487ms
```

- k1 耗时 62,487ms → budget 剩余 3.5s < 5s minimum → FASTBREAK=2 无法尝试第2 key
- 根本原因: NVU_TIER_BUDGET_DSV4P_NV=66 = UPSTREAM_TIMEOUT=66 → 零 headroom
- 第2个请求: k3 504 at 64,049ms, 剩余 2.0s < 5s → 同样无法尝试第2 key

### peer-fb 救援 (可靠)
- 请求1: dsv4p_nv ATE → peer-fb OK: status=200 bytes=1311 ttfb=4ms
- 请求2: dsv4p_nv ATE → peer-fb OK: status=200 bytes=14 ttfb=4617ms
- peer-fb 2/2 100% SR

### DB (code-level 问题)
- nv_requests: 0 rows (全部表为空)
- DB 连接正常 (logs_db Up 28h, pg 8191kB)
- nv_gw 日志无 DB 相关错误
- 代码级问题，不可配置修复

### ms_gw 健康
- 0 req in 6h window (低流量期)

### tier_attempts
- 0 rows (DB 为空)

## 参数变更

| 参数 | 旧值 | 新值 | Δ | 理由 |
|------|------|------|-----|------|
| NVU_TIER_BUDGET_DSV4P_NV | 66 | 72 | +6s | 66=UPSTREAM → 零 headroom → EMPTY_200_FASTBREAK=2 被 5s min 截断. +6s→72 给 k1 62.5s 后留 9.5s 尝试 k2. 72 < 205 BUDGET 安全 |

## 其他参数 (不变)
- UPSTREAM_TIMEOUT=66 (最优)
- NVU_PEXEC_TIMEOUT_FASTBREAK=1 (触底)
- NVU_EMPTY_200_FASTBREAK=2 (最优，现可生效)
- TIER_TIMEOUT_BUDGET_S=205 (最优)
- NVU_TIER_BUDGET_GLM5_2_NV=120 (最优)
- TIER_COOLDOWN_S=15 (触底)
- KEY_COOLDOWN_S=25 (触底)
- NVU_FALLBACK_HEALTH_THRESHOLD=0.05 (触底)
- NVU_PEER_FB_SKIP_MODELS= (最优)
- NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms (最优)
- NVU_MS_GW_FALLBACK_TIMEOUT=120 (最优)
- NVU_PEER_FALLBACK_TIMEOUT=66 (最优)
- NVU_CONNECT_RESERVE_S=0 (触底)
- NVU_SSLEOF_RETRY_DELAY_S=1.0 (触底)

## 铁律验证
- ✅ 只改HM1: 仅修改 HM1 compose + 重启 nv_gw
- ✅ 改前必有数据: 4 req 日志 + env + 容器状态
- ✅ 改后必有验证: 容器 Up 9s healthy, NVU_TIER_BUDGET_DSV4P_NV=72 env 确认
- ✅ 聚焦 nv_gw: 仅分析 nv_gw 链路
- ✅ 所有修改写入仓库: 本轮 commit
- ✅ 单参数少改多轮: 仅 +1 参数, +6s

## 验证
- 容器: nv_gw Up 9 seconds (healthy), ms_gw/logs_db 正常
- 环境: NVU_TIER_BUDGET_DSV4P_NV=72 ✅
- health: {"status": "ok"} ✅
- budget math: 72-62.5=9.5s ≥ 5s min → FASTBREAK=2 可生效
## ⏳ 轮到HM1优化HM2
