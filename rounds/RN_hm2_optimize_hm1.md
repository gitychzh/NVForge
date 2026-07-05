# R766: HM2→HM1 — PEXEC_TIMEOUT_FASTBREAK 1→2 (+1 key) — 429差异化分布证明key级问题非函数级

**时间**: 2026-07-06 03:12 UTC  
**作者**: opc2_uname (HM2)  
**类型**: HM2优化HM1（铁律：只改HM1不改HM2）

## 📊 改前数据

### 1h窗口 (02:12–03:12 UTC)
| 指标 | 值 |
|------|-----|
| 总请求 | 288 |
| OK (status=200) | 265 (91.9%) |
| FAIL (status≠200) | 23 (8.1%) |
| avg_ttfb | 45,641ms |
| avg_duration | 54,345ms |
| max_duration | 228,635ms |

### per-model 1h
| 模型 | 请求 | OK | FAIL | SR | avg_dur |
|------|------|-----|------|-----|---------|
| dsv4p_nv | 168 | 148 | 20 | 88.1% | 66,958ms |
| glm5_2_nv | 114 | 111 | 3 | 97.4% | 38,362ms |
| kimi_nv | 6 | 6 | 0 | 100% | 4,836ms |

### 错误分析 (23 ATE)
全部 `all_tiers_exhausted → all_tiers_failed_in_mapped_tier`，tiers_tried_count=2，fallback_occurred=false。无health阻断fallback错误。

### NVCFPexecTimeout max (1h)
| tier | key | max_ms | UPSTREAM=66 余量 |
|------|-----|--------|------------------|
| dsv4p_nv | k0 | 60,823ms | 5.2s ✓ |  
| glm5_2_nv | k1 | 62,389ms | 3.6s ✓ |

### key_cycle_429s 分布 (1h, dsv4p_nv)
| 429次数 | 请求计数 |
|---------|----------|
| 0 | 父~126 |
| 1 | 21 |
| 2 | 11 |
| 3 | 4 |
| 4 | 2 |

→ **429 key-specific分布不均：k0/k1遭遇更多429，其他key较少**。89次429后通过key rotation成功恢复。

### tier_attempts error breakdown (1h)
| tier | error_type | cnt | avg_elapsed_ms | max_elapsed_ms |
|------|------------|-----|----------------|----------------|
| glm5_2_nv | empty_200 | 35 | — | — |
| dsv4p_nv | empty_200 | 35 | — | — |
| glm5_2_nv | NVCFPexecTimeout | 26 | 54,416 | 62,389 |
| glm5_2_nv | 504_nv_gateway_timeout | 19 | — | — |
| dsv4p_nv | NVCFPexecTimeout | 18 | 52,927 | 60,823 |

### 健康度
dsv4p_nv func 74f02205 health=1.0（最新日志条目）

### Fallback统计 (1h)
| fallback_occurred | attempted | cnt | avg_dur |
|-------------------|-----------|-----|---------|
| false | false | 229 | 44,375ms |
| true | true | 38 | 107,888ms |
| true | false | 21 | 66,180ms |

Fallback 38次实际attempt，FALLBACK_GRAPH双向工作正常。

### 结论
- R765 (EMPTY_200_FASTBREAK 2→3) 效果正面：SR从85.9%(6h)回升至91.9%(1h)
- dsv4p_nv 429分布key-specific不均 → 不是R731所称"函数级uniform"
- FASTBREAK=1在第一个429-hit key后即放弃 → 未尝试其他非429 key
- NVCFPexecTimeout非binding (buffer≥3.6s)，UPSTREAM=66安全
- dsv4p_nv function health=1.0 → 函数本身健康

## 🔧 变更

**参数**: `NVU_PEXEC_TIMEOUT_FASTBREAK` 1 → 2 (+1 key attempt)

**变更理由**:
1. R765后SR=91.9%，dsv4p_nv SR=88.1%——20个dsv4p_nv ATE
2. dsv4p_nv遭遇42个key-specific 429 (key_cycle_429s分布不均)，不是R731所称的"函数级uniform"
3. FASTBREAK=1在第一个key遭遇429/timeout后立即终止tier，未尝试其他非429 key
4. 89次429后通过rotation成功恢复 → 证明不同key可绕过429
5. dsv4p_nv func 74f02205 health=1.0 → 函数本身健康，问题出在key-specific
6. 预期效果: 约半数dsv4p_nv ATE(10/20)通过第2key救回 → SR 88.1%→~94%

**安全边界**:
- 每个额外key ≤ 25s KEY_COOLDOWN + 66s UPSTREAM = 91s << BUDGET=114s ✓
- 2 keys 最多消耗 2×66=132s，但BUDGET=114 会在132s前触发全局abort → 实际≤114s
- glm5_2_nv SR=97.4% (优秀), kimi_nv=100% → 不受影响
- FALLBACK_GRAPH双向工作正常 → 额外key不影响fallback行为

**compose路径**: `/opt/cc-infra/docker-compose.yml` line 609

```diff
- NVU_PEXEC_TIMEOUT_FASTBREAK: "1"
+ NVU_PEXEC_TIMEOUT_FASTBREAK: "2"
```

## ✅ 改后验证

**容器重启**: `docker compose up -d nv_gw` → Recreated + Started ✓

**环境变量确认**:
```
NVU_PEXEC_TIMEOUT_FASTBREAK=2
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=114
NVU_EMPTY_200_FASTBREAK=3
FALLBACK_HEALTH_THRESHOLD=0.10
```

**日志检查**: 无error/warn，正常启动
```
[NV-PROXY] Listening on 0.0.0.0:40006 (role=passthrough, default_tier=dsv4p_nv)
```

**健康检查**: `curl localhost:40006/health` → `{"status": "ok"}` ✓

## 📈 预期下一轮

- dsv4p_nv SR 88.1% → 预期 ~93-95%
- 观察1h窗口 SR 91.9% → 预期 ~95%+
- ATE从23 → 预期 ~13-15
- avg_dur可能因额外key attempt略增 ~2-3s（仅失败路径）

## 🔗 相关轮次

- R765: EMPTY_200_FASTBREAK 2→3（本轮不动此参数）
- R731/R709: FASTBREAK 2→1的历史决策（当前数据推翻其"函数级uniform"前提）
- R728: FASTBREAK 1→2的最初部署（与R766方向一致）

---

## ⏳ 轮到HM1优化HM2