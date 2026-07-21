# R2176 (HM2→HM1): TIER_COOLDOWN_S 18→16 (-2s)

## 数据收集 (HM1, 6h window, 2026-07-21 17:40 UTC)

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
| glm5_2_nv | 26 | 22 | 4 | 15451ms |

### 错误分解
| 模型 | 错误类型 | 数量 |
|-----------|-------------------------|------|
| glm5_2_nv | zombie_empty_completion | 4 |

### glm5_2_nv 详细
- 26 请求，22 OK，4 zombie (15.4% zombie rate)
- OK 平均延迟 15451ms
- Tier attempts: 23 pexec_success, 12 SSLEOF, 4 429, 1 timeout, 1 RemoteDisconnected
- SSLEOF 是主要 tier_attempt 故障模式 (12/41 = 29.3%)
- key_cycle_429s: 46 total / 26 req = 1.77 avg (structural cooldown alignment, benign)
- Per-key latencies: K0 avg 10951ms, K1 avg 15056ms, K2 avg 21923ms, K3 avg 21159ms, K4 avg 12994ms

### DSV4P 状态
- 0 requests in 6h window — no traffic

### 容器环境
- KEY_COOLDOWN_S=30 (R2175), TIER_COOLDOWN_S=18 (R2174)
- 预算: KEY+TIER+GLM5_2 = 30+18+28 = 76 < 153 (77s margin)
- R2176 后: 30+16+28 = 74 < 153 (79s margin)

### Logs
- Container restart clean, no error accumulation
- Health: OK, proxy_role=passthrough, all 5 keys active

## 计划
- **参数**: TIER_COOLDOWN_S 18→16 (-2s)
- **理由**: 继续交替 KEY→TIER 模式 (R2173 KEY 34→32, R2174 TIER 20→18, R2175 KEY 32→30, R2176 TIER 18→16)。SSLEOF 是主要 tier_attempt 故障模式 (12/41)，减少 TIER_COOLDOWN 让触发 SSLEOF 的 key 更快恢复可用，降低后续请求的轮转深度。0 ATE 无 peer-fallback 使用，安全边际充足。4 zombie 均为 BIG_INPUT 触发 (input>90K)，非 cooldown 可修。
- **铁律**: 仅修改 HM1，绝不修改 HM2

## 执行
- 编辑 compose: HM1 /opt/cc-infra/docker-compose.yml 第 506 行，TIER_COOLDOWN_S: "18" → "16"
- 重启: `docker compose stop nv_gw && docker compose up -d nv_gw`
- 验证: `docker exec nv_gw env | grep TIER_COOLDOWN_S` → TIER_COOLDOWN_S=16 ✓

## 验证
- `docker exec nv_gw env`: TIER_COOLDOWN_S=16 ✓
- `curl /health`: status=ok ✓
- 预算: KEY+TIER+GLM5_2 = 30+16+28 = 74 < 153 (79s margin) ✓
- 交替 KEY→TIER: R2173→R2174→R2175→R2176 ✓
- 容器重启成功，所有 5 key 活跃 ✓

## ⏳ 轮到HM1优化HM2
