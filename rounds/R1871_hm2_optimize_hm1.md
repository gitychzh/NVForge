# R1871 (HM2→HM1): NOP — 全NVCF侧zombie, 零重启后数据, 参数已达保守位置

## 改前数据 (2026-07-19 09:40 CST, HM1 6h window)

### 整体成功���
- **6h**: 13 OK / 37 total = **35.1% SR** (24 fail)
- **dsv4p_nv**: 3/3 OK (100%) — 干净
- **glm5_2_nv**: 10/34 OK (29.4%) — 重度退化

### 错误分类 (24条, 100% glm5_2_nv)
| error_type | count | 可配置? |
|---|---|---|
| zombie_empty_completion | 24 | ❌ NVCF侧 |

### 关键指标
- **ATE**: 3条 phantom ATE (status=200, tiers_tried=1, 非真失败) — 0条真ATE (status=502)
- **key_cycle_429s**: glm5_2_nv 33×1cycle + 1×2cycle — 近乎每请求都触429
- **fallback**: 0 fallback occurred (37条全f)
- **tier attempts**: pexec_success 45, pexec_429 1 (仅1条成功进入tier层)
- **durations**: glm5_2 OK avg 6620ms (1916-14181), dsv4p OK avg 9381ms (4480-14501)

### 容器状态
- **nv_gw**: running, healthy, started 2026-07-19T01:37:41Z (R1870 deploy后重启, ~8h前)
- **日志**: clean, 无error/warn, 仅startup banner
- **重启后请求**: 0条 (最近5min DB零请求)

### 环境确认
- KEY_COOLDOWN_S=46, TIER_COOLDOWN_S=46 (R1870部署)
- UPSTREAM_TIMEOUT=49, TIER_TIMEOUT_BUDGET_S=178
- 46+46=92 << 178 BUDGET safe
- HM2 KEY=25 证明46仍保守

## 分析

24条错误全为 `zombie_empty_completion` → 100% NVCF侧glm5_2函数退化, 非本地配置可修。与R1870及之前多轮同构(glm5_2 NVCF DEGRADING持续)。dsv4p_nv 3/3干净, 非proxy层问题。

key_cycle_429s 34条/37请求 = 91.9%触发率 → NVCF glm5_2函数端限流严重, 每个请求都触429然后key轮转。KEY_COOLDOWN=46仍远低于zombie发生前的NVCF窗口(60s), 但zombie本身是函数端问题非cooldown可解。

**介入触发条件全不满足:**
- SR 35.1% 远低于93%连续触发线, 但全为NVCF侧zombie, 非本地config可修
- fallback 0, 无真ATE(status=502), 无新错误分类
- 零重启后数据, 无法验证R1870效果
- 参数已处保守位置(KEY=TIER=46, UPSTREAM=49, BUDGET=178)

→ **NOP** — 硬改违反铁律。等待glm5_2 NVCF函数恢复 + 积累重启后数据。

## 结论

NOP轮。0改HM1, 0改HM2。下轮R1872盯: glm5_2 zombie是否消退, 重启后SR是否回升, 若有新数据可考虑微调。

## ⏳ 轮到HM1优化HM2
