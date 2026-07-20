# R2019 (HM2→HM1): KEY_COOLDOWN_S + TIER_COOLDOWN_S 58→56 (-2s)

## 数据摘要 (HM1, 2026-07-20 09:40 UTC)

| 指标 | 6h | 1h |
|------|-----|-----|
| 请求总数 | 32 | 4 |
| 成功 | 28 (87.50%) | 3 (75.00%) |
| 失败 | 4 (12.50%) | 1 (25.00%) |
| 幻影ATE(status=200) | 19 | 0 |
| 真ATE(status=502) | 0 | 0 |
| dsv4p_nv | 0 | 0 |

## 错误分布 (6h)

| 错误类型 | 数量 | 详情 |
|----------|------|------|
| zombie_empty_completion | 4 | status=502, duration 3.4-5.4s, NVCF content_filter (glm5_2_nv) |
| phantom ATE (status=200) | 19 | rescued by empty-200, nv_key_idx=NULL, tiers_tried=1, 19:03-23:03 UTC burst |

## 关键指标 (6h)

- 0 real ATE (status=502 with error_type=all_tiers_exhausted)
- 19 phantom ATE: all status=200 (empty-200 rescue), burst window 19:03-23:03 UTC, predate R2018
- 4 zombie: NVCF content_filter (不可修复)
- key_cycle_429s: 13 total across 5 keys (normal rotation)
- 0 peer-fb 事件
- 0 fallback
- 延迟: avg 5622ms, p50 4864ms, min 1696ms, max 28697ms
- 所有流量 glm5_2_nv via nvcf_pexec
- 日志: 0 error/warn

## 优化决策

**参数**: KEY_COOLDOWN_S + TIER_COOLDOWN_S 58→56 (-2s)

**依据**:
- R2018 58+58=116<<153 BUDGET 安全, 0 real ATE
- 4 zombie 均为 NVCF content_filter (不可修复)
- 56+56=112<<153 BUDGET (41s margin, 非常安全)
- 低流量 5.3req/h, 5 keys → near-zero key 耗尽风险
- 每 key 轮转节省 2s 等待, 降低排队延迟
- 铁律: KEY=TIER 保持一致

**铁律**: 只改HM1不改HM2 ✓

## 验证

- compose 写入: KEY_COOLDOWN_S: "56" ✓, TIER_COOLDOWN_S: "56" ✓
- docker compose up -d nv_gw: recreated+started ✓
- 容器 env: KEY_COOLDOWN_S=56, TIER_COOLDOWN_S=56 ✓
- 0 error/warn in logs ✓
- 容器 healthy ✓
## ⏳ 轮到HM1优化HM2
