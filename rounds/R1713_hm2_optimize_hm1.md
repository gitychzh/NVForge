# R1713: HM2→HM1 — BIG_INPUT breaker: FAIL_N 3→1, COOLDOWN 60→1800

## 数据 (6h window, 2026-07-17 10:33–16:42 UTC)

- 59 requests: 49 OK (83.1%), 10 zombie_empty_completion (16.9%), 0 ATE, 0 fallback
- 100% key_cycle_429s: 55/59 cycle=1, 4/59 cycle=2 — k1/k4 share egress IP 134.195.101.193
- 10 zombies: all glm5_2_nv, all >250K chars (284K-315K), all openclaw, 4.9-13.4s, ~30 min cadence
- Success: avg 13.4s, min 4.0s, max 51.8s
- cc4101: 正常, no errors
- peer-fallback: 0 triggered (no ATE, zombies caught by zombie detection not fallback)

## 根因分析

R1712 KEY_COOLDOWN/TIER_COOLDOWN 70→60 未能降低 429 率 (100%→100%)。k1/k4 共享出口 IP 134.195.101.193 是 429 唯一瓶颈, per-key cooldown 对此无效。

BIG_INPUT breaker (R1695) 设 FAIL_N=3 + COOLDOWN=60s, 但 10 个 zombie 间隔 ~30 min, breaker 在 60s 后自动关闭, 下个 zombie 来临时 breaker 已 CLOSED → 0% 命中率。FAIL_N=3 要求 3 次连续失败, 但 zombie 是间隔 30 min 的单次事件, 永不累积到 3。

## 优化

**NVU_BIG_INPUT_FAIL_N 3→1 (-2), NVU_BIG_INPUT_COOLDOWN_S 60→1800 (+1740s)**

FAIL_N=1: 第一个 zombie trigger breaker OPEN。COOLDOWN=1800s=30min: 匹配 zombie 30 min 间隔, 保持 breaker OPEN 到下一个 zombie 来临时, 直接返回 all_tiers_exhausted 跳过 pexec 尝试 → 省 5-13s/zombie。成功路径 unaffected (zombie 只出现在 >250K chars, 正常请求不走此路径)。

## 验证

- `docker exec nv_gw env`: FAIL_N=1, COOLDOWN=1800, THRESHOLD=250000 ✓
- `curl localhost:40006/health`: {"status":"ok"} ✓
- Restart: Container nv_gw Recreated+Started ✓

## 铁律
只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
