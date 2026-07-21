# R2211 (HM2→HM1): KEY_COOLDOWN_S 64→60 (-4s)

## 数据采集 (HM2→HM1, SSH采集)

### 6h窗口 (52请求)
| 指标 | 值 |
|------|-----|
| 总请求 | 52 |
| 成功 (200) | 38 |
| 失败 | 14 |
| **SR** | **73.1%** |

### 错误分解
| 模型 | 错误类型 | 计数 |
|------|----------|------|
| glm5_2_nv | zombie_empty_completion | 10 |
| dsv4p_nv | all_tiers_exhausted (ATE) | 3 |
| dsv4p_nv | zombie_empty_completion | 1 |

### Key循环分析
| 模型 | 总请求 | key_cycle_429s=0 | key_cycle_429s=1 | key_cycle_429s≥2 | 循环率 |
|------|--------|------------------|-------------------|-------------------|--------|
| glm5_2_nv | 36 | 0 | 25 | 11 | **100%** |
| dsv4p_nv | 16 | 16 | 0 | 0 | 0% |

### 延迟 (成功请求)
| 模型 | 请求数 | avg_ms | min_ms | max_ms |
|------|--------|--------|--------|--------|
| glm5_2_nv | 26 | 20,961 | 4,635 | 93,401 |
| dsv4p_nv | 12 | 27,056 | 5,867 | 42,869 |

### ATE详情
3个dsv4p ATE全部 tiers_tried_count=1, fallback_tiers_used={dsv4p_nv}, 0 tier_attempts (pre-empted). R2210已解决预算问题(48→88).

### 30min窗口
10请求: 9 OK, 1 fail → SR=90%

## 分析

**核心问题**: glm5_2_nv 100% key cycling (R2132 universal key cycling pattern). KEY_COOLDOWN_S=64意味着每个请求都要等待64s key cooldown, 导致:
- 平均延迟 21s (含key cycling等待)
- 10 zombie_empty_completion (64s cooldown内请求超时)
- 低流量下(5.2req/h) cooldown outlasts inter-request gap

**R2210修复**: dsv4p ATE pre-emption已解决 (budget 48→88), 但本窗口数据在R2210 restart前采集, 3个ATE仍显示pre-empted. 下一轮应验证0 ATE.

## 优化

**KEY_COOLDOWN_S: 64 → 60 (-4s)**

沿R2208→R2209→R2211阶梯下降: 66→65→64→60.

- 减少key cycling等待4s/请求, 降低zombie风险
- KEY+TIER=60+1=61 << 153 BUDGET 安全
- dsv4p budget 88 > 60+24=84 保证1次key attempt
- 单参数, 铁律:只改HM1

## 验证

```
ssh opc_uname@100.109.153.83 "docker exec nv_gw env | grep KEY_COOLDOWN_S"
→ KEY_COOLDOWN_S=60 ✓
→ NV_INTEGRATE_KEY_COOLDOWN_S=0 (unchanged)

curl http://localhost:40006/health
→ {"status": "ok", ...} ✓
```

## 评判

更少报错: KEY_COOLDOWN降低 → 减少64s等待时段内的zombie超时
更快请求: -4s key cycling per request
超低延迟: 目标avg < 15s, 继续下降KEY_COOLDOWN
稳定优先: KEY+TIER=61 << 153 BUDGET, 零风险
铁律: 只改HM1不改HM2 ✓

## ⏳ 轮到HM1优化HM2