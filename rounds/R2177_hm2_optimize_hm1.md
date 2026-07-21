# R2177 (HM2→HM1): KEY_COOLDOWN_S 30→28 (-2s)

## 数据收集 (HM1, 6h window, 2026-07-21 18:00 UTC)

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
| glm5_2_nv | 26 | 22 | 4 | 16456ms |

### 错误分解
| 模型 | 错误类型 | 数量 |
|-----------|-------------------------|------|
| glm5_2_nv | zombie_empty_completion | 4 |

### glm5_2_nv 详细
- 26 请求，22 OK，4 zombie (15.4% zombie rate)
- OK 平均延迟 16456ms，最大 46273ms
- 429 cycle 分布: cycle 1=14 reqs, cycle 2=8 reqs, cycle 4=4 reqs
- 0 tier fallback 到 dsv4p_nv — 所有请求都在 glm5_2_nv 上完成
- 0 peer-fallback 使用

### DSV4P 状态
- 0 requests in 6h window — no traffic

### 容器环境
- KEY_COOLDOWN_S=30 (R2175), TIER_COOLDOWN_S=16 (R2176)
- 预算: KEY+TIER+GLM5_2 = 30+16+28 = 74 < 153 (79s margin)
- R2177 后: 28+16+28 = 72 < 153 (81s margin)

### Logs
- Container restart clean, no error accumulation
- Health: OK, proxy_role=passthrough, all 5 keys active

## 计划
- **参数**: KEY_COOLDOWN_S 30→28 (-2s)
- **理由**: 继续交替 KEY→TIER 模式 (R2173 KEY 34→32, R2174 TIER 20→18, R2175 KEY 32→30, R2176 TIER 18→16, R2177 KEY 30→28)。4 zombie 全部 glm5_2_nv，0 ATE，0 peer-fallback 使用，安全边际充足。429 cycle 分布显示 key 轮转频繁 (cycle 1=14, cycle 2=8, cycle 4=4)，减少 KEY_COOLDOWN 让 key 更快恢复可用，降低后续请求的轮转深度。SSLEOF 是 R2176 主要 tier_attempt 故障模式 (12/41)，TIER_COOLDOWN 16s 已足够处理。预算 72<153 (81s margin) 安全。
- **铁律**: 仅修改 HM1，绝不修改 HM2

## 执行
- 编辑 compose: HM1 /opt/cc-infra/docker-compose.yml 第 500 行，KEY_COOLDOWN_S: "30" → "28"
- 重启: `docker compose -f /opt/cc-infra/docker-compose.yml stop nv_gw && docker compose -f /opt/cc-infra/docker-compose.yml up -d nv_gw`
- 验证: `docker exec nv_gw env | grep KEY_COOLDOWN_S` → KEY_COOLDOWN_S=28 ✓

## 验证
- `docker exec nv_gw env`: KEY_COOLDOWN_S=28 ✓
- 预算: KEY+TIER+GLM5_2 = 28+16+28 = 72 < 153 (81s margin) ✓
- 交替 KEY→TIER: R2173→R2174→R2175→R2176→R2177 ✓
- 容器重启成功 ✓

## ⏳ 轮到HM1优化HM2
