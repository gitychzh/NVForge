# R2265 (HM2→HM1): KEY_COOLDOWN_S 48→42

## 数据快照 (6h window)
- 56 requests, 40 OK (71.4% SR), 16 failures
- glm5_2_nv: 42 req/30 OK, 7 ATE + 5 zombie = 12 failures (28.6%)
- dsv4p_nv: 14 req/10 OK, 3 ATE + 1 zombie = 4 failures (28.6%)
- ALL 10 ATE failures have **0 tier_attempts** — pre-empted, never attempted a key
- glm5_2_nv key cycling: 35.7% of requests hit 2+ key cycles (429 storms)

## 根因分析
KEY_COOLDOWN_S=48 is too long. When all 5 keys hit 429 in rapid succession (35.7% cycle2+ rate), they're all in cooldown simultaneously. The gateway waits for cooldown to clear but FASTBREAK=1 cannot rescue — budget is consumed by waiting, producing 0-tier_attempts ATE. PER_KEY=72s, ratio 1.39 at budget=100 gives only 1.39 key cycles, insufficient when all keys are stuck.

## 优化
- **KEY_COOLDOWN_S**: 48 → 42 (single param, -6s)
- 减少6s cooldown让key更快恢复可用, 降低all-keys-cooldown窗口概率
- 保守微调, 避免过度激进引发429雪崩
- 新ratio: 42+30=72, budget=100, ratio=100/72=1.39 (unchanged per-key, but keys recover faster)

## 全局检查
- Global: 48+5+100=153 < 192 ✓ (TIER_TIMEOUT_BUDGET_S)
- PER_KEY: 42+30=72s, budget 100, ratio 1.39
- 铁律: 只改HM1, 绝不改HM2

## ⏳ 轮到HM1优化HM2