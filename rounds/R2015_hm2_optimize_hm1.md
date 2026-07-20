# R2015 (HM2→HM1): KEY_COOLDOWN_S + TIER_COOLDOWN_S 62→60 (-2s)

## 数据摘要 (HM1, 2026-07-20 09:20 UTC)

| 指标 | 6h | 30min |
|------|-----|-------|
| 请求总数 | 32 | 2 |
| 成功 | 29 (90.63%) | 2 (100.00%) |
| 失败 | 3 (9.38%) | 0 (0.00%) |
| dsv4p_nv | 0 | 0 |

## 错误分布 (6h)

| 错误类型 | 数量 | 详情 |
|----------|------|------|
| zombie_empty_completion | 3 | status=502, duration 3.4-4.9s, NVCF content_filter (glm5_2_nv) |
| phantom ATE (status=200) | 21 | 非真实失败, 网关已交付200 |

## 关键指标 (6h)

- key_cycle_429s: 11/32 (34.4%) — R2008 60→62 未降低429率
- 0 real ATE (status=502)
- 0 peer-fb 事件
- 0 fallback
- 延迟: avg 5598ms, min 1696ms, max 28697ms
- 所有流量 glm5_2_nv

## 日志 (最近100行)

无 error/warn — 仅有2条 ATTEMPT 日志 (09:03:20 k5 timeout=20s, 09:03:25 k1 timeout=20s)

## 优化决策

**参数**: KEY_COOLDOWN_S + TIER_COOLDOWN_S 62→60 (-2s)

**依据**:
- R2008 将 KEY=TIER 从 60→62 试图降低 429 率, 但 6h 429 率仍 34.4% — 无效改动
- 429 根本原因是 NVCF 服务端行为, 本地 cooldown 62 vs 60 无差异
- 回退到 60 节省 2s 每次 key 轮转等待, 降低排队延迟
- 铁律: KEY=TIER 保持一致
- PB 约束: 60+60=120 << 153 BUDGET (33s margin, 非常安全)
- 3 zombie 均为 NVCF content_filter (不可修复), 无其他错误类型

**铁律**: 只改HM1不改HM2 ✓

## 验证

- compose 写入: KEY_COOLDOWN_S: "60" ✓, TIER_COOLDOWN_S: "60" ✓
- docker compose up -d nv_gw: recreated+started ✓
- 容器 env: KEY_COOLDOWN_S=60, TIER_COOLDOWN_S=60 ✓
- /health: `{"status": "ok"}` ✓
- 无 drift 风险 (容器 env 与 compose 一致) ✓
## ⏳ 轮到HM1优化HM2
