# R1924 (HM2→HM1): NVU_TIER_BUDGET_GLM5_2_NV 44→42 (-2s)

## 数据 (6h窗口, HM1 DB)

| 指标 | 值 |
|---|---|
| 总请求 | 37 |
| 成功 | 26 (70.3% SR) |
| 失败 | 11 |
| zombie_empty_completion (glm5_2) | 9 |
| ATE (dsv4p, status=502) | 2 |
| phantom ATE (status=200) | 5 (3 dsv4p + 2 glm5_2) |
| peer-fb triggered | 0 |
| key_cycle_429s (glm5_2) | 23 (21×1 cycle + 2×2 cycles) |

### 成功延迟 (6h)

| model | total | avg_ms | min_ms | max_ms |
|---|---|---|---|---|
| glm5_2_nv | 22 | 8655 | 2333 | 27809 |
| dsv4p_nv | 4 | 16485 | 1963 | 43081 |

### tier_attempts

| tier | error_type | cnt |
|---|---|---|
| glm5_2_nv | pexec_success | 23 |
| glm5_2_nv | pexec_SSLEOFError | 1 |
| glm5_2_nv | pexec_timeout | 1 |

### 其他

- 全部37请求均为big input (≥115000 chars)
- 0 fallback_occurred
- nv_gw 容器在R1923重启后无新error/warn日志

## 优化

**NVU_TIER_BUDGET_GLM5_2_NV: 44→42 (-2s)**

- glm5_2 OK max=27809ms < UPSTREAM=30s 安全
- 节省2s per zombie fail path
- 23 key_cycle_429s 持续表明glm5_2 key耗尽/429频繁
- 单参数，铁律：只改HM1不改HM2

## 验证

- `docker compose up -d nv_gw` 已重建容器
- `docker exec nv_gw env` 确认 NVU_TIER_BUDGET_GLM5_2_NV=42
- `/health` 返回 ok
## ⏳ 轮到HM1优化HM2