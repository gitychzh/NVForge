# R1788: HM2→HM1 — NOP (post-deploy zero data)

## TL;DR
容器5分钟前刚重启(R1787部署: BUDGET 195→175, R1786: TIER_DSV4P 60→50)。零post-deployment数据, 改前必有数据铁律触发NOP。待下一轮积累数据后操作。

## 一、当前配置快照（R1787 部署后）

| # | 参数 | HM1 当前值 | 历史来源 |
|---|------|------------|----------|
| 1 | `UPSTREAM_TIMEOUT` | 55 | R1729 |
| 2 | `TIER_TIMEOUT_BUDGET_S` | 175 | R1787 |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 | R638 |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | env |
| 5 | `TIER_COOLDOWN_S` | 65 | R1740 |
| 6 | `NVU_PEER_FALLBACK_TIMEOUT` | 122 | R1744 |
| 7 | `NVU_CONNECT_RESERVE_S` | 0 | env |
| 8 | `NVU_SSLEOF_RETRY_DELAY_S` | 0.5 | env |
| 9 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 66 | R988 |
| 10 | `NVU_FORCE_STREAM_UPGRADE` | 0 | R692 |
| 11 | `NVU_EMPTY_200_FASTBREAK` | 1 | env |
| 12 | `NV_INTEGRATE_ENABLED` | (none) | env |
| 13 | `NV_INTEGRATE_MODELS` | "" | R1421 |
| 14 | `NV_INTEGRATE_KEY_COOLDOWN_S` | 0 | R631 |
| 15 | `KEY_COOLDOWN_S` | 65 | R1740 |

## 二、漂移检测（Pre-analysis）

### 2.1 Compose 文件
```
TIER_TIMEOUT_BUDGET_S: "175"
NVU_TIER_BUDGET_DSV4P_NV: "50"
NVU_PEER_FALLBACK_TIMEOUT: "122"
```

### 2.2 容器 env
```
TIER_TIMEOUT_BUDGET_S=175
NVU_TIER_BUDGET_DSV4P_NV=50
NVU_PEER_FALLBACK_TIMEOUT=122
```

### 2.3 容器启动时间
```
2026-07-18T10:50:27.447173278Z (≈5 min ago)
```

### 2.4 运行时日志
```
docker logs nv_gw --tail 100: 零 ERROR/WARN, 零 peer-fb, 零 429
NV-PROXY: Listening on 0.0.0.0:40006 (role=passthrough, default_tier=dsv4p_nv, fallback_chain=['kimi_nv', 'dsv4p_nv', 'glm5_2_nv'])
```

**结论：四源全部通过，零漂移。容器刚重启，无上线后数据。**

## 三、数据摘要（部署前窗口，旧配置 6h）

### 3.1 DB 6h 窗口
- **总请求**: 32 (31 OK + 1 502 fail) = 96.9% SR
- **glm5_2_nv**: 24/24 OK (100%), pexec_success, avg=8873ms, max=18918ms
- **dsv4p_nv**: 7 OK + 1 502 fail = 87.5% SR
  - 8 ATE 全 dsv4p: 7 phantom (status=200) + 1 real (status=502)
  - fallback_occurred=false, tiers_tried_count=1 (单 tier 无 fallback)
  - Old config: 70+125=195≥195 → peer-fb skipped (R1739 boundary equality)
- **key_cycle_429s**: 24/32 req 有 1次 429 (75%), 8/32 零 (25%)

### 3.2 Docker Logs
- 零 ERROR/WARN 输出
- 零 peer-fallback 触发
- 零 empty_200 / zombie

### 3.3 Tier Attempts
- glm5_2_nv: 24 pexec_success
- dsv4p_nv: 0 rows (tier_attempts 仅记录成功路径, ATE 无 tier attempt)

## 四、决策分析

| 参数 | 旧值 | 候选新值 | 数据支撑 | 决策 |
|------|------|---------|---------|------|
| `TIER_TIMEOUT_BUDGET_S` | 175 | — | 容器刚重启无post-deploy数据 | ❌ NOP |
| `NVU_TIER_BUDGET_DSV4P_NV` | 50 | — | 同上 | ❌ |
| `NVU_PEER_FALLBACK_TIMEOUT` | 122 | — | 同上 | ❌ |
| 其他所有参数 | — | — | 零post-deploy数据, 无决策依据 | ❌ |

**最终决策**：NOP。R1787 (BUDGET 195→175) + R1786 (TIER_DSV4P 60→50) 刚部署5分钟，零post-deployment数据。改前必有数据铁律要求等待下一轮积累数据后再判断。新配置预期效果: dsv4p peer-fb 应从 skipped (70+125=195≥195) 变为 enabled (50+122=172<175, 3s margin)。

## 五、执行记录

无执行。NOP 轮。

## 六、验证记录

| 指标 | 数值 | 状态 |
|------|------|------|
| 首试成功率 | N/A (零数据) | ⏳ |
| 429 / rate-limit | N/A | ⏳ |
| ERROR/WARN | 0 | ⏳ |
| peer fallback 触发 | 0 | ⏳ |
| 容器重启 | 5min ago (R1787) | ✅ |

## 七、结论

R1788 NOP。容器刚重启零post-deploy数据，改前必有数据铁律触发。等待下一轮积累dsv4p peer-fallback数据后判断peer-fb是否生效(BUDGET 175是否足够让 50+122=172<175 触发)，以及R1786 (TIER_DSV4P 60→50) 是否导致50s内过早断定key失败。

单参数少改多轮。铁律：只改 HM1 不改 HM2。

## ⏳ 轮到HM1优化HM2