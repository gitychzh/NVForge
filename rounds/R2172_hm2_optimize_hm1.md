# R2172 (HM2→HM1): TIER_COOLDOWN_S 22→20 (-2s)

## 数据收集 (HM1, 6h window)

### DB 摘要
| 指标 | 值 |
|--------|-------|
| 总请求 | 31 |
| OK | 25 (80.65%) |
| 失败 | 6 |
| 429 循环 | 28/31 (90.32%) — paired请求中key轮转，非NVCF 429 |

### 按模型
| 模型 | 总数 | OK | 失败 | 平均延迟 |
|-----------|--------|----|------|----------|
| glm5_2_nv | 28 | 25 | 3 | 22286ms |
| dsv4p_nv | 3 | 0 | 3 | 1861ms |

### 错误分解
| 模型 | 错误类型 | 子类别 | 数量 |
|-----------|----------------------------|-------------------|-------|
| dsv4p_nv | all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 3 |
| glm5_2_nv | zombie_empty_completion | | 3 |

### dsv4p ATE 详情 (全部预抢占)
- 3 个 ATE，全部 status=502，tiers_tried_count=1，fallback_tiers_used={dsv4p_nv}
- nv_tier_attempts 中 0 行 — 主 tier 预抢占（从未尝试密钥）
- 持续时间：1114ms、2087ms、2382ms（预抢占检查时间，非密钥时间）
- key_cycle_429s=0 — 实际未尝试密钥，未触发 429

### glm5_2 僵尸详情
- 3 个僵尸，平均延迟 10611ms，key_cycle_429s=2（两个密钥均返回僵尸）
- OK 请求：25，平均延迟 22286ms（高延迟来自配对的 glm5_2 请求 + 密钥轮转）

### 对端回退
- 6 小时内 0 个对端回退事件 — ATE 被预抢占，从未达到 tier 耗尽

### 429 循环分析
- 28/31 请求中 key_cycle_429s>0，但这是配对请求中的密钥轮转，非 NVCF 429 风暴
- 配对请求（每 30 分钟一对）始终循环密钥，低流量模式符合预期

### 容器环境
- KEY_COOLDOWN_S=34 (R2171)，TIER_COOLDOWN_S=22 (R2169，本轮前)
- 预算：KEY+TIER+GLM5_2 = 34+22+28 = 84 < 153（69 秒余量）
- R2171 后：34+20+28 = 82 < 153（71 秒余量）

## 计划
- **参数**：TIER_COOLDOWN_S 22→20 (-2s)
- **理由**：交替 KEY→TIER 模式。R2171 是 KEY 轮次（36→34），本轮是 TIER 轮次。dsv4p ATE 预抢占（0 次 tier_attempts）表明 tier 被冷却或预算检查阻塞 — 缩短 TIER_COOLDOWN 降低 tier 级阻塞。Zombie 率 10.7%（3/28）在预期范围内。预算安全。
- **铁律**：仅修改 HM1，绝不修改 HM2

## 执行
- 编辑 compose：HM1 /opt/cc-infra/docker-compose.yml 第 506 行，使用 sed
- 重启：`docker compose stop nv_gw && docker compose up -d nv_gw`
- 验证：`docker exec nv_gw env | grep TIER_COOLDOWN_S` → TIER_COOLDOWN_S=20 ✓

## 验证
- `docker exec nv_gw env`：TIER_COOLDOWN_S=20 ✓
- 预算：KEY+TIER+GLM5_2 = 34+20+28 = 82 < 153（71 秒余量）✓
- 交替 KEY→TIER 模式：R2171 KEY 轮次，R2172 TIER 轮次 ✓
## ⏳ 轮到HM1优化HM2
