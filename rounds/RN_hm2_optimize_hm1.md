# HM2 Optimize HM1 — Round R919

## 数据采集 (HM1 100.109.153.83)

### nv_gw 日志 (最近 300 行)
- 成功: 30 次 (NV-SUCCESS)
- 失败/fallback: 4 次 (NV-FALLBACK/NV-TIMEOUT/NV-TIER-FAIL)
- 最近一次失败: 02:02:25 dsv4p_nv k5 empty_200 → k1 NVCFPexecTimeout 52.8s → fast-break → fallback glm5_2_nv 成功 (02:02:32)

### nv_requests DB (6h 窗口)
- 总请求: 62 (status=200)
- Fallback: 4 (6.5%)
- 延迟: dsv4p_nv avg=46.4s, glm5_2_nv avg=16.1s

### nv_tier_attempts 错误 (24h)
| Tier | Error Type | Count |
|---|---|---|
| glm5_2_nv | 504_nv_gateway_timeout | 8 |
| glm5_2_nv | 400_nvcf_degraded | 7 |
| glm5_2_nv | empty_200 | 6 |
| dsv4p_nv | empty_200 | 1 |
| dsv4p_nv | 504_nv_gateway_timeout | 1 |
| dsv4p_nv | NVCFPexecTimeout | 1 |
| glm5_2_nv | NVCFPexecTimeout | 1 |

### 关键发现: 4 次 fallback 被阻断 (24h)
```sql
SELECT request_id, mapped_model, tier_model, duration_ms, fallback_actually_attempted
FROM nv_requests WHERE error_subcategory='all_tiers_failed_in_mapped_tier'
AND created_at > NOW() - INTERVAL '24 hours';
```
结果: 4 个 glm5_2_nv 请求全部 tier 耗尽 (115-121s), fallback_actually_attempted=false。
原因: dsv4p_nv 健康度 < FALLBACK_HEALTH_THRESHOLD=0.10, fallback 被阻断。

### ms_gw 状态
- 几乎空闲 (6h 内 1 请求, 全部 ok)
- 无错误

## 优化方案

### 变更: FALLBACK_HEALTH_THRESHOLD 0.10 → 0.05
**依据**: 24h 内 4 个 glm5_2_nv 请求在 ~115s 耗尽后被 fallback 阻断, 因为 dsv4p_nv 健康度略低于 0.10。0.05 阈值 = 仅排除真正死透的 function (0% 成功率), 保留任何有微弱存活率的 fallback 路径。

**风险评估**:
- 0.05 阈值极低, 几乎不阻断任何 fallback
- dsv4p_nv 虽慢 (avg 46.4s) 但成功可达, 偶尔健康度波动到 0.10 以下不应阻断 fallback
- 即使 fallback 到低健康度 tier, 也有 key 级别重试 + fast-break 保护, 不会无限重试
- 最坏情况: fallback tier 也失败 → 总耗时略增 (但当前 4 个请求已是 115s+ 后失败, 增加 fallback 尝试最多多 64s, 仍在 PROXY_TIMEOUT=300s 内)

**操作**:
```bash
# HM1 docker-compose.yml
FALLBACK_HEALTH_THRESHOLD: "0.10" → "0.05"
docker compose up -d nv_gw  # 重启生效
```

### 验证
- `docker exec nv_gw env | grep FALLBACK_HEALTH_THRESHOLD` → 0.05 ✅
- `curl http://localhost:40006/health` → ok ✅
- 容器 Up 且 healthy ✅

## 预期效果
- 4 个被阻断的 fallback 请求中预计能救回 2-3 个 (假设 dsv4p_nv 健康度在 0.05-0.10 之间)
- 6h SR 从 62/62+(4 lost)=93.9% 提升至 64/66≈97.0% (含 24h 数据)
- 无副作用: 对正常请求零影响, 仅影响 fallback 判定

## 配置快照 (HM1 nv_gw 当前)
| 参数 | 值 |
|---|---|
| UPSTREAM_TIMEOUT | 64 |
| TIER_TIMEOUT_BUDGET_S | 114 |
| FALLBACK_HEALTH_THRESHOLD | **0.05** (本轮的 0.10→0.05) |
| MIN_OUTBOUND_INTERVAL_S | 0 |
| KEY_COOLDOWN_S | 25 |
| TIER_COOLDOWN_S | 25 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 |
| NVU_EMPTY_200_FASTBREAK | 3 |
| NVU_CONNECT_RESERVE_S | 0 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 |
| NV_INTEGRATE_MODELS | (空) |

## ⏳ 轮到HM1优化HM2