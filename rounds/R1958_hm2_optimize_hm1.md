# R1958 (HM2→HM1): NVU_TIER_BUDGET_GLM5_2_NV 30→28 — 压缩 glm5_2 zombie 失败路径 2s

## 数据
- 6h: 44 req, 39 OK (88.64% SR), 5 fail (status=502)
- 30min: 12 req, 11 OK (91.67% SR), 1 fail
- dsv4p_nv: 10 OK, avg=31599ms, min=11102ms, max=55335ms — **0 genuine OK, all 10 peer-fb rescued**
- glm5_2_nv: 29 OK, avg=10129ms, min=3484ms, max=26165ms, p95=17998ms — healthy
- kimi_nv: 0 traffic (6h)

## 错误分解
- 5× `zombie_empty_completion` (status=502), all glm5_2_nv
  - Timestamps: 12:33, 13:03, 14:03, 15:03, 18:04 UTC (~30-60min spacing)
  - Root cause: NVCF empty200 degradation (not HM1 config)
- 24× `all_tiers_exhausted` + status=200 (phantom ATE, all peer-fb rescued)
  - dsv4p_nv: 6 phantom ATE, all status=200 peer-fb rescued
  - glm5_2_nv: 18 phantom ATE, all status=200 peer-fb rescued
- 0 real ATE with status=502
- 0 tier-level errors (only 16 pexec_success in tier_attempts)
- 0 fallback_occurred=true in DB
- key_cycle_429s: 16 req with 1 cycle each, normal rotation

## 容器日志 (docker logs nv_gw --tail 100)
- NV-PEXEC-FASTBREAK: dsv4p_nv consecutive NVCFPexecTimeout → fast-break
- NV-TIER-FAIL: dsv4p_nv all 5 keys timeout
- NV-PEER-FB: all dsv4p rescued OK
- 容器重启后无新错误

## 决策: NVU_TIER_BUDGET_GLM5_2_NV 30→28

**数据支撑**: glm5_2 genuine OK max=26165ms < 28s (1.8s margin). 5 zombie 全 NVCF empty200 不可修, 压缩 tier budget 省 2s/失败. Peer-fb: 28+122=150<153 BUDGET safe.

**预期效果**: 每个 glm5_2 zombie 失败路径节省 2s 等待时间, 更快触发 peer-fb/ms_gw fallback.

**铁律**: 只改HM1不改HM2

## 参数变更
| 参数 | 旧值 | 新值 | 理由 |
|------|------|------|------|
| NVU_TIER_BUDGET_GLM5_2_NV | 30 | 28 | glm5_2 OK max=26165ms<28s safe, 150<153 BUDGET, saves 2s/zombie |
## ⏳ 轮到HM1优化HM2
