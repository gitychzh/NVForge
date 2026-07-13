# R1000: HM2→HM1 — 移除glm5_2_nv peer-fb跳过, 启用peer-fallback

## 1. 数据收集 (HM1, 重启后9min, R1245已部署)

### 6h 总体
| 指标 | 值 |
|------|-----|
| 总请求 | 144 |
| 成功(200) | 113 |
| 失败 | 31 |
| SR | **78.5%** |

### 6h 按模型
| 模型 | 请求 | 成功 | 失败 | SR | avg_dur |
|------|------|------|------|------|---------|
| glm5_2_nv | 136 | 109 | 27 | 80.1% | 39943ms |
| dsv4p_nv | 8 | 4 | 4 | 50.0% | 58451ms |

### 6h 错误分布
| 错误类型 | 数量 |
|----------|------|
| zombie_empty_completion | 17 |
| all_tiers_exhausted | 13 |
| NVStream_IncompleteRead | 1 |

### 6h nv_tier_attempts
- glm5_2_nv IntegrateTimeout × 6 (avg 91,331ms, max 93,529ms)

### 关键发现
1. **NVU_PEER_FB_SKIP_MODELS=glm5_2_nv** — 82.6%失败请求的模型没有peer-fallback路径
2. **ms_gw BrokenPipeError** — 0/21 OK, 无有效ms_gw恢复
3. 6h fallback_occurred 全部 false — glm5_2_nv ATE直接返回502, 没有二次救援

## 2. 优化决策

**变更**: `NVU_PEER_FB_SKIP_MODELS` glm5_2_nv → 空

**理由**:
- glm5_2_nv 6h 27/136=19.9%失败率, 错误=zombie_empty_completion+IntegrateTimeout
- peer-fb 跳过了最高失败率的模型 → ATE无恢复路径
- ms_gw BrokenPipeError(0/21 → 100%失败) → ms_gw路径不可靠
- NOP不是正确选择: 78.5% SR远低于目标, ATE无有效恢复是配置问题(非NVCF问题)
- 启用peer-fb: HM2独立key池给glm5_2_nv ATE请求二次机会
- 已验证: R1039曾将dsv4p_nv从skip移除并确认peer-fb路径有效

## 3. 执行

1. Python stdin pipe编辑 compose line 497: `NVU_PEER_FB_SKIP_MODELS: "glm5_2_nv"` → `NVU_PEER_FB_SKIP_MODELS: ""`
2. YAML lint: OK
3. `docker compose stop nv_gw && docker compose up -d nv_gw`: 容器重新创建, 启动成功
4. `docker exec nv_gw env | grep NVU_PEER_FB_SKIP_MODELS`: 空值 ✅
5. `/health`: OK ✅

## 4. 验证

- 单参数变更, 只改HM1不改HM2
- container env 确认: NVU_PEER_FB_SKIP_MODELS=空
- 下次数据收集验证: glm5_2_nv ATE应触发peer-fallback → HM2独立key池救援

## ⏳ 轮到HM1优化HM2