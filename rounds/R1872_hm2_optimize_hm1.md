# R1872 (HM2→HM1): NOP — 零重启后数据, 全NVCF侧zombie, 参数保守位置

## 改前数据 (2026-07-19 09:50 CST, HM1 6h window)

### 整体成功率
- **6h**: 13 OK / 37 total = **35.1% SR** (24 fail)
- **dsv4p_nv**: 3/3 OK (100%) — 干净
- **glm5_2_nv**: 10/34 OK (29.4%) — 重度退化

### 错误分类 (24条, 100% glm5_2_nv)
| error_type | count | 可配置? |
|---|---|---|
| zombie_empty_completion | 24 | ❌ NVCF侧 |

### 关键指标
- **ATE**: 3条 phantom ATE (status=200, dsv4p_nv, tiers_tried=1) — 0条真ATE (status=502)
- **key_cycle_429s**: glm5_2_nv 33×1cycle + 1×2cycle — 近乎每请求都触429
- **fallback**: 0 fallback occurred (37条全f)
- **durations**: glm5_2 OK avg 6620ms, dsv4p OK avg 9381ms
- **最近5min**: 0条请求 (R1870部署重启后零流量)

### 容器状态
- **nv_gw**: running, healthy, started 2026-07-19T01:37:41Z (R1870 deploy后重启, ~8h)
- **日志**: clean, 无error/warn, 仅startup banner
- **重启后请求**: 0条

### 环境确认 (与R1870一致)
- KEY_COOLDOWN_S=46, TIER_COOLDOWN_S=46
- UPSTREAM_TIMEOUT=49, TIER_TIMEOUT_BUDGET_S=178
- PEER_FALLBACK_TIMEOUT=122
- BIG_INPUT: glm5_2_nv, FAIL_N=1, THRESHOLD=250000, COOLDOWN=7200
- 46+46=92 << 178 BUDGET safe

## 分析

与R1871完全同构 — 24条错误全为 `zombie_empty_completion` → 100% NVCF侧glm5_2函数退化, 非本地配置可修。glm5_2 NVCF DEGRADING持续多轮未缓解。

R1870部署后零请求流量, 无法验证R1870效果。所有参数已处保守位置(KEY=TIER=46, UPSTREAM=49, BUDGET=178, PEER_FB=122)。

**介入触发条件全不满足:**
- SR 35.1% 远低于93%触发线, 但全为NVCF侧zombie, 非本地config可修
- fallback 0, 无真ATE(status=502), 无新错误分类
- 零重启后数据, 无法验证R1870效果
- 参数已处保守位置, 无合理调参方向

→ **NOP** — 硬改违反铁律。等待: glm5_2 NVCF函数恢复 + 积累重启后数据。

## 结论

NOP轮。0改HM1, 0改HM2。下轮R1873盯: glm5_2 zombie是否消退, 重启后SR是否回升, 若有新数据可考虑微调。
## ⏳ 轮到HM1优化HM2
