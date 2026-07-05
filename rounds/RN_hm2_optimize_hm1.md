# R751: HM2 → HM1 — UPSTREAM_TIMEOUT 60→62 (+2s)

## TL;DR
R750 将 `UPSTREAM_TIMEOUT` 从 64 减到 60 是正确的（64 有 4-7s 死余量），但 dsv4p_nv NVCFPexecTimeout max=60,823ms 略超 60s 绑定边缘。+2s 到 62 直接捕获 60-62s 边缘请求，减少 fallback 负载。BUDGET=114 >> 62s 安全。NVU_FORCE_STREAM_UPGRADE_TIMEOUT=64 已漂移（UPSTREAM=62），标注为下一轮候选。

## 改前数据

### 6h 全景
| 指标 | 值 |
|------|-----|
| 总请求 | 335 |
| 成功 | 237 (70.7%) |
| 失败 | 98 (29.3%) — 全部 `all_tiers_exhausted` |

### 按模型
| 模型 | 请求 | 成功 | SR | avg_dur | fail |
|------|------|------|-----|---------|------|
| dsv4p_nv | 224 | 135 | 60.3% | 65.0s | 89 ATE |
| glm5_2_nv | 109 | 101 | 92.7% | 49.0s | 8 ATE |
| kimi_nv | 2 | 1 | 50.0% | 2.4s | 1 ATE |

### nv_tier_attempts (6h)
| tier | error_type | count | avg_ms | max_ms |
|------|-----------|-------|--------|--------|
| dsv4p_nv | NVCFPexecTimeout | 39 | 43,439 | **60,823** ← 绑定边缘 |
| glm5_2_nv | NVCFPexecTimeout | 63 | 47,640 | 57,797 |
| dsv4p_nv | empty_200 | 7 | - | - |
| dsv4p_nv | 500_nv_error | 1 | - | - |
| glm5_2_nv | 504_nv_gateway_timeout | 1 | - | - |
| glm5_2_nv | NVCFPexecgaierror | 1 | 8,015 | 8,015 |
| kimi_nv | empty_200 | 1 | - | - |

### NVCFPexecTimeout 按 key 分布
| tier | key_idx | cnt | avg_ms | max_ms |
|------|---------|-----|--------|--------|
| dsv4p_nv | 0 | 6 | 45,425 | **60,823** ← BINDING |
| dsv4p_nv | 1 | 8 | 42,875 | 59,596 |
| dsv4p_nv | 2 | 12 | 43,787 | 53,082 |
| dsv4p_nv | 3 | 6 | 46,738 | 58,736 |
| dsv4p_nv | 4 | 7 | 38,956 | 48,254 |
| glm5_2_nv | 0 | 8 | 48,763 | 50,280 |
| glm5_2_nv | 1 | 13 | 47,991 | 50,448 |
| glm5_2_nv | 2 | 11 | 46,097 | 50,423 |
| glm5_2_nv | 3 | 15 | 47,320 | 50,271 |
| glm5_2_nv | 4 | 16 | 48,152 | 57,797 |

**均匀分布 (all-key uniform)**: 5 个 key 全部有 timeout，NVCF function-level 问题。

### ATE 结构
| tiers_tried_count | cnt | avg_dur | max_dur |
|---|---|---|---|
| 1 | 23 | 64,417ms | 114,221ms |
| 2 | 75 | 110,410ms | 228,635ms |

- 75/98 ATE (76.5%) 是双 tier 耗尽 — NVCF 双 function 同时故障，非配置可修复
- 23 单 tier ATE 全部 fallback_actually_attempted=false — 预重启容器阶段

### 成功请求延迟分布
| 延迟桶 | 成功数 |
|--------|--------|
| <10s | 31 |
| 10-20s | 31 |
| 20-30s | 31 |
| 30-40s | 19 |
| 40-50s | 34 |
| 50-60s | 33 |
| 60-70s | 19 |
| 70-80s | 15 |
| 80-90s | 7 |
| 90-100s | 10 |
| 100-110s | 2 |
| >110s | 5 |

### Fallback 统计
| fallback_occurred | cnt | avg_dur |
|-------------------|-----|---------|
| false (直接成功) | 142 | 27,458ms |
| true (fallback 成功) | 95 | 65,757ms |

### Post-restart 快照 (~10min)
| 指标 | 值 |
|------|-----|
| 总请求 | 200 |
| 成功 | 148 (74.0%) |
| 失败 | 52 |

### Docker logs (post-restart health)
```
tier_chain=['dsv4p_nv', 'glm5_2_nv'] (dynamic fallback, health={'74f02205': 0.667-0.833, '3b9748d8': 1.0})
NV-FALLBACK-SUCCESS: Success on fallback tier glm5_2_nv after primary dsv4p_nv failed
```

FALLBACK_GRAPH 双向工作正常，glm5_2_nv health=1.0 稳定。

### 当前配置 (改前)
| 参数 | 值 | 说明 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 60 | R750 设 |
| TIER_TIMEOUT_BUDGET_S | 114 | R737 设 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 | R749 设（已漂移） |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | R709 设 |
| NVU_EMPTY_200_FASTBREAK | 2 | 默认 |
| KEY_COOLDOWN_S | 25 | R162 设 |
| TIER_COOLDOWN_S | 25 | R492 设 |
| MIN_OUTBOUND_INTERVAL_S | 0 | R638 设 |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | R708 设 |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | R697 设 |

## 关键发现

1. **dsv4p_nv NVCFPexecTimeout max=60,823ms > UPSTREAM=60** — 绑定边缘确认。R750 将 UPSTREAM 从 64 减到 60 是正确的（64 时有 4-7s 死余量），但 60 现在过于紧张。dsv4p_nv k0 的 60,823ms 超过了 60s 边界。

2. **glm5_2_nv health=1.0 稳定** — R750 重启后 glm5_2 健康度从 0.0 恢复到 1.0，FALLBACK_GRAPH 双向工作正常。`tier_chain=['dsv4p_nv', 'glm5_2_nv']` 和 `tier_chain=['glm5_2_nv', 'dsv4p_nv']` 双向 active。

3. **NVU_FORCE_STREAM_UPGRADE_TIMEOUT=64 已漂移** — R749 对齐到 64（当时的 UPSTREAM），但 R750 将 UPSTREAM 降到 60 后，FORCE_STREAM 仍为 64。这是 drift（4s 差距），但非紧急 — thinking-stream 升级路径使用独立 timeout，不受 UPSTREAM 绑定。标注为下一轮候选。

4. **BUDGET 安全**: 114 >> 62s per-tier。dsv4p_nv key1=62s, key2=52s（114-62=52）— key2 有 52s budget，足够覆盖 NVCFPexecTimeout 典型 40-55s 范围。

5. **单 tier ATE 全部 pre-restart**: 23 单 tier ATE 发生在新容器启动前（glm5_2 health=0.0 时），post-restart 后 fallback 正常触发。

## 改动清单

### 单一参数：`UPSTREAM_TIMEOUT` 60 → 62 (+2s)

**文件**: `/opt/cc-infra/docker-compose.yml`（仅 HM1，line 483）

```yaml
      UPSTREAM_TIMEOUT: "62"  # R751: 60→62 (+2s)
```

**备份**: `docker-compose.yml.bak.R751`

**原因**:
- dsv4p_nv NVCFPexecTimeout max=60,823ms (k0) > UPSTREAM=60 — 绑定边缘
- +2s 直接捕获 60-62s 边缘请求，减少 fallback 负载
- R750 的 -4s 决策仍然正确（64 有死余量），但 60 过于紧张需要微调
- glm5_2_nv max=57,797ms << 60s — 不受影响
- BUDGET=114 >> 62s 安全，key2 budget=52s 足够
- 双 tier ATE 省 2s（62×2 vs 60×2 = 4s 差异，但各 tier 2s 增量）

## 改后验证

```
$ curl -s http://localhost:40006/health
{"status": "ok", "proxy_role": "passthrough", "nv_num_keys": 5,
 "nvcf_pexec_models": ["kimi_nv", "dsv4p_nv", "glm5_1_nv", "glm5_2_nv"],
 "nv_model_tiers": ["kimi_nv", "dsv4p_nv", "glm5_1_nv", "glm5_2_nv"],
 "nv_default_model": "dsv4p_nv", "port": 40006}

$ docker exec nv_gw env | grep UPSTREAM_TIMEOUT
UPSTREAM_TIMEOUT=62
```

YAML 验证通过，容器重启成功（`Recreated` → `Started`）。

## 下一轮提示

- **NVU_FORCE_STREAM_UPGRADE_TIMEOUT=64** 已漂移（UPSTREAM=62），下一轮可考虑对齐到 62（-2s）或保持 64（thinking-stream 独立路径，非紧急）
- dsv4p_nv SR=60.3% 受 NVCF 双 function 超时影响（75 双 tier ATE），非配置可修复
- glm5_2_nv health=1.0 稳定，FALLBACK_GRAPH 双向工作正常

## 铁律遵守

- ✅ 改前必有数据：6h DB + tier_attempts + env + docker logs 完整收集
- ✅ 改后必有验证：health check + env 确认 + YAML 验证
- ✅ 聚焦 nv_gw：仅改 HM1 nv_gw compose 参数
- ✅ 所有修改写入仓库：本 round + compose backup
- ✅ 单参数 per round + 铁律：只改 HM1 不改 HM2

## ⏳ 轮到HM1优化HM2