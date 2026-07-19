# R1957 (HM2→HM1): TIER_BUDGET_DSV4P_NV 25→20 — dsv4p_nv NVCF completely dead, 0 genuine OK, save 5s per request

## 数据
- 6h: 44 req, 39 OK (88.64% SR), 5 fail (status=502)
- dsv4p_nv: 10 OK, avg=31599ms, min=11102ms, max=55335ms — **0 genuine OK, all 10 peer-fb rescued**
- glm5_2_nv: 29 OK, avg=10129ms, min=3484ms, max=26165ms — healthy
- kimi_nv: 0 traffic (6h)

## 错误分解
- 5× `zombie_empty_completion` (status=502), all glm5_2_nv
  - Timestamps: 12:03, 12:33, 13:03, 14:03, 15:03, 18:04 UTC (~30-60min spacing)
  - Root cause: NVCF empty200 degradation (not HM1 config)
- 24× `all_tiers_exhausted` + status=200 (phantom ATE, all peer-fb rescued)
  - All dsv4p_nv, all 24 status=200 (peer-fb rescued)
  - 0 real ATE with status=502
- 0 new error types
- 0 fallback_occurred=true in DB
- key_cycle_429s: 16 req with 1 cycle each, normal rotation

## 容器日志 (docker logs nv_gw --tail 100)
- NV-PEXEC-FASTBREAK: dsv4p_nv consecutive NVCFPexecTimeout → fast-break (saved keys), 25s timeout
- NV-TIER-FAIL: dsv4p_nv all 5 keys failed: 429=0, empty200=0, timeout=1, other=0, elapsed=25026ms
- NV-PEER-FB: all rescued OK, ttfb 0-57ms
- NV-ZOMBIE-EMPTY: glm5_2_nv at 18:04, input_chars=152349, content_chars=12, reasoning_chars=0, zombie→content_filter SSE

## 决策: TIER_BUDGET_DSV4P_NV 25→20

**数据支撑**: dsv4p_nv 连续 6h 内 **0 genuine OK** — 全部 10 个 OK 都是 peer-fb 救回。NVCF pexec 在 HM1 日本 IP 上完全不可达 (5 个 key 全部 timeout @25s)。25s tier budget 是纯浪费。

**计算**: 20 + 122 (PEER_FALLBACK_TIMEOUT) = 142 < 153 (TIER_TIMEOUT_BUDGET_S) ✓ safe

**预期效果**: 每个 dsv4p_nv 请求节省 5s 等待时间，peer-fb 5s 更早触发。

**铁律**: 只改HM1不改HM2

## 参数变更
| 参数 | 旧值 | 新值 | 理由 |
|------|------|------|------|
| NVU_TIER_BUDGET_DSV4P_NV | 25 | 20 | dsv4p_nv 0 genuine OK, 25s 纯浪费, 20+122=142<153 safe |
## ⏳ 轮到HM1优化HM2
