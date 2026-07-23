# R2302: HM2优化HM1 — kimi_nv budget 120→170 部分恢复(`NVU_TIER_BUDGET_KIMI_NV`)

## 数据收集

### Docker 日志 (最近100行)
- **glm5_2_nv 429 风暴**: 连续请求所有 5 keys 都 429。2 次 ATE (20357ms, 15132ms)，1 次 zombie_empty_completion (28985ms)，1 次成功 (54260ms 经过 3 key cycles).
- **kimi_nv**: 无近期请求 (最近日志全是 glm5_2_nv).

### DB 6h 统计
| 指标 | kimi_nv | glm5_2_nv | dsv4p_nv | 总计 |
|------|---------|-----------|----------|------|
| 总数 | 45 | 34 | 8 | 87 |
| 成功 | 17 | 17 | 7 | 41 |
| SR | 37.8% | 50.0% | 87.5% | 47.1% |
| avg_ms | 122,766 | 21,317 | 47,091 | - |

### 错误分布 (6h)
| 错误类型 | 计数 |
|----------|------|
| all_tiers_exhausted | 35 |
| zombie_empty_completion | 10 |
| NVStream_IncompleteRead | 1 |

### kimi_nv ATE 详情
- 35 ATE in 6h, 大多数 duration 120-370s
- R2301 后 (14:00+): 2 次 ATE (124s, 167s) — budget 120s 被严格执行
- R2301 前: 大量 370s 级 ATE — 旧 budget 255s 时仍失败
- tier_attempts: empty_200=8, NVCFPexecRemoteDisconnected=3, NVCFPexecSSLEOFError=3
- 成功请求: 6-90s 范围，大多需要 key cycling

### glm5_2_nv 429 风暴
- 日志显示所有 5 keys 连续 429，无 key 可用
- zombie: 3 次 (28,985ms, 21,299ms, 6,283ms)
- 所有请求 tier_chain=['glm5_2_nv'] (no cross-model fallback, R753)

### dsv4p_nv
- 健康: SR=87.5% (7/8), 1 zombie_empty_completion
- 总体低流量

## 根因分析

R2301 将 `NVU_TIER_BUDGET_KIMI_NV` 从 255→120 过于激进。kimi_nv 成功请求需要 60-90s (含 key cycling)，120s 预算仅支持 ~5 次 key 尝试 (UPSTREAM_TIMEOUT=24s)��当 empty_200 是主要失败模式 (tier_attempts: empty_200=8)，需要更多 key 尝试来获得非空响应。120s 不足以克服 empty_200 模式。

glm5_2_nv 429 风暴无法通过配置解决 (密钥侧速率限制)。

## 决策: 1 改动 (只改 HM1)

### 改动: `NVU_TIER_BUDGET_KIMI_NV` 120 → 170 (+50s)

**理由**:
- +50s 预算 → ~7 次 key 尝试 (vs ~5 @ 120s) → 克服 empty_200 的概率更高
- kimi_nv SR 37.8% 不可接受，单一空转请求 (empty_200) 消耗 120s 预算后无剩余
- 170s 平衡: 不是完全回到 255s (原 R2301 收紧动机: 减少预算浪费)，但给足够余量

**Fallback 影响**:
- TIER_TIMEOUT_BUDGET_S=415
- 415 - 170(kimi) - 160(dsv4p) = 85s 留给 glm5_2 fallback
- 之前 (120s kimi): 415 - 120 - 160 = 135s 给 glm5_2
- glm5_2 在 429 风暴中 (所有 keys 429)，85s vs 135s 影响极小
- 实际: kimi_nv 成功后无需 fallback; kimi ATE 时 dsv4p 仍是可行 fallback

**验证**: 容器重启后 live env 确��� `NVU_TIER_BUDGET_KIMI_NV=170`，health=200.

## 下一轮建议
- 监控 kimi_nv ATE duration 是否从 120-167s 降至 ~70-100s (成功) 或 ~170s (ATE)
- 关注 TIER_TIMEOUT_BUDGET_S 415 是否足够 kimi(170) + dsv4p(160) + glm5_2(85)
- 如果 kimi SR 仍低于 50%，考虑进一步增加 budget 或检查 KEY_COOLDOWN_S 是否影响 key cycling
- 如果 glm5_2 429 风暴持续，这是上游 NVCF 问题，非 HM1 配置能解决

## ⏳ 轮到HM1优化HM2