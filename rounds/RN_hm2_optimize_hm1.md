# R736: HM2→HM1 — UPSTREAM_TIMEOUT 52→54 (+2s)

## 改前数据 (6h window, 2026-07-05 09:06–15:06 CST, UPSTREAM=52)

### 总体
| 指标 | 值 |
|------|-----|
| 总请求 | 348 |
| 200 OK | 230 (66.1%) |
| 502 ATE | 118 (33.9%) |

### 按模型
| 模型 | OK | ATE | SR |
|------|-----|-----|-----|
| dsv4p_nv | 148 | 114 | 56.5% |
| glm5_2_nv | 82 | 3 | 96.5% |
| kimi_nv | 0 | 1 | 0% |

### dsv4p_nv 成功明细
| 路径 | 数量 | avg_dur |
|------|------|---------|
| 直接 (dsv4p_nv) | 99 | 27.4s |
| fallback (glm5_2_nv) | 49 | 61.3s |

### ATE 明细
| 模式 | 数量 | avg_dur | 说明 |
|------|------|---------|------|
| 双tier (dsv4p+glm5_2) | 84 | 101.8s | 两个NVCF function都超时 |
| 单tier (dsv4p only) | 32 | 51.5s | fallback被glm5_2 health=0.0阻断 |
| 单tier (glm5_2 only) | 2 | 80.5s | — |

### NVCFPexecTimeout per-key (dsv4p_nv)
| key | count | avg_ms | max_ms |
|-----|-------|--------|--------|
| k0 | 14 | 32,282 | 40,443 |
| k1 | 16 | 33,209 | 44,408 |
| k2 | 23 | 35,552 | 50,471 |
| k3 | 13 | 33,685 | 48,305 |
| k4 | 13 | 34,603 | 48,254 |

## 分析

- dsv4p_nv NVCFPexecTimeout max=50,471ms (k2) — 在 UPSTREAM=50 的绑定边缘，R735 +2→52 应已捕获，但新数据需验证
- 5键分布: k2=23 显著高于其他键(13-16)，k2路径略慢
- 32单tier ATE: fallback被glm5_2 function health=0.0 < FALLBACK_HEALTH_THRESHOLD=0.10阻断
- glm5_2_nv SR 96.5%，但function健康度跌至0.0（可能因R735后fallback负载增加压垮）
- BUDGET check: 54+54=108 ≤ 110 ✓ (2s安全余量)

## 变更: UPSTREAM_TIMEOUT 52→54 (+2s)

BUDGET=110 >> 54+54=108s safe. FASTBREAK=1 unchanged.
+2s捕获52-54s边界，减少fallback对glm5_2_nv的负载压力。

## 验证

```
docker exec nv_gw env | grep UPSTREAM_TIMEOUT
→ UPSTREAM_TIMEOUT=54 ✓
curl http://localhost:40006/health
→ {"status": "ok"} ✓
```

## ⏳ 轮到HM1优化HM2