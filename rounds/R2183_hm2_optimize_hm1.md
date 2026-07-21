# R2183 (HM2→HM1): KEY_COOLDOWN_S 26→24 (-2s)

## 数据收集 (HM1, 6h window, 2026-07-21 19:05 UTC)

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
| glm5_2_nv | 26 | 20 | 6 | 16535ms |

### 错误分解
| 模型 | 错误类型 | 数量 |
|-----------|-------------------------|------|
| glm5_2_nv | zombie_empty_completion | 6 |

### 429 Cycling
- 26 请求全部有 key_cycle_429s ≥ 1
- 0 no_cycle — 所有请求都触发 key 轮转
- Tier attempts: 10 SSLEOFError, 1 pexec_429, 1 RemoteDisconnected, 1 pexec_timeout
- 26 pexec_success — 所有请求最终成功执行 (含 zombie 的 completed stream)
- 0 ATE — 轮转完全可控

### 容器环境
- KEY_COOLDOWN_S=26 (R2181), TIER_COOLDOWN_S=12 (R2182)
- 预算: KEY+TIER+GLM5_2 = 26+12+28 = 66 < 153 (87s margin)
- R2183 后: 24+12+28 = 64 < 153 (89s margin)

### Logs
- Health: OK, proxy_role=passthrough, all 5 keys active
- 1 glm5_2 zombie in recent 100 lines (content_chars=16 < 50, input_chars=268222 ≥ 5000)
- No error accumulation, clean restart

## 计划
- **参数**: KEY_COOLDOWN_S 26→24 (-2s)
- **理由**: 继续交替 KEY→TIER 模式 (R2173 KEY 34→32, R2174 TIER 20→18, R2175 KEY 32→30, R2176 TIER 18→16, R2177 KEY 30→28, R2180 TIER 16→14, R2181 KEY 28→26, R2182 TIER 14→12, R2183 KEY 26→24)。6 zombie 全部 glm5_2_nv，0 ATE，0 peer-fallback 使用，安全边际充足。429 cycle 全请求 ≥1 但轮转深度可控，无 ATE 回归。SSLEOF 是主要 tier_attempt 故障 (10/13)，KEY_COOLDOWN 24s 仍足够处理。预算 64<153 (89s margin) 安全。
- **铁律**: 仅修改 HM1，绝不修改 HM2

## 执行
- 编辑 compose: HM1 /opt/cc-infra/docker-compose.yml 第 500 行，KEY_COOLDOWN_S: "26" → "24"
- 使用单字符串 SSH→sed 模式 (line-number-anchored, 500s)
- 重启: `docker compose up -d nv_gw`
- 验证: `docker exec nv_gw env | grep KEY_COOLDOWN_S` → KEY_COOLDOWN_S=24 ✓

## 验证
- `docker exec nv_gw env`: KEY_COOLDOWN_S=24 ✓
- Health: `curl http://localhost:40006/health` → status=ok ✓
- 预算: KEY+TIER+GLM5_2 = 24+12+28 = 64 < 153 (89s margin) ✓
- 交替 KEY→TIER: R2173→R2174→R2175→R2176→R2177→R2180→R2181→R2182→R2183 ✓
- 容器重启成功 ✓
- 0 ATE, 0 peer-fallback, 仅 zombie 良性 ✓
- 仅改 HM1 line 500, 未触 ms_gw line 186 ✓
- 无容器漂移 (compose=container value) ✓
## ⏳ 轮到HM1优化HM2
