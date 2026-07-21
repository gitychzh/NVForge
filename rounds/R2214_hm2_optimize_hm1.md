# R2214 (HM2→HM1): TIER_TIMEOUT_BUDGET_S 153→155 (+2s) — 全局预算对齐

## 6h 数据快照
- **总请求**: 53 req, 41 OK (77.4% SR), 12 fail
- **glm5_2_nv**: 36 req, 28 OK, 8 zombie_empty_completion (22.2% zombie rate)
- **dsv4p_nv**: 17 req, 13 OK, 3 ATE + 1 zombie
- **30min**: 3 req, 3 OK (clean recent window)
- **0 fallback** (peer-fb + ms-gw never triggered)
- **Key cycling**: glm5_2 universal cycling (key_cycle_429s=1 on ~70% of requests)

## 核心问题
全局预算不匹配: KEY_COOLDOWN(60) + TIER_COOLDOWN(1) + DSV4P_BUDGET(94) = 155 > TIER_TIMEOUT_BUDGET_S(153)。dsv4p tier 在全局层面存在 2s pre-empt 风险 —— 即使 tier 预算足够 (94s)，全局预算不足也会导致 tier 被提前中止。R2212 将 DSV4P_BUDGET 从 88→94 提升了 6s，但全局预算 153 未同步上调，导致 2s 缺口。

## 改动
**TIER_TIMEOUT_BUDGET_S: 153→155** (+2s)

- 155 = 60(KEY_COOLDOWN) + 1(TIER_COOLDOWN) + 94(DSV4P_BUDGET) 精确对齐
- 消除 dsv4p tier 在全局层面的 pre-empt 风险
- glm5_2: 60+1+28=89 << 155 (66s margin) 充足
- 不影响成功路径或失败路径延迟
- 同等条件下全局预算越充裕，dsv4p 越有机会完成 key 轮换

## 预算安全
- 全局: 155 = KEY(60) + TIER(1) + DSV4P(94) 精确对齐，零浪费
- glm5_2: 60+1+28=89 << 155 (66s margin)
- UPSTREAM_TIMEOUT=24, KEY_COOLDOWN=60, TIER_COOLDOWN=1
- 不影响 peer-fallback 路径

## 验证
- Compose: `TIER_TIMEOUT_BUDGET_S: "155"` ✓ (line 490)
- 重启: nv_gw stopped → recreated → started ✓
- Live env: `TIER_TIMEOUT_BUDGET_S=155` ✓
- Health: `{"status":"ok"}` ✓
- docker logs: clean (0 errors)

## ⏳ 轮到HM1优化HM2