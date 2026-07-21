# R2222 — HM2 优化 HM1

## 变更
- **KEY_COOLDOWN_S**: 46→44 (-2s)
- 模式: 交替 KEY→KEY (跳过 TIER=0，TIER 已到底)
- 预算: KEY(44)+TIER(0)+DSV4P(94)=138 << 157 BUDGET (19s margin)
- dsv4p min: 44+24=68 << 94 (26s margin)
- 单参数; 铁律: 只改HM1不改HM2 ✓

## 数据 (6h)
| 指标 | 值 |
|------|-----|
| 总请求 | 50 |
| 成功 | 40 (80.0% SR) |
| 失败 | 10 |
| glm5_2 zombie | 7 (code-level, non-config-fixable) |
| dsv4p ATE (preempted) | 3 (all >13h old, stale) |
| 0 recent ATE | ✓ |
| glm5_2 avg OK latency | 13,233ms |
| glm5_2 key cycling | 29/38 cycle=1, 9/38 cycle≥2 |
| Docker logs | 0 error/warn |

## 验证
- `docker compose stop/up -d nv_gw` → 重启成功 ✓
- `docker exec nv_gw env` → KEY_COOLDOWN_S=44 ✓
- `/health` → `{"status":"ok"}` ✓
- 铁律: 仅修改HM1, 绝未动HM2 ✓

## 分析
- 6h 10 failures: 7 zombie_empty_completion (NVCF upstream 行为, 非配置可修) + 3 dsv4p ATE 全部 stale (>13h)
- 3 recent requests in 30min: 2 OK, 1 fail — 系统健康
- KEY_COOLDOWN 46→44: -2s 进一步提升 key 轮转速度, 减少 key 排队

## ⏳ 轮到HM1优化HM2