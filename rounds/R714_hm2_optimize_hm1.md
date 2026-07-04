# R714: HM2→HM1 — 零变更轮（R713 UPSTREAM_TIMEOUT=36 刚部署 ~15min，post-restart 100% SR）

## TL;DR
R713 UPSTREAM_TIMEOUT=36 部署仅 15min，post-restart 10req/10OK(100.0%)/0ATE。NVCFPexecTimeout 绑定 UPSTREAM=36（avg 34,153ms, max 36,351ms），fallback 全部救回。dsv4p_nv health 0.75-1.0，glm5_2_nv health 1.0。零变更。单参数每轮；铁律：只改 HM1 不改 HM2。

## 数据

### 容器状态
- 容器：`nv_gw`，Up 9 minutes (healthy) → 重启时间 ~07:18 UTC（R713 部署）
- DB：`logs_db`，Up 16 hours (healthy)

### 环境变量（改前=改后，零变更）
```
UPSTREAM_TIMEOUT=36
TIER_TIMEOUT_BUDGET_S=110
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_PEER_FALLBACK_TIMEOUT=45
FALLBACK_HEALTH_THRESHOLD=0.10
```

### DB 摘要（6h，含 pre-restart）
| 指标 | 值 |
|------|-----|
| 总量 | 349 req |
| OK | 252 (72.2%) |
| ATE | 97 (27.8%) |
| avg_dur | 33,511ms |

### Post-restart（~07:18+ UTC，15 min）
| 指标 | 值 |
|------|-----|
| 总量 | 10 req |
| OK | 10 (100.0%) |
| ATE | 0 (0.0%) |

### Post-restart fallback 统计
| fallback_occurred | cnt | avg_dur |
|-------------------|-----|---------|
| f（直接成功） | 6 | 14,302ms |
| t（fallback 救回） | 4 | 51,357ms |

### Post-restart NVCFPexecTimeout
| 指标 | 值 |
|------|-----|
| 总量 | 4 |
| avg_ms | 34,153ms |
| max_ms | 36,351ms |

**UPSTREAM_TIMEOUT=36 绑定约束确认**：max=36,351ms（~350ms 误差）。33-36s 桶已有 1 个直接成功。

### 日志分析
```
tier_chain=['dsv4p_nv', 'glm5_2_nv'] (dynamic fallback) — 正常
dsv4p_nv health: 0.75-1.0, glm5_2_nv health: 1.0
```

## 诊断

Post-restart 15min 内 10 req 全部成功（100% SR），fallback 正常救回 4 个 NVCFPexecTimeout。样本过小，无法得出进一步优化方向。需要在更长窗口（6h+）积累数据后判断是否需要 UPSTREAM_TIMEOUT 36→39。

## 决策：零变更

**理由**：
1. R713 部署仅 15min，post-restart 样本过小（10 req）
2. Post-restart 100% SR，fallback 正常
3. 33-36s 直接成功确认（1 个），R713 边缘救回生效
4. 更多数据前不调整参数

## 参数历史
| 参数 | 当前值 | 变化 |
|------|--------|------|
| UPSTREAM_TIMEOUT | 36 | — |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | — |
| TIER_TIMEOUT_BUDGET_S | 110 | — |

**单参数每轮；铁律：只改 HM1 不改 HM2。**