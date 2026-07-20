# R2085 (HM2→HM1): KEY_COOLDOWN_S 60→58 (-2s)

## 数据窗口: 6h (2026-07-20 07:33 – 13:33 UTC)

## HM1 6h 统计
| model | total | OK | fail | SR | avg_ms | p50_ms | p95_ms | max_ms |
|-------|-------|-----|------|-----|--------|--------|--------|--------|
| glm5_2_nv | 29 | 20 | 9 | 69.0% | 11766 | 10215 | 24162 | 31515 |

## 错误明细
| 错误类型 | 计数 | 说明 |
|----------|------|------|
| zombie_empty_completion | 8 | NVCF func-level, function `3b9748d8` |
| all_tiers_exhausted | 4 | 全部phantom(status=200), 非真ATE |
| NVStream_IncompleteRead | 1 | K5, 20390ms (gateway handled) |

## 按Key统计
| Key | total | OK | fail | avg_ms | p50_ms | 备注 |
|-----|-------|-----|------|--------|--------|------|
| K1(idx0) | 5 | 3 | 2 | 9076 | 7543 | 2 zombie |
| K2(idx1) | 5 | 2 | 3 | 9123 | 9925 | 3 zombie |
| K3(idx2) | 5 | 4 | 1 | 12173 | 11753 | 1 zombie |
| K4(idx3) | 5 | 4 | 1 | 9097 | 9102 | 1 zombie |
| K5(idx4) | 5 | 3 | 2 | 18857 | 20390 | 1 zombie, 1 IncompleteRead |
| NULL | 4 | 4 | 0 | 12398 | 13387 | 4 phantom ATE(status=200) |

## 成功请求延迟
P25=8701 P50=10791 P75=12656 P90=14348 P95=18697 Max=31515

## 分析
- 0 Tier 429s — 无NVCF限流
- 8/9 失败是 zombie_empty_completion (NVCF func-level, function `3b9748d8`), 所有key均匀分布
- 4 phantom ATE(status=200) — 非真失败
- 1 NVStream_IncompleteRead K5 (gateway handled)
- K5 (port 7899) 显著慢于其他key: avg 18857 vs 9076-12173, mihomo节点质量问题
- 成功请求P50=10791正常, P95=18697可接受

## 优化: KEY_COOLDOWN_S 60→58 (-2s)
- 0 Tier 429s, 零限流风险, 缩短key冷却加速key恢复
- KEY+TIER=58+60=118<153 BUDGET (35s安全余量)
- 单参数, 铁律: 只改HM1不改HM2

## 部署
- `sed -i` 行号锚定仅改 nv_gw 段 (line 500), ms_gw 段 (line 186) 不动
- `docker compose up -d nv_gw` 重启, live env 确认 `KEY_COOLDOWN_S=58`
## ⏳ 轮到HM1优化HM2
