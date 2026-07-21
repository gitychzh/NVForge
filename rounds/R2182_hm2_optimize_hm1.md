# R2182 (HM2→HM1): TIER_COOLDOWN_S 14→12 (-2s)

## 数据收集 (HM1, 6h window, 2026-07-21 18:50 UTC)

### DB 摘要
| 指标 | 值 |
|--------|------|
| 总请求 | 26 |
| OK | 21 (80.8%) |
| 失败 | 5 |
| ATE | 0 |
| Peer-fallback | 0 |

### 按模型
| 模型 | 总数 | OK | 失败 | 平均延迟 |
|-----------|-----|-----|------|----------|
| glm5_2_nv | 26 | 21 | 5 | 15486ms |

### 错误分解
| 模型 | 错误类型 | 数量 |
|-----------|-------------------------|------|
| glm5_2_nv | zombie_empty_completion | 5 |

### 429 Cycling
- 26 请求全部有 key_cycle_429s ≥ 1 (cycle 1=15, cycle 2+=11)
- 0 no_cycle — 所有请求都触发 key 轮转
- Tier attempts: 17 pexec errors (11 SSLEOFError, 4 pexec_429, 1 RemoteDisconnected, 1 pexec_timeout)
- 429 率低, 0 ATE — 轮转可控

### 30min Recent
- 2 reqs, 1 OK, avg 10404ms — 1 zombie

### 容器环境
- KEY_COOLDOWN_S=26 (R2181), TIER_COOLDOWN_S=14 (R2180)
- 预算: KEY+TIER+GLM5_2 = 26+14+28 = 70 < 153 (83s margin)
- R2182 后: 26+12+28 = 66 < 153 (87s margin)

### Logs
- Health: OK, proxy_role=passthrough, all 5 keys active
- No error accumulation, clean restart

## 计划
- **参数**: TIER_COOLDOWN_S 14→12 (-2s)
- **理由**: 继续交替 KEY→TIER 模式 (R2173 KEY 34→32, R2174 TIER 20→18, R2175 KEY 32→30, R2176 TIER 18→16, R2177 KEY 30→28, R2180 TIER 16→14, R2181 KEY 28→26, R2182 TIER 14→12)。5 zombie 全部 glm5_2_nv，0 ATE，0 peer-fallback 使用，安全边际充足。429 cycle 全请求 ≥1 但轮转深度可控 (cycle 1=15/26, cycle 2+=11/26)，无 ATE 回归。SSLEOF 是主要 tier_attempt 故障 (11/17)，TIER_COOLDOWN 12s 仍足够处理（预算 66<153, 87s margin）。
- **铁律**: 仅修改 HM1，绝不修改 HM2

## 执行
- 编辑 compose: HM1 /opt/cc-infra/docker-compose.yml 第 506 行，TIER_COOLDOWN_S: "14" → "12"
- 使用单字符串 SSH→sed 模式 (line-number-anchored, 506s)
- 重启: `docker compose -f /opt/cc-infra/docker-compose.yml stop nv_gw && docker compose -f /opt/cc-infra/docker-compose.yml up -d nv_gw`
- 验证: `docker exec nv_gw env | grep TIER_COOLDOWN_S` → TIER_COOLDOWN_S=12 ✓

## 验证
- `docker exec nv_gw env`: TIER_COOLDOWN_S=12 ✓
- Health: `curl http://localhost:40006/health` → status=ok ✓
- 预算: KEY+TIER+GLM5_2 = 26+12+28 = 66 < 153 (87s margin) ✓
- 交替 KEY→TIER: R2173→R2174→R2175→R2176→R2177→R2180→R2181→R2182 ✓
- 容器重启成功 ✓
- 0 ATE, 0 peer-fallback, 仅 zombie 良性 ✓
- 仅改 HM1 line 506, 未触 ms_gw line 185 ✓
## ⏳ 轮到HM1优化HM2