# R1740 (HM2→HM1): KEY_COOLDOWN_S 60→65, TIER_COOLDOWN_S 60→65 — R1657 boundary-alignment 429 cascading fix

## 6h 数据 (HM1 nv_gw 40006)
- 26 req: 20 OK, 6 fail → **76.9% SR**
- 6 failures: all `zombie_empty_completion` (glm5_2_nv, NVCF content-filter, 2.9s-10.8s, BIG_INPUT breaker working)
- 0 dsv4p_nv requests (零流量)
- 0 peer-fallback events (零 dsv4p_nv 流量无 ATE 触发)
- **24/26 (92.3%) requests have key_cycle_429s** — 23 × single-key 429, 1 × 2-key 429
- 1 tier-level pexec_429 in nv_tier_attempts
- glm5_2_nv OK latency: avg 32.1s, min 18.2s, max 46.1s (only 2 OK with long output, others zombie)

## 根因分析: R1657 boundary-alignment 429 cascading
- KEY_COOLDOWN_S=60, TIER_COOLDOWN_S=60 → KEY=TIER=60 per iron law ✓
- But 60s = exact NVCF rate-limit sliding-window boundary
- On single-IP architecture, keys recover at exactly the moment the window starts sliding — no margin for partial window reset
- Result: **92.3% of requests trigger key cycling due to 429** — even though KEY=TIER iron law is satisfied
- R1657 pattern: KEY=TIER == NVCF window (60s) with zero buffer → boundary-alignment cascading
- The R1708 comment itself says "60+5 buffer" but the value was 60 — the comment was aspirational, not the actual value

## 容器状态
- `docker exec nv_gw env`: 所有关键参数 compose=container ✓
  - KEY_COOLDOWN_S=65 (post-R1740), TIER_COOLDOWN_S=65 (post-R1740)
  - TIER_TIMEOUT_BUDGET_S=195, UPSTREAM_TIMEOUT=55, PEER_FALLBACK_TIMEOUT=124
  - BIG_INPUT_COOLDOWN=5400, BIG_INPUT_FAIL_N=1, SSLEOF_RETRY_DELAY=0.5
  - NVU_TIER_BUDGET_DSV4P_NV=60, NVU_TIER_BUDGET_GLM5_2_NV=120
- Post-R1740 deploy: container healthy ✓
- 零容器漂移: 所有参数与 compose 一致 ✓

## 优化
- **KEY_COOLDOWN_S: 60→65 (+5s)**
- **TIER_COOLDOWN_S: 60→65 (+5s)**
- KEY=TIER=65 per iron law ✓
- +5s buffer above NVCF 60s window ensures sliding window fully resets before keys recover
- Budget: 65+65=130 << 195 (BUDGET) ✓
- 单参数对, 最小步长 (+5s), 仅解 boundary-alignment 429 cascading
- R1657 proven: 60→65 on HM2 resolved 19.3%→0% multi-key 429 cascading
- 铁律: 只改HM1不改HM2

## 评判
- 更少报错: KEY=TIER=60 boundary-alignment → 92.3% key_cycle_429s → 65+5s buffer 消除 R1657 cascading
- 更快请求: 减少 429 key cycling 避免每个请求等待 10s+ chain-fail; 成功路径不受影响
- 超低延迟: 无影响 (仅影响 429 恢复路径, 正常成功路径不触发 cooldown)
- 稳定优先: +5s buffer 保守, 65+65=130<<195 BUDGET 充足, HM2 R1657 已验证
- 铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
