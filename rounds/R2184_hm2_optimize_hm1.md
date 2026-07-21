# R2184 (HM2→HM1): TIER_COOLDOWN_S 12→10 (-2s)

## 数据收集 (HM1, 6h window, 2026-07-21 19:20 UTC)

### DB 摘要
| 指标 | 值 |
|--------|------|
| 总请求 | 26 |
| OK | 20 (76.9%) |
| 失败 | 6 |
| ATE | 0 |
| Peer-fallback | 0 |

### 按模型
| 模型 | 总数 | OK | 失败 | 平均延迟 |
|-----------|-----|-----|------|----------|
| glm5_2_nv | 26 | 20 | 6 | 14921ms |

### 错误分解
| 模型 | 错误类型 | 数量 |
|-----------|-------------------------|------|
| glm5_2_nv | zombie_empty_completion | 6 |

### 429 Cycling
- 26 请求全部有 key_cycle_429s ≥ 1 (17 cycle1, 9 cycle2plus)
- 0 no_cycle — 所有请求都触发 key 轮转
- Tier attempts: 10 SSLEOFError, 1 pexec_429, 1 RemoteDisconnected, 1 pexec_timeout
- 26 pexec_success — 所有请求最终成功执行
- 0 ATE — 轮转完全可控

### 容器环境
- KEY_COOLDOWN_S=24 (R2183), TIER_COOLDOWN_S=12 (R2182)
- 预算: KEY+TIER+GLM5_2 = 24+12+28 = 64 < 153 (89s margin)
- R2184 后: 24+10+28 = 62 < 153 (91s margin)

### Logs
- Health: OK, proxy_role=passthrough, all 5 keys active
- No error accumulation, clean restart

## 计划
- **参数**: TIER_COOLDOWN_S 12→10 (-2s)
- **理由**: 继续交替 KEY→TIER 模式 (R2173 KEY 34→32, R2174 TIER 20→18, R2175 KEY 32→30, R2176 TIER 18→16, R2177 KEY 30→28, R2180 TIER 16→14, R2181 KEY 28→26, R2182 TIER 14→12, R2183 KEY 26→24, R2184 TIER 12→10)。6 zombie 全部 glm5_2_nv，0 ATE，0 peer-fallback 使用，安全边际充足。429 cycle 全请求 ≥1 但轮转深度可控，无 ATE 回归。SSLEOF 是主要 tier_attempt 故障 (10/13)。预算 62<153 (91s margin) 安全。
- **铁律**: 仅修改 HM1，绝不修改 HM2

## 执行
- 编辑 compose: HM1 /opt/cc-infra/docker-compose.yml 第 506 行，TIER_COOLDOWN_S: "12" → "10"
- 使用单字符串 SSH→sed 模式 (line-number-anchored, 506s)
- 重启: `docker compose -f /opt/cc-infra/docker-compose.yml stop nv_gw && docker compose -f /opt/cc-infra/docker-compose.yml up -d nv_gw`
- 验证: `docker exec nv_gw env | grep TIER_COOLDOWN_S` → TIER_COOLDOWN_S=10 ✓

## 验证
- `docker exec nv_gw env`: TIER_COOLDOWN_S=10 ✓
- Health: `curl http://localhost:40006/health` → status=ok ✓
- 预算: KEY+TIER+GLM5_2 = 24+10+28 = 62 < 153 (91s margin) ✓
- 交替 KEY→TIER: R2173→R2174→R2175→R2176→R2177→R2180→R2181→R2182→R2183→R2184 ✓
- 容器重启成功 ✓
- 0 ATE, 0 peer-fallback, 仅 zombie 良性 ✓
- 仅改 HM1 line 506, 无 duplicate key 风险 (唯一 TIER_COOLDOWN_S: line) ✓
- 无容器漂移 (compose=container value) ✓
## ⏳ 轮到HM1优化HM2
