# R2174 (HM2→HM1): TIER_COOLDOWN_S 20→18 (-2s)

## 数据收集 (HM1, 6h window)

### DB 摘要
| 指标 | 值 |
|--------|------|
| 总请求 | 30 |
| OK | 24 (80.0%) |
| 失败 | 6 |

### 按模型
| 模型 | 总数 | OK | 失败 | 平均延迟 |
|-----------|-----|-----|------|----------|
| glm5_2_nv | 27 | 24 | 3 | 24942ms |
| dsv4p_nv | 3 | 0 | 3 | 1861ms |

### 错误分解
| 模型 | 错误类型 | 数量 |
|-----------|-------------------------|------|
| dsv4p_nv | all_tiers_exhausted | 3 |
| glm5_2_nv | zombie_empty_completion | 3 |

### dsv4p ATE 详情 (全部预抢占)
- 3 ATE，全部 status=502，key_cycle_429s=0
- 3 个 ATE 均在 03:39-03:40 (5h 前)，近期无新 ATE
- tiers_tried_count=1, fallback_tiers_used={dsv4p_nv}
- 0 nv_tier_attempts 行 — 主 tier 预抢占，从未尝试密钥

### glm5_2_nv 状态
- 27 请求，24 OK，3 zombie (11.1% zombie rate)
- OK 平均延迟 24942ms
- Tier attempts: 27 pexec_success, 13 SSLEOF, 10 timeout, 6 429, 1 RemoteDisconnected
- Key cycling: 27/27 请求有 key_cycle_429s (12x1, 8x2, 4x4, 2x3, 1x7)
- 每请求需要 2-4 次密钥轮转才能找到非故障密钥

### 对端回退
- 6h 内 0 个对端回退事件

### 容器环境
- KEY_COOLDOWN_S=32 (R2173), TIER_COOLDOWN_S=20 (R2172)
- 预算：KEY+TIER+GLM5_2 = 32+20+28 = 82 < 153 (71s 余量)
- R2174 后：32+18+28 = 78 < 153 (75s 余量)

## 计划
- **参数**：TIER_COOLDOWN_S 20→18 (-2s)
- **理由**：交替 KEY→TIER 模式。R2173 是 KEY 轮次 (34→32)，本轮 R2174 是 TIER 轮次。glm5_2 每请求需要 2-4 次密钥轮转，SSLEOF 是主要故障模式 (13/57 tier attempts)。缩短 TIER_COOLDOWN 让故障密钥更快恢复可用，减少后续请求的轮转深度。dsv4p ATE 均为 5h 前预抢占 (0 tier_attempts)，非 TIER_COOLDOWN 可修。预算安全 (75s 余量)。
- **铁律**：仅修改 HM1，绝不修改 HM2

## 执行
- 编辑 compose：HM1 /opt/cc-infra/docker-compose.yml 第 506 行，TIER_COOLDOWN_S: "20" → "18"
- 重启：`docker compose -f docker-compose.yml stop nv_gw && docker compose -f docker-compose.yml up -d nv_gw`
- 验证：`docker exec nv_gw env | grep TIER_COOLDOWN_S` → TIER_COOLDOWN_S=18 ✓

## 验证
- `docker exec nv_gw env`：TIER_COOLDOWN_S=18 ✓
- 预算：KEY+TIER+GLM5_2 = 32+18+28 = 78 < 153 (75s 余量) ✓
- 交替 KEY→TIER 模式：R2173 KEY 轮次，R2174 TIER 轮次 ✓
- ms_gw 段 (line 185) 未修改 ✓
## ⏳ 轮到HM1优化HM2
