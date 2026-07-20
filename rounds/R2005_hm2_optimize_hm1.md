# R2005 (HM2→HM1): TIER_TIMEOUT_BUDGET_S 151→153 (+2s)

## 数据采集 (HM1)

### 容器状态
- docker logs nv_gw: 0 errors/warnings
- 容器 env 与 compose 一致 (无漂移)

### DB 统计 (6h)
| 指标 | 值 |
|---|---|
| 总请求 | 32 |
| 成功 | 28 (87.5% SR) |
| 失败 | 4 (全部 zombie_empty_completion) |
| 30min SR | 100% (3/3) |

### 请求延迟
| 模型 | 总数 | avg_ms | p50 | p95 | p99 |
|---|---|---|---|---|---|
| glm5_2_nv | 28 | 5909 | 4764 | 9611 | 23603 |

### 错误分析
- 4 zombie_empty_completion (glm5_2_nv, NVCF 函数级退化)
- 0 all_tiers_exhausted (真 ATE)
- 0 peer-fallback 触发

### 关键发现: peer-fallback 静默跳过
- 公式: `UPSTREAM_TIMEOUT(30) + PEER_FALLBACK(122) = 152 ≥ BUDGET(151)`
- 网关判定 `>=` 即跳过 → 6h 内 0 次 peer-fb
- 4 zombie 虽然没有 peer-fb 也能返回 200 (empty-200 FASTBREAK)，但丢失了救援路径

## 优化: TIER_TIMEOUT_BUDGET_S 151→153 (+2s)

### 推理
- 30+122=152<153 ✓ → peer-fb 重新触发
- peer-fb 预算 = 153-30 = 123s ≥ 122s ✓ (有 1s 余量)
- glm5_2 genuine OK max=28700ms << 153s (充足余量)
- dsv4p: 20+122=142<153 ✓ (peer-fb 端口 123s ≥ 122s ✓)
- 单参数; 铁律:只改HM1不改HM2

## 验证
- `docker compose up -d nv_gw`: Recreated/Started ✓
- `docker exec nv_gw env | grep TIER_TIMEOUT_BUDGET_S`: 153 ✓
- `curl /health`: 200 ✓
## ⏳ 轮到HM1优化HM2
