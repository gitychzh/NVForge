# R1681: HM2→HM1 — FASTBREAK 3→2 (-1 key) — zombie_empty_completion 3键浪费→2键, 省~9s/ATE

**决策**: 降 NVU_PEXEC_TIMEOUT_FASTBREAK 3→2。zombie_empty_completion 是 NVCF glm5.2 model-level 行为 (finish_reason=stop, content<50chars, input≥5000, no tool_calls), 非 key-specific。3 键尝试浪费第 3 键 ~9s 于已失败的 NVCF function, 2 键压缩 27s→18s 后快速退 tier。

## 数据摘要

### 6h 窗口 (2026-07-17 07:00~13:00 UTC)
| 指标 | 值 |
|------|-----|
| 总请求 | 30 |
| 成功 | 19 (63.3%) |
| 失败 | 11 |
| zombie_empty_completion | 11 (100% of failures) |
| all_tiers_exhausted | 0 |
| 429 rate limit | 0 |
| peer-fallback triggered | 0 |

### 1h 窗口
| 指标 | 值 |
|------|-----|
| 总请求 | 7 |
| 成功 | 5 (71.4%) |
| 失败 | 2 |
| zombie_empty_completion | 2 |

### 日志 Zombie 最新模式 (nv_gw --tail 100)
```
10:33: k2→k3→ZOMBIE (22s, 2 keys wasted)
11:03: k5→k1→k2→ZOMBIE (75s, 3 keys wasted)
11:33: k3→k4→k5→ZOMBIE (67s, 3 keys wasted)
12:03: k1→k2→ZOMBIE (20s, 2 keys wasted)
12:33: k3→k4→k5→k1→ZOMBIE (47s, 4 keys wasted)
13:03: k2→k3→k4→ZOMBIE (41s, 3 keys wasted)
```

### cc4101 日志
低流量, 1 req/100 lines, stream=200 OK (非 zombie 路径, 小 context 请求)

### DB 最近 10 条
- 4 zombie (502, ~4.5-27s), 6 成功 (200, ~4.3-12.5s)
- 全部 tiers_tried_count=1, fallback_occurred=false
- 无 peer-fallback, 无 ms_gw 回退

## 修改详情

| 参数 | 旧值 | 新值 | 理由 |
|------|------|------|------|
| NVU_PEXEC_TIMEOUT_FASTBREAK | 3 | 2 | zombie 是 NVCF model-level, 3 键浪费第 3 键 ~9s; 2 省 ~9s/ATE, 快速退 tier |

## 约束检查
- Budget: 2×9+66=84 < 120 ✓
- glm5_2 + peer-fb: 120 + 72 = 192 < 195 ✓
- dsv4p_nv + peer-fb: 70 + 72 = 142 < 195 ✓
- KEY=TIER=55 铁律: ✓
- PEER_FALLBACK_TIMEOUT=72 ≥ HM2 BUDGET=70+2 ✓

## 验证
```
docker exec nv_gw env | grep FASTBREAK
→ NVU_PEXEC_TIMEOUT_FASTBREAK=2 ✓
```

## 铁律验证
- ✅ 只改HM1: 仅修改 HM1 compose + 重启 nv_gw
- ✅ 改前必有数据: 6h+1h DB + 日志 zombie 模式
- ✅ 改后必有验证: docker exec env 确认
- ✅ 聚焦 nv_gw: 仅 nv_gw 容器 env
- ✅ 所有修改写入仓库: 本轮 commit
## ⏳ 轮到HM1优化HM2
