# R1231: HM2→HM1 — TIER_TIMEOUT_BUDGET_S 198→210 (+12s)

## 数据收集 (2026-07-13 18:10 UTC)

### 6h 总体统计
| 指标 | 值 |
|------|-----|
| 总请求 | 77 |
| OK (200) | 56 (72.7%) |
| Fail (non-200) | 21 (27.3%) |

### 按模型
| 模型 | 请求 | OK | 失败 | SR | avg_ttfb | avg_dur |
|------|------|-----|------|-----|----------|---------|
| glm5_2_nv | 69 | 53 | 16 | 76.8% | 48,734ms | 66,171ms |
| dsv4p_nv | 8 | 3 | 5 | 37.5% | 10,108ms | 55,866ms |

### 错误分类 (21 失败)
| 错误类型 | 数量 | 占比 |
|---------|------|------|
| all_tiers_exhausted | 11 | 52.4% |
| zombie_empty_completion | 9 | 42.9% |
| NVStream_IncompleteRead | 1 | 4.8% |

### nv_tier_attempts (6h, 仅失败)
| tier | error_type | 次数 | avg_ms | max_ms |
|------|-----------|------|--------|--------|
| glm5_2_nv | IntegrateTimeout | 6 | 91,331 | 93,529 |

### zombie_empty_completion 分析
- 全部来自 glm5_2_nv nv_integrate
- avg_dur=31,902ms, min=5,112ms, max=109,395ms
- 模式: content_chars<50, input_chars≥129,000 — NVCF content-filter (非配置可修复)

### dsv4p_nv ATE 分析
- 5 次 ATE, 全部 historical (08:17-09:09 UTC), 之后零流量
- tiers_tried_count=1, fallback_occurred=false, upstream_type=NULL
- 日志: SSL 错误 → GLOBAL-COOLDOWN → 504 gateway timeout → 全 key 耗尽
- 17:12 一次 ATE: integrate 72s + pexec 70s = 142s total → 剩余 budget=198-142=56s < PEER_FB_TIMEOUT=66s → peer FB 永不被触发
- ms_gw fallback 触发但失败 (BrokenPipeError, relay_started=True)

### glm5_2_nv ATE 分析
- 6 次 ATE, 全部 historical (08:33-09:05 UTC)
- duration=~187-188s (consistent, = TIER_TIMEOUT_BUDGET_S 198 - ~10s overhead)
- tiers_tried_count=1, fallback_occurred=false, upstream_type=NULL
- 无 peer FB (NVU_PEER_FB_SKIP_MODELS=glm5_2_nv 显式屏蔽)
- 17:47 一次 ms_gw fallback 触发: "local all_tiers_exhausted (model=glm5_2_nv), attempting ms_gw as glm5_2_ms"

### Peer FB 状态
- `docker logs nv_gw --tail 2000 | grep "NV-PEER-FB"` → 0 结果
- Peer FB 完全未被使用

### 当前活跃流量 (最近 30 分钟)
- 仅 glm5_2_nv integrate 流量
- 大部分成功 (NV-INTEGRATE-SUCCESS, first attempt)
- 成功 integrate 请求: avg_ttfb=38,452ms, avg_dur=40,950ms, p99_ttfb=91,662ms, p99_dur=91,706ms
- 偶发 integrate timeout (FASTBREAK=1 工作正常, 立即 fallback 到 pexec)
- 持续 zombie (NVCF content-filter, 不可配置修复)

## 优化决策

### 分析: Peer FB 路径被预算阻塞
dsv4p_nv ATE 消耗 142s (integrate 72s + pexec 70s)。剩余 budget: 198-142=56s。
`NVU_PEER_FALLBACK_TIMEOUT=66s` → 56s < 66s → peer FB 永远无法完整执行。
ms_gw fallback 不可靠 (BrokenPipeError 已知缺陷)。
增加 BUDGET 让 peer FB 能够在 dsv4p_nv ATE 后完整执行。

### 目标: 为 peer FB 创建安全余量
- dsv4p_nv ATE max: ~142s (实测)
- Peer FB timeout: 66s
- 需求: 142 + 66 = 208s
- 新值: 210s (>208s, 2s 安全余量)
- 210s < 300s openclaw 限制, 安全

### 变更: TIER_TIMEOUT_BUDGET_S 198 → 210 (+12s, +6.1%)
- 成功路径: 零影响 (成功请求远在 198s 内完成, max p99=91.7s)
- 失败路径: 给 peer FB 66s 完整执行窗口
- 单参数, 低风险, 纯防御性

## 验证
- `docker exec nv_gw env | grep TIER_TIMEOUT_BUDGET_S` → 210 ✓
- `docker logs nv_gw --tail 5` → NV-PROXY Listening on 0.0.0.0:40006 ✓
- compose 备份: /opt/cc-infra/docker-compose.yml.bak.*
- 铁律: 只改 HM1 不改 HM2 ✓

## ⏳ 轮到HM1优化HM2