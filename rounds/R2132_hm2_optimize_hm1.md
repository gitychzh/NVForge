# R2132 (HM2→HM1): TIER_COOLDOWN_S 56→54 (-2s)

## 数据收集

### 6h 窗口 (20:33-02:33 UTC, 2026-07-21)
- **总请求**: 33 req / 24 OK (72.7% SR) / 9 zombie / 0 ATE / 0 fallback
- **全量模型**: glm5_2_nv (openclaw) — 无 dsv4p_nv/kimi_nv 请求
- **OK 延迟**: avg 8752ms, min 2874ms, max 20254ms
- **key_cycle_429s**: 33/33 请求均为 1 (正常key轮转，非问题)
- **fallback**: 0/33 = 无 fallback 触发

### 错误分析
- **zombie_empty_completion × 9**: glm5_2_nv, 间隔 ~30min, 持续时间 3.6-11.6s
  - 均为 NVCF 侧空响应，非配置可修复
  - 时间分布: 18:33, 19:03, 19:33, 20:03, 20:33, 21:03, 21:34, 22:03, 22:33
- **ATE**: 0 — R2131 TIER_COOLDOWN_S=58→56 成功消除 ATE (9→0)

### 30min 窗口
- 3 req / 3 OK (100% SR) / 0 error — 干净

### 两端 env 对比
| 参数 | HM1 (本次改前) | HM2 |
|------|---------------|-----|
| TIER_COOLDOWN_S | 56 | 56 (未改) |
| KEY_COOLDOWN_S | 66 | 66 |
| UPSTREAM_TIMEOUT | 24 | 24 |
| TIER_TIMEOUT_BUDGET_S | 153 | 153 |
| MIN_OUTBOUND_INTERVAL_S | 0 | 0 |

## 优化决策

**决策**: TIER_COOLDOWN_S 56→54 (-2s)

**依据**:
1. R2131 已证明 TIER_COOLDOWN_S=58 消除 ATE (9→0)，56 延续 0 ATE
2. KEY+TIER=66+54=120 < 153 BUDGET (33s margin)，充分安全
3. 低流量 (5.5 req/h)，5 key 资源充足，cooldown 压缩风险极低
4. 继续 R2131 的 cooldown 压缩轨迹，提升 fallback 链可用性

**单参数，铁律**: 只改 HM1 不改 HM2

## 执行验证

- ✅ compose 修改: 行 505 TIER_COOLDOWN_S: "54"
- ✅ docker compose up -d nv_gw: 容器重建成功
- ✅ docker exec nv_gw env: TIER_COOLDOWN_S=54
- ✅ curl /health: {"status": "ok", "port": 40006}

## ⏳ 轮到HM1优化HM2
