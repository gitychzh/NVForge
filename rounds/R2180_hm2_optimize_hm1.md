# R2180 (HM2→HM1): TIER_COOLDOWN_S 16→14 (-2s)

## 数据收集 (HM1, 6h window, 2026-07-21 18:20 UTC)

### DB 摘要
| 指标 | 值 |
|--------|------|
| 总请求 | 26 |
| OK | 22 (84.6%) |
| 失败 | 4 |
| ATE | 0 |
| Peer-fallback | 0 |

### 按模型
| 模型 | 总数 | OK | 失败 | 平均延迟 |
|-----------|-----|-----|------|----------|
| glm5_2_nv | 26 | 22 | 4 | 15203ms |

### 错误分解
| 模型 | 错误类型 | 数量 |
|-----------|-------------------------|------|
| glm5_2_nv | zombie_empty_completion | 4 |

### 429 Cycling
- 26 请求全部有 key_cycle_429s ≥ 1 (cycle 1=15, cycle 2+=11)
- 0 no_cycle — 所有请求都触发 key 轮转
- Tier attempts: 26 pexec_success, 11 SSLEOFError, 4 pexec_429, 1 RemoteDisconnected, 1 pexec_timeout
- 429 率低 (~9.3% of tier attempts), 0 ATE — 轮转可控

### 30min Recent
- 2 reqs, 2 OK (100%), avg 11976ms — clean

### 容器环境
- KEY_COOLDOWN_S=28 (R2177), TIER_COOLDOWN_S=16 (R2176)
- 预算: KEY+TIER+GLM5_2 = 28+16+28 = 72 < 153 (81s margin)
- R2180 后: 28+14+28 = 70 < 153 (83s margin)

### Logs
- Health: OK, proxy_role=passthrough, all 5 keys active
- No error accumulation, clean restart

## 计划
- **参数**: TIER_COOLDOWN_S 16→14 (-2s)
- **理由**: 继续交替 KEY→TIER 模式 (R2173 KEY 34→32, R2174 TIER 20→18, R2175 KEY 32→30, R2176 TIER 18→16, R2177 KEY 30→28, R2180 TIER 16→14)。4 zombie 全部 glm5_2_nv，0 ATE，0 peer-fallback 使用，安全边际充足。429 cycle 全请求 ≥1 但轮转深度可控 (cycle 1=15/26, cycle 2+=11/26)，无 ATE 回归。SSLEOF 是主要 tier_attempt 故障 (11/43)，TIER_COOLDOWN 14s 仍足够处理。预算 70<153 (83s margin) 安全。
- **铁律**: 仅修改 HM1，绝不修改 HM2

## 执行
- 编辑 compose: HM1 /opt/cc-infra/docker-compose.yml 第 506 行，TIER_COOLDOWN_S: "16" → "14"
- 重启: `docker compose -f /opt/cc-infra/docker-compose.yml stop nv_gw && docker compose -f /opt/cc-infra/docker-compose.yml up -d nv_gw`
- 验证: `docker exec nv_gw env | grep TIER_COOLDOWN_S` → TIER_COOLDOWN_S=14 ✓

## 验证
- `docker exec nv_gw env`: TIER_COOLDOWN_S=14 ✓
- Health: `curl http://localhost:40006/health` → status=ok ✓
- 预算: KEY+TIER+GLM5_2 = 28+14+28 = 70 < 153 (83s margin) ✓
- 交替 KEY→TIER: R2173→R2174→R2175→R2176→R2177→R2180 ✓
- 容器重启成功 ✓
- 0 ATE, 0 peer-fallback, 仅 zombie 良性 ✓

## ⏳ 轮到HM1优化HM2