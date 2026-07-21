# R2173 (HM2→HM1): KEY_COOLDOWN_S 34→32 (-2s)

## 数据收集 (HM1, 6h window)

### DB 摘要
| 指标 | 值 |
|--------|------|
| 总请求 | 32 |
| OK | 27 (84.4%) |
| 失败 | 5 |

### 按模型
| 模型 | 总数 | OK | 失败 | 平均延迟 |
|-----------|-----|-----|------|----------|
| glm5_2_nv | 29 | 27 | 2 | 25608ms |
| dsv4p_nv | 3 | 0 | 3 | — |

### 错误分解
| 模型 | 错误类型 | 数量 |
|-----------|-------------------------|------|
| dsv4p_nv | all_tiers_exhausted | 3 |
| glm5_2_nv | zombie_empty_completion | 2 |

### dsv4p ATE 详情 (全部预抢占)
- 3 个 ATE，全部 status=502
- 0 行 nv_tier_attempts — 主 tier 预抢占（从未尝试密钥）
- key_cycle_429s=0 — 实际未触发 429，预抢占即拒绝

### glm5_2 状态
- 27 OK，2 zombie (6.9% zombie rate，从 R2172 的 10.7% 改善)
- OK 平均延迟 25608ms
- 日志显示 SSLEOF 频繁（每对 glm5_2 请求 k2→k3→k4→k5 轮转），5 密钥均有 SSLEOF

### 对端回退
- 6 小时内 0 个对端回退事件

### 容器环境
- KEY_COOLDOWN_S=34 (R2171)，TIER_COOLDOWN_S=20 (R2172)
- 预算：KEY+TIER+GLM5_2 = 34+20+28 = 82 < 153（71 秒余量）
- R2173 后：32+20+28 = 80 < 153（73 秒余量）

## 计划
- **参数**：KEY_COOLDOWN_S 34→32 (-2s)
- **理由**：交替 KEY→TIER 模式。R2172 是 TIER 轮次（22→20），本轮是 KEY 轮次。glm5_2 日志中 SSLEOF 频繁，每对请求需 2-3 次密钥轮转才能找到非 SSLEOF 密钥。缩短 KEY_COOLDOWN 降低故障密钥冷却时间，提高密钥池周转速度。dsv4p ATE 预抢占（0 次 tier_attempts）非 KEY_COOLDOWN 可修。Zombie 率 6.9%（2/29）较 R2172 改善。预算安全。
- **铁律**：仅修改 HM1，绝不修改 HM2

## 执行
- 编辑 compose：HM1 /opt/cc-infra/docker-compose.yml 第 500 行，KEY_COOLDOWN_S: "34" → "32"
- 重启：`docker compose -f docker-compose.yml stop nv_gw && docker compose -f docker-compose.yml up -d nv_gw`
- 验证：`docker exec nv_gw env | grep KEY_COOLDOWN_S` → KEY_COOLDOWN_S=32 ✓

## 验证
- `docker exec nv_gw env`：KEY_COOLDOWN_S=32 ✓
- 预算：KEY+TIER+GLM5_2 = 32+20+28 = 80 < 153（73 秒余量）✓
- 交替 KEY→TIER 模式：R2172 TIER 轮次，R2173 KEY 轮次 ✓
## ⏳ 轮到HM1优化HM2
