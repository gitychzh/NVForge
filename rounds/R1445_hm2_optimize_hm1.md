# R1445: HM2→HM1 — NVU_MS_GW_FALLBACK_TIMEOUT 240→280

## 数据收集 (HM1)

### 容器状态
- nv_gw 重启时间: 2026-07-15T09:32:49 UTC (R1442 deploy, 约1h前)
- ms_gw 运行: 11h
- md5sum docker-compose: 5e81a97c (R1442 deploy)

### nv_gw env (重启前)
| 参数 | 值 |
|---|---|
| UPSTREAM_TIMEOUT | 66 |
| NVU_TIER_BUDGET_DSV4P_NV | 66 |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 |
| PROXY_TIMEOUT | 360 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 240 |
| TIER_COOLDOWN_S | 15 |
| KEY_COOLDOWN_S | 25 |
| MIN_OUTBOUND_INTERVAL_S | 0 |

### 6h DB 概况 (nv_requests)
- 54 req, 34 OK, 20 fail → **63.0% SR**
- dsv4p_nv: 12 req, 2 OK, 10 fail (16.7% SR, avg 68004ms)
- glm5_2_nv: 43 req, 32 OK, 11 fail (74.4% SR, avg 17716ms)

### 6h 错误分布
| 错误类型 | 计数 | 平均耗时 |
|---|---|---|
| zombie_empty_completion | 12 | 13147ms |
| all_tiers_exhausted | 9 | 103143ms |

### 重启后 (09:32 UTC→) 数据
- 7 req, 2 OK, 5 fail → **28.6% SR** (小样本)
- dsv4p_nv: 3/3 fail (100% ATE), 0 success
- glm5_2_nv: 3/5 fail (2 zombie + 1 ATE), 2 success

### ms_gw 6h
- 35 req, 31 OK, 4 error → **88.6% SR**
- glm5_2_ms: 22 OK
- dsv4p_ms: 9 OK
- 4 MS-VARIANT-EXHAUSTED (glm5_2_ms, stream_no_data_lines)

### nv_tier_attempts 6h
- 0 rows (clean, no key cycling recorded)

## 分析

### 核心发现: dsv4p_nv ms_gw relay timeout
docker logs 显示 3 次 dsv4p_nv ATE→ms_gw fallback relay 超时:
- 248930ms (249s) > 240s limit
- 243708ms (244s) > 240s limit
- 249815ms (250s) > 240s limit

所有 3 次 relay_started=True — ms_gw 确实在 relay，但 relay 完成时间略超 240s 限制。
ms_gw 日志确认 MS-OK-STREAM for dsv4p_nv — relay 最终成功，但 nv_gw 提前超时断开。

### zombie_empty_completion 持续
12 次 zombie (NVCF content-filter, 输入>150K, 输出<30 chars) — 不可配置修复，由 openclaw 自行 fallback 处理。

### ms_gw 健康
88.6% SR, 4 MS-VARIANT-EXHAUSTED (glm5_2_ms stream_no_data_lines) — 正常水平。

## 优化决策

**NVU_MS_GW_FALLBACK_TIMEOUT: 240→280 (+40s)**

理由:
- 观测到 dsv4p_nv ms_gw relay 在 244-250s 完成，但 240s timeout 提前断开
- 280s 给 30s+ buffer 覆盖 250s
- 预算: 66s tier budget + 280s fallback = 346s < 360s PROXY_TIMEOUT (安全)
- 单参数修改，仅影响 ms_gw fallback 的超时窗口

不修改项:
- PROXY_TIMEOUT 360 足够 (346s < 360s)
- NVU_TIER_BUDGET_DSV4P_NV=66 已验证 floor (R1440)，继续
- zombie 系 NVCF content-filter，不可配置修复

## 验证

```
docker exec nv_gw env | grep NVU_MS_GW_FALLBACK_TIMEOUT
→ NVU_MS_GW_FALLBACK_TIMEOUT=280 ✓

curl -s http://localhost:40006/health
→ {"status": "ok", ...} ✓
```

容器重启: 2026-07-15T10:49:16 UTC

## 铁律
只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
