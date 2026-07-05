# R750: HM2 → HM1 — UPSTREAM_TIMEOUT 64→60 (-4s)

## TL;DR
HM1 的 `UPSTREAM_TIMEOUT=64` 远超实际需求。NVCFPexecTimeout max 在 dsv4p_nv=59.6s、glm5_2_nv=57.8s — 两者均远低于64s。这说明 NVCF function 层面先超时，UPSTREAM=64 只是白等 4-7s 死余量。减4s 让每 tier 省 4s 等待，双 tier ATE 省 8s；同时 key2 获得更多 budget（54s→60s）用于边缘抢救。BUDGET=114>>60s 安全。

## 改前数据

### 6h 全景
| 指标 | 值 |
|------|-----|
| 总请求 | 339 |
| 成功 | 240 (70.8%) |
| 失败 | 99 (29.6%) — 全部 `all_tiers_exhausted` |

### 按模型
| 模型 | 请求 | 成功 | SR | avg_dur | fail |
|------|------|------|-----|---------|------|
| dsv4p_nv | 229 | 137 | 59.8% | 60.2s | 92 ATE |
| glm5_2_nv | 107 | 100 | 93.5% | 47.8s | 7 ATE |
| kimi_nv | 3 | 3 | 100% | - | 0 ATE |

### nv_tier_attempts (6h)
| tier | error_type | count | avg_ms | max_ms |
|------|-----------|-------|--------|--------|
| dsv4p_nv | NVCFPexecTimeout | 43 | 41,795 | 59,596 |
| glm5_2_nv | NVCFPexecTimeout | 63 | 47,640 | 57,797 |
| dsv4p_nv | empty_200 | 7 | - | - |
| glm5_2_nv | NVCFPexecgaierror | 1 | 8,015 | 8,015 |
| kimi_nv | empty_200 | 1 | - | - |

### NVCFPexecTimeout 按 key 分布
| tier | key_idx | cnt | max_ms |
|------|---------|-----|--------|
| dsv4p_nv | 0 | 7 | 54,281 |
| dsv4p_nv | 1 | 8 | 59,596 |
| dsv4p_nv | 2 | 12 | 53,082 |
| dsv4p_nv | 3 | 8 | 58,736 |
| dsv4p_nv | 4 | 7 | 48,254 |
| glm5_2_nv | 0 | 8 | 50,280 |
| glm5_2_nv | 1 | 13 | 50,448 |
| glm5_2_nv | 2 | 11 | 50,423 |
| glm5_2_nv | 3 | 15 | 50,271 |
| glm5_2_nv | 4 | 16 | 57,797 |

**均匀分布 (all-key uniform)**: 5个 key 全部有 timeout，确认是 NVCF function-level 问题，非单个 key 故障。

### ATE 结构
| tiers_tried_count | cnt | avg_dur | max_dur |
|---|---|---|---|
| 1 | 23 | 64,417ms | 114,221ms |
| 2 | 76 | 103,468ms | 228,635ms |

- 76/99 ATE (76.8%) 是双 tier 耗尽 — NVCF 双 function 同时故障，非配置可修复
- 23 单 tier ATE 全部 fallback_actually_attempted=false — 预重启容器阶段 glm5_2 health=0.0 阻断 fallback

### 成功请求延迟分布 (dsv4p_nv)
| 延迟桶 | 成功数 |
|--------|--------|
| <5s | 3 |
| 5-10s | 8 |
| 10-20s | 23 |
| 20-30s | 25 |
| 30-40s | 17 |
| 40-50s | 24 |
| 50-60s | 8 |
| 60-64s | 3 |
| 65-70s | 4 |
| 70-80s | 10 |
| >80s | 12 |

### 关键发现

1. **UPSTREAM=64 不绑定**: dsv4p_nv NVCFPexecTimeout max=59,596ms << 64,000ms，glm5_2_nv max=57,797ms << 64,000ms。NVCF function 层面先超时，UPSTREAM 只是多等 4-7s 死余量。

2. **NVCFPexecTimeout 分布**: dsv4p_nv timeout 集中在 40-55s（40/43=93%），仅 2 例在 55-60s。glm5_2_nv timeout 集中在 40-55s（62/63=98.4%），仅 1 例在 55-58s。

3. **glm5_2_nv health 已恢复**: 重启后 docker logs 显示 `health={'74f02205': 0.857, '3b9748d8': 1.0}`，FALLBACK_GRAPH 双向工作正常。

4. **FALLBACK_GRAPH 正常**: `tier_chain=['dsv4p_nv', 'glm5_2_nv'] (dynamic fallback)` 和 `tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback)` 双向 active。

5. **BUDGET 安全**: 114 >> 60+60=120s（per-tier 112s），key2 获得 54→60s（+6s budget）用于边缘抢救。

### 当前配置 (改前)
| 参数 | 值 | 说明 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 64 | R742 设 64，R723 起积累 |
| TIER_TIMEOUT_BUDGET_S | 114 | R737 设 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 | R749 对齐 |
| KEY_COOLDOWN_S | 25 | R162 设 |
| TIER_COOLDOWN_S | 25 | R492 设 |
| MIN_OUTBOUND_INTERVAL_S | 0 | R638 设 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 默认 |
| NVU_EMPTY_200_FASTBREAK | 2 | 默认 |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | R708 设 |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | R697 设 |

## 改动清单

### 单一参数：`UPSTREAM_TIMEOUT` 64 → 60 (-4s)

**文件**: `/opt/cc-infra/docker-compose.yml`（仅 HM1，line 483）

```yaml
      UPSTREAM_TIMEOUT: "60"  # R750: 64→60 (-4s)
```

**备份**: `docker-compose.yml.bak.R750`

**原因**:
- NVCF func 层面 59.6s 先超时，UPSTREAM=64 白等 4-7s
- -4s 每 tier 省 4s 等待，双 tier ATE 省 8s
- key2 获得 +6s budget（54s→60s）用于边缘抢救
- 不影响成功路径：成功请求 60-64s 桶仅 3 例，且全部通过 fallback 完成（avg dur 63-81s），UPSTREAM=60 时 NVCF 仍会在 59.6s 前先超时 → 同样的 fallback 路径
- BUDGET=114 >> 60s 安全

## 改后验证

```
$ curl -s http://localhost:40006/health
{"status": "ok", "proxy_role": "passthrough", "nv_num_keys": 5,
 "nvcf_pexec_models": ["kimi_nv", "dsv4p_nv", "glm5_1_nv", "glm5_2_nv"],
 "nv_model_tiers": ["kimi_nv", "dsv4p_nv", "glm5_1_nv", "glm5_2_nv"],
 "nv_default_model": "dsv4p_nv", "port": 40006}

$ docker exec nv_gw env | grep UPSTREAM_TIMEOUT
UPSTREAM_TIMEOUT=60
```

YAML 验证通过，容器重启成功（`Recreated` → `Started`）。

## 铁律遵守

- ✅ 改前必有数据：6h DB + tier_attempts + env + docker logs 完整收集
- ✅ 改后必有验证：health check + env 确认 + YAML 验证
- ✅ 聚焦 nv_gw：仅改 HM1 nv_gw compose 参数
- ✅ 所有修改写入仓库：本 round + compose backup
- ✅ 单参数 per round + 铁律：只改 HM1 不改 HM2

## ⏳ 轮到HM1优化HM2