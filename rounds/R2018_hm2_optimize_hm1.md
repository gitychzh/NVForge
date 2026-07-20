# R2018 (HM2→HM1): KEY_COOLDOWN_S + TIER_COOLDOWN_S 60→58 (-2s)

## 数据摘要 (HM1, 2026-07-20 09:30 UTC)

| 指标 | 6h | 1h |
|------|-----|-----|
| 请求总数 | 32 | 4 |
| 成功 | 29 (90.63%) | 3 (75.00%) |
| 失败 | 3 (9.38%) | 1 (25.00%) |
| dsv4p_nv | 0 | 0 |

## 错误分布 (6h)

| 错误类型 | 数量 | 详情 |
|----------|------|------|
| zombie_empty_completion | 3 | status=502, duration 4.1-4.9s, NVCF content_filter (glm5_2_nv) |

## 关键指标 (6h)

- 0 real ATE (status=502)
- key_cycle_429s: 4/4 (1h), present on all success requests — normal key rotation
- 0 peer-fb 事件
- 0 fallback
- 延迟: avg 5598ms, min 1696ms, max 28697ms
- 所有流量 glm5_2_nv via nvcf_pexec
- 日志: 0 error/warn

## 优化决策

**参数**: KEY_COOLDOWN_S + TIER_COOLDOWN_S 60→58 (-2s)

**依据**:
- R2017 60+60=120<<153 BUDGET 安全, 0 real ATE
- 3 zombie 均为 NVCF content_filter (不可修复)
- 58+58=116<<153 BUDGET (37s margin, 非常安全)
- 低流量 5.3req/h, 5 keys → near-zero key 耗尽风险
- 每 key 轮转节省 2s 等待, 降低排队延迟
- 铁律: KEY=TIER 保持一致

**铁律**: 只改HM1不改HM2 ✓

## 验证

- compose 写入: KEY_COOLDOWN_S: "58" ✓, TIER_COOLDOWN_S: "58" ✓
- docker compose up -d nv_gw: recreated+started ✓
- 容器 env: KEY_COOLDOWN_S=58, TIER_COOLDOWN_S=58 ✓
- 0 error/warn in logs ✓
- 容器 healthy ✓
## ⏳ 轮到HM1优化HM2