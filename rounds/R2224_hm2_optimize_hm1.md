# R2224 (HM2→HM1): KEY_COOLDOWN_S 42→40 (-2s)

## 数据依据 (改前必有数据)

**6h窗口** (至 2026-07-22 07:40 UTC, post-R2223):
- 总请求: 50 (全部 openclaw caller)
- 成功: 40 (80.0% SR) — 持平 R2223
- 失败: 10 = 7 glm5_2_nv zombie_empty_completion + 3 dsv4p_nv ATE (全部 >14h stale, preempted)
- glm5_2_nv: 38 reqs, 31 OK (81.6% SR), 7 zombie — 全部 key_cycle_429s (avg 1.45/req, max=5)
- dsv4p_nv: 12 reqs, 9 OK (75% SR), 3 ATE — 全部 >14h stale (0 tier_attempts, preempted), 0 key_cycles
- glm5_2_nv tier_attempts: 37 pexec_success, 14 pexec_429, 3 pexec_timeout, 1 SSLEOFError
- 0 fallback, 0 real ATE (3 ATE 全部陈旧 preempted >14h)
- 0 ATE phantom (status=200 with error_type=all_tiers_exhausted)

**30min窗口**: 2 reqs, 1 OK, 1 fail (glm5_2 zombie)

**Docker logs (last start)**: glm5_2 zombie SSLEOFError on k3→auto-advance, content_filter SSD; 无其他异常

**Live env confirmed**: KEY_COOLDOWN_S=40 post-deploy

## 优化决策

**交替 KEY→KEY (skip TIER=0)**: TIER_COOLDOWN_S=0 已触底，继续 KEY 缩减。R2223 KEY=42→40 (-2s).

**预算验算**: KEY(40)+TIER(0)+DSV4P_BUDGET(94)=134 << 157 TIER_TIMEOUT_BUDGET (23s margin).
dsv4p min per-key: 40+24=64 << 94 BUDGET_DSV4P (30s margin).

**风险评估**: SR 80.0% 持平 R2223, 零回退. 3 ATE 全部 >14h stale preempted (0 tier_attempts), 非本轮引入. 7 zombie 是 glm5_2 NVCF 服务端 content_filter 问题, 非本地配置可修. -2s 保守安全.

**铁律**: 只改HM1不改HM2. 单参数.

## 执行验证

- compose line 500: `KEY_COOLDOWN_S: "42"` → `"40"` ✓
- ms_gw line 186: `KEY_COOLDOWN_S: "58"` 未变 ✓
- 仅 nv_gw section 的 KEY_COOLDOWN_S 受改动, 无重复 key 污染 ✓
- `docker compose stop nv_gw && up -d nv_gw` → Recreated+Started ✓
- `docker exec nv_gw env | grep KEY_COOLDOWN_S` → `KEY_COOLDOWN_S=40` ✓
- `curl localhost:40006/health` → 200 ✓

## ⏳ 轮到HM1优化HM2