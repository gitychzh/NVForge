# R2013 (HM2→HM1): NVU_TIER_BUDGET_GLM5_2_NV 22→20 (-2s)

## 数据摘要 (HM1, 2026-07-20 08:55 UTC)

| 指标 | 6h | 30min |
|------|-----|-------|
| 请求总数 | 32 | 2 |
| 成功 | 28 (87.50%) | 1 (50.00%) |
| 失败 | 4 (12.50%) | 1 (50.00%) |
| dsv4p_nv | 0 | 0 |

## 错误分布 (6h)

| 错误类型 | 数量 | 详情 |
|----------|------|------|
| zombie_empty_completion | 4 | status=502, duration 3.4-4.9s, NVCF content_filter (glm5_2_nv) |
| phantom ATE (status=200) | 21 | 非真实失败, 网关已交付200 |

## 日志 (最近100行)

仅有1条 zombie 告警: `08:33:29 [NV-UPSTREAM-ERROR-CHUNK] glm5_2_nv finish_reason=content_filter zombie=True`

## 关键参数 (HM1 live env)

- UPSTREAM_TIMEOUT=30
- TIER_TIMEOUT_BUDGET_S=153
- NVU_TIER_BUDGET_GLM5_2_NV=22 → **20** (本轮)
- NVU_TIER_BUDGET_DSV4P_NV=20
- NVU_PEER_FALLBACK_TIMEOUT=122
- PEER_FB_SKIP_MODELS=kimi_nv

## 优化决策

**参数**: NVU_TIER_BUDGET_GLM5_2_NV 22→20 (-2s)

**依据**:
- glm5_2_nv 真实 OK max=9201ms << 20s tier budget (10.8s headroom, 安全)
- 4个 zombie 均在 3.4-4.9s 内超时, 非 tier budget 耗尽触发的 ATE
- 0 peer-fb 事件: 僵尸在 tier exhaustion 之前就被检测到
- 节约 2s: 僵尸 tier-exhaustion 路径从 22s 缩短到 20s

**PB 约束检查**:
- UPSTREAM=30 + PEER=122 = 152 < BUDGET=153 ✓ (1s margin, strict <)
- 即使 glm5_2 也需要 peer-fb(非 skip), 20s 不影响

**铁律**: 只改HM1不改HM2 ✓

## 验证

- compose 写入: `NVU_TIER_BUDGET_GLM5_2_NV: "20"` ✓
- docker compose up -d nv_gw: recreated+started ✓
- 容器 env: `NVU_TIER_BUDGET_GLM5_2_NV=20` ✓
- /health: `{"status": "ok"}` ✓
## ⏳ 轮到HM1优化HM2
