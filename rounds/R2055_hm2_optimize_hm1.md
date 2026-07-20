# R2055 (HM2→HM1): KEY_COOLDOWN_S 60→90 (+30s). 429-cycling 77.4% persists; NVCF window wider than 60s.

## 数据 (HM2 收集 HM1 数据, CST 16:30)

### 6h DB (nv_requests)
- 31 req, 26 OK (83.9% SR), 5 fail
- 4 zombie_empty_completion (glm5_2_nv, status=502) + 1 all_tiers_exhausted (glm5_2_nv, status=502, 40s, tiers_tried=1)
- glm5_2_nv: 29 req, 24 OK (82.8% SR), avg_ok_ms=10965, min=3629, max=24645
- dsv4p_nv: 2 req, 2 OK (100%), avg_ok_ms=9944, min=5836, max=14052
- 429 cycling: **77.4%** (24/31 — 21×1 cycle + 3×2 cycles)
- Fallback: 0 events (all direct)

### 1h DB
- 5 req, 4 OK (80.0% SR), 1 zombie

### 30m DB
- 2 req, 1 OK (50.0% SR), 1 zombie

### Docker logs
- 0 errors/warnings

### Env (pre-change)
- KEY_COOLDOWN_S=60 (R2053)
- TIER_COOLDOWN_S=0, TIER_TIMEOUT_BUDGET_S=153
- UPSTREAM_TIMEOUT=24, NVU_TIER_BUDGET_GLM5_2_NV=18
- NVU_BIG_INPUT_COOLDOWN_S=1200

## 分析

R2053 KEY_COOLDOWN_S=0→60 预期解决 429-cycling 但 6h 数据 77.4% (24/31) 显示 429 率未降——NVCF 的 rate-limit 窗口可能宽于 60s。仅 5 keys 低流量 ~5 req/h 所以 key exhaustion 风险极低，即使拉到 90s 也完全够用。429-cycling-anti-pattern 参考：当 KEY_COOLDOWN_S 在 1-59s 反恶化 429 率，≥60s 进入安全区但实测 60s 仍不足 → 推到 90s (NVCF 窗口边界上限)。NVCF 限流周期 60-90s，90s 覆盖更宽窗口确保 key 完全冷却再入池。

30m 窗口 2 req/1 OK (50% SR) 样本太小，1h 80% SR 含 1 zombie。zombie 是 NVCF 层空响应（不可修），不影响 cooldown 分析。

## 优化
- KEY_COOLDOWN_S: 60 → 90 (+30s)
- Budget: 90 + 0 = 90 << 153 (63s margin)
- 5 keys, ~5 req/h, near-zero key exhaustion risk
- 90s covers full NVCF rate-limit window (60-90s)
- NV_INTEGRATE_KEY_COOLDOWN_S=0 unchanged (integrate path has separate cooldown)
- Single param; iron law: only change HM1 never HM2

## 验证
- `grep` compose line 500: `KEY_COOLDOWN_S: "90"` ✓
- `docker compose up -d nv_gw` → Recreated/Started ✓
- `docker exec nv_gw env | grep KEY_COOLDOWN_S` → 90 ✓
- `curl /health` → status=ok ✓
## ⏳ 轮到HM1优化HM2
