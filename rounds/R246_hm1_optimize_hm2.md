# R246: HM1→HM2 — 无变更 (71st no-change verification; 全7参数均衡 & converged; 30min 99.51% 1208/1214; 5 ATE + 1 NVStream_TimeoutError; 0 budget breaks; kimi num_attempts=0 key dead; 24h 99.24% 5078/5117; 铁律:只改HM2不改HM1)

**回合类型**: 验证/无变更  
**时间**: 2026-06-28 20:28 UTC+8  
**原则**: 少改多轮 · 单参数 · 铁律:只改HM2不改HM1

---

## 数据收集

### HM2 环境变量 (docker exec hm40006 env)
| 参数 | 值 | 状态 |
|------|-----|------|
| KEY_COOLDOWN_S | 38 | 收敛区间 (34–45), 距GLOBAL=45 差7s |
| TIER_COOLDOWN_S | 45 | =GLOBAL_COOLDOWN=45, 完全收敛 |
| UPSTREAM_TIMEOUT | 63 | 保守 (floor=50, ceiling=71) |
| MIN_OUTBOUND_INTERVAL_S | 15.6 | 5×15.6=78s > GLOBAL=45s, buffer 33s |
| TIER_TIMEOUT_BUDGET_S | 115 | 充足, 0 budget breaks in logs |
| HM_CONNECT_RESERVE_S | 24 | =HM1, 跨机收敛完成 (gap=0) |
| PROXY_TIMEOUT | 300 | 固定 |
| HM_NV_MODEL_TIERS | [deepseek_hm_nv, glm5.1_hm_nv, kimi_hm_nv] | 3-tier |

### 30分钟窗口 (PostgreSQL)
```
总请求: 1214 | 成功: 1208 (99.51%)
```

**错误分布**:
| 错误类型 | 数量 |
|----------|------|
| all_tiers_exhausted | 5 |
| NVStream_TimeoutError | 1 |

**Tier分布**:
| Tier | 请求数 | fallback |
|------|--------|----------|
| deepseek_hm_nv | 1129 | 170 |
| glm5.1_hm_nv | 79 | 5 |
| (kimi fallback) | 5 | 0 |

**glm5.1 429 per key (30min)**:
| Key | 429数 |
|-----|-------|
| k0 | 60 |
| k1 | 71 |
| k2 | 75 |
| k3 | 73 |
| k4 | 79 |
| **总计** | **358** |

**Tier-level 错误 (30min)**:
| Tier | 错误类型 | 数量 |
|------|----------|------|
| deepseek_hm_nv | NVCFPexecSSLEOFError | 78 |
| deepseek_hm_nv | NVCFPexecTimeout | 25 |
| glm5.1_hm_nv | 429_nv_rate_limit | 358 |
| glm5.1_hm_nv | NVCFPexecSSLEOFError | 28 |
| glm5.1_hm_nv | NVCFPexecConnectionResetError | 16 |
| glm5.1_hm_nv | 500_nv_error | 15 |
| glm5.1_hm_nv | NVCFPexecTimeout | 1 |

### 24小时窗口
```
总请求: 5117 | 成功: 5078 (99.24%)
错误: 36 ATE + 2 NVStream_IncompleteRead + 1 NVStream_TimeoutError
```
| Tier | 请求数 | fallback |
|------|--------|----------|
| deepseek_hm_nv | 3408 | 2446 |
| glm5.1_hm_nv | 1673 | 5 |

**24h 429 per key**: k0=908, k1=819, k2=803, k3=794, k4=749 (total 4073)

### kimi 状态
- **kimi_hm_nv**: 0 tier attempts (30min & 24h) — **kimi_k2.6 API key 完全失效**
- Mock kimi-k2.6 NVCF function ID: 0 请求流经 kimi tier
- RR counter: kimi=145 (last from R1 era, never incremented since)

### 容器日志 (docker logs hm40006 --tail 200)
- 40 HM-SUCCESS 标记
- **0 budget break events** (confirmed: no `remaining X.Xs < 10s minimum`)
- 0 fallback 429 事件
- 1 deepseek SSLEOFError (latest log line)

### RR 计数器状态
```
{"hm_nv_deepseek": 6915, "hm_nv_kimi": 145, "hm_nv_glm5.1": 6101}
```

---

## 分析

### ✅ 全7参数均衡 & 收敛
所有7个可配置参数已到达各自的验证收敛目标:
- **TIER_COOLDOWN_S=45** = GLOBAL_COOLDOWN=45 — 最大收敛点, 完全对齐
- **KEY_COOLDOWN_S=38** — 在收敛区间内, 距GLOBAL=45 差7s (足够保守)
- **UPSTREAM_TIMEOUT=63** — 保守天花板, 高于floor=50, 低于ceiling=71
- **MIN_OUTBOUND_INTERVAL_S=15.6** — 5×15.6=78s > GLOBAL=45s, buffer=33s 充足
- **TIER_TIMEOUT_BUDGET_S=115** — 充足, 0 budget breaks 证明无预算压力
- **HM_CONNECT_RESERVE_S=24** — =HM1值, 跨机收敛完成 (gap=0)
- **PROXY_TIMEOUT=300** — 固定

### ✅ 99.51% 30min成功率为有效无变更信号
- 1208/1214 (99.51%) — 满足 ≥99% threshold
- 5 ATE + 1 NVStream_TimeoutError = 全NVCF server-side (外部瓶颈)
- 0 配置性参数间隙可优化
- 0 budget breaks — TIER_TIMEOUT_BUDGET_S 无压力
- deepseek 93% 流量占比 (1129/1214), 170 fallbacks 全部正常

### ✅ kimi tier 0 attempts — 不需要参数优化
- kimi_k2.6 API key 已完全失效 (Pitfall#41: kimi num_attempts=0)
- 无任何kimi请求流经 — 移除/保留kimi tier无关参数优化

### ✅ 70+ 轮稳定性plateau确认
- 连续70+轮无变更验证 — 所有参数已到验证收敛点
- 错误模式完全一致: ATE + NVStream (NVCF server-side)
- 无配置漂移, 无参数退化

---

## 执行: 无变更

**为什么是无变更轮**:
1. 30min 99.51% 成功 → ≥99% threshold 满足
2. 所有7参数在验证收敛目标 → 无可改参数
3. 0 budget breaks → TIER_TIMEOUT_BUDGET_S 无需增加
4. 错误全NVCF server-side (ATE + NVStream_TimeoutError) → 非配置性瓶颈
5. kimi tier 0 attempts → kimi key 死, 与参数优化无关
6. Key-level 429均匀分布 (k0=60, k1=71, k2=75, k3=73, k4=79) → 函数级饱和, 非单key优化
7. 无budget break事件 → 无预算压力 → 无TIER_TIMEOUT_BUDGET_S增加需求

**为什么不是其他参数**:
- **KEY_COOLDOWN_S**: 38在收敛区间 (34–45), 距GLOBAL=45差7s — 无需调整 (429分布均匀, 函数级饱和)
- **TIER_COOLDOWN_S**: 45=GLOBAL_COOLDOWN — 完全收敛, 无需调整
- **UPSTREAM_TIMEOUT**: 63保守 — 高于floor=50, SSLEOFError=28/30min在可接受范围
- **MIN_OUTBOUND_INTERVAL_S**: 15.6 → 5×15.6=78s, buffer=33s > GLOBAL=45 — 充足, 无需调整
- **TIER_TIMEOUT_BUDGET_S**: 115 — 0 budget breaks 证明无压力, 无需调整
- **HM_CONNECT_RESERVE_S**: 24 = HM1 — 跨机收敛完成, 无需调整
- **PROXY_TIMEOUT**: 300固定 — 不触及

**验证命令** (无执行):
```
# All verified from running container — no changes needed
docker exec hm40006 env | grep KEY_COOLDOWN_S      # → 38
docker exec hm40006 env | grep TIER_COOLDOWN_S       # → 45
docker exec hm40006 env | grep UPSTREAM_TIMEOUT      # → 63
docker exec hm40006 env | grep MIN_OUTBOUND_INTERVAL_S  # → 15.6
docker exec hm40006 env | grep TIER_TIMEOUT_BUDGET_S    # → 115
docker exec hm40006 env | grep HM_CONNECT_RESERVE_S    # → 24
docker exec hm40006 env | grep PROXY_TIMEOUT         # → 300
```

---

## 预期效果

| 指标 | 当前 | 预期 (不变) |
|------|------|-------------|
| 30min 成功率 | 99.51% | 99.51% (无变化) |
| 24h 成功率 | 99.24% | 99.24% (无变化) |
| budget breaks | 0 | 0 (无变化) |
| 错误类型 | 5 ATE + 1 NVStream | 同 (NVCF server-side) |
| 429 分布 | 均匀 (k0~k4) | 均匀 (函数级饱和) |

---

## ⏳ 轮到HM2优化HM1  ← 脚本检测此标记