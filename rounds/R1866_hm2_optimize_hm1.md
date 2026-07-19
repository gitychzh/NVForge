# R1866 (HM2→HM1): KEY_COOLDOWN_S 50→48, TIER_COOLDOWN_S 50→48 (-2s each)

## 改前数据 (2026-07-19 ~09:10 UTC)

### 6h窗口
| 指标 | 值 |
|------|-----|
| 总请求 | 37 |
| 成功 | 14 |
| 失败 | 23 |
| SR | 37.8% |
| avg OK duration | 7300ms |

### 按模型
| 模型 | 总请求 | 成功 | 失败 | SR | avg OK |
|------|--------|------|------|-----|--------|
| glm5_2_nv | 34 | 11 | 23 | 32.4% | 6733ms |
| dsv4p_nv | 3 | 3 | 0 | 100% | 9381ms |

### 错误分析
- 全部23条失败: `zombie_empty_completion` (NVCF侧, 不可配置修复)
- 0 ATE, 0 SSLEOF, 0 429, 0 peer-fb超时
- 3条 ATE phantom (status=200, error_type=all_tiers_exhausted, dsv4p_nv, 1 tier tried): 非真实失败

### 30min窗口
- 4 req, 0 OK, 4 fail (全部zombie, 最近活跃期)

### 容器健康
- nv_gw: Up 5 minutes (healthy), /health ok
- 所有容器正常
- docker logs 0 errors
- 无fallback事件

## 分析
- glm5_2_nv 持续NVCF zombie降级状态, 23条全部为NVCF侧不可修复错误
- dsv4p_nv 100% SR, 3/3 OK
- HM2 KEY=25 / TIER=25 证明50→48保守
- 48+48=96 << 178 TIER_BUDGET 安全
- 48s > 25s (HM2参考) 仍远保守
- 无peer-fb约束冲突 (UPSTREAM=49 + PEER=122 = 171 < 178)

## 优化
- KEY_COOLDOWN_S: 50 → 48 (-2s)
- TIER_COOLDOWN_S: 50 → 48 (-2s)
- 单参数对; 铁律:只改HM1不改HM2

## 验证
- docker exec nv_gw env: KEY_COOLDOWN_S=48 ✓, TIER_COOLDOWN_S=48 ✓
- curl /health: status=ok ✓
- docker compose up -d nv_gw: restarted, env confirmed
## ⏳ 轮到HM1优化HM2
