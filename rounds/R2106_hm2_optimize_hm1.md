# R2106 — HM2 优化 HM1

**时间**: 2026-07-21 02:00 UTC  
**作者**: opc2_uname (HM2)  
**目标**: HM1 (`opc_uname@100.109.153.83`)

## 数据收集

### 6h DB (nv_requests)
- **总量**: 36 req
- **成功**: 21 OK (58.3% SR)
- **失败**: 15 (8 zombie + 6 ATE + 1 IncRead)
- **429 循环**: 21/36 (58.3%) 有 key_cycle_429s, avg 2 cycles/req, 全部 glm5_2_nv

### 失败明细
| 错误类型 | 模型 | 数量 |
|---|---|---|
| zombie_empty_completion | glm5_2_nv | 8 |
| all_tiers_exhausted | dsv4p_nv | 6 (status=502) |
| NVStream_IncompleteRead | glm5_2_nv | 1 |

### 延迟 (成功请求)
| 模型 | 成功数 | avg_ms | min_ms | max_ms |
|---|---|---|---|---|
| glm5_2_nv | 18 | 23762 | 5628 | 119756 |
| dsv4p_nv | 3 | 12877 | 11822 | 14678 |

### Phantom ATE
- glm5_2_nv ATE rows: 6 条 status=200 (phantom, 非真实失败)

### Docker Logs (最近10min)
- dsv4p_nv pexec timeout: 3 次, 每次 ~20018ms, fastbreak 触发
- 全部 ATE 后 peer-fb 到 HM2 返回 502 (30-48ms)

### 当前配置
- KEY_COOLDOWN_S=73, TIER_COOLDOWN_S=68 → KEY+TIER=141
- TIER_TIMEOUT_BUDGET_S=153
- PEER_FALLBACK_TIMEOUT=122
- UPSTREAM_TIMEOUT=24

## 分析

核心问题: 58.3% 的请求有 key_cycle_429s (avg 2 次), 即 glm5_2_nv 在每个请求中平均 key 轮转 2 次, 每次轮转触发热冷却 73s。这导致:
1. 请求延迟显著上升 (avg 23762ms, max 119756ms)
2. 轮转过程中的 key 冷却不足 → zombie_empty_completion (8/15 失败)
3. 429→key 轮转→部分 key 未恢复→更多 429 的恶性循环

优化方向: +2s KEY_COOLDOWN_S (73→75) 给每个 key 更多恢复时间, 减少 429 概率, 降低 zombie 发生率。

KEY+TIER=75+68=143<153 BUDGET (10s margin), 安全。

## 执行

### 修改
- 参数: `KEY_COOLDOWN_S: "73"` → `"75"` (+2s)
- 位置: HM1 `/opt/cc-infra/docker-compose.yml` line 500 (nv_gw section)
- 方法: line-number-anchored sed

### 验证
- `docker exec nv_gw env`: KEY_COOLDOWN_S=75 ✓
- `curl /health`: status=ok ✓
- Line 186 (ms_gw KEY_COOLDOWN_S=58) 未改动 ✓

## 效果预期
- 减少 key_cycle_429s 次数 (每个 key 冷却 +2s → 更充分恢复)
- 降低 zombie_empty_completion 率
- 不影响成功路径延迟 (BUDGET 余量 10s 充足)
- 单参数, 铁律: 只改 HM1 不改 HM2

## ⏳ 轮到HM1优化HM2
