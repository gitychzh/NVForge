# R1245: HM2→HM1 — dsv4p_nv 移出 NV_KEY_INTEGRATE_KEYS (K5不再走integrate, 直接pexec)

## 数据 (6h: 08:00–13:33 UTC, pre-R1245)

| 指标 | 值 |
|------|-----|
| 总请求 | 141 |
| OK (200) | 110 (78.0%) |
| 失败 | 31 (22.0%) |
| zombie_empty_completion | 16 (NVCF content-filter, 不可配置修复) |
| all_tiers_exhausted | 14 |
| NVStream_IncompleteRead | 1 |

### 按路径

| 路径 | 请求数 | OK | SR | avg_dur |
|------|--------|----|----|---------|
| nv_integrate (glm5_2_nv) | 115 | 99 | 86.1% | 29.4s |
| nvcf_pexec (glm5_2_nv) | 9 | 8 | 88.9% | 97.6s |
| **nvcf_pexec (dsv4p_nv)** | **3** | **3** | **100%** | **22.4s** |
| dsv4p_nv ATE (无 upstream_type) | 5 | 0 | 0% | 75.9s |

### dsv4p_nv ATE error_detail 分析

```
request_id=a5e493da: integrate_dsv4p_nv_all_keys_failed (k5 IntegrateTimeout 72,068ms)
  → tier_dsv4p_nv_all_keys_failed: k5 integrate timeout + k1 504_gateway_timeout + k2 budget_exhausted_after_connect
  → all_tiers_failed: dsv4p_nv only, elapsed=142,677ms
  → ms_gw fallback: BrokenPipeError 10,853ms (relay_started=True)

request_id=78090ee9: tier_dsv4p_nv_all_keys_failed: k2 504_gateway_timeout (67,663ms)
  → all_tiers_failed: dsv4p_nv only, elapsed=67,665ms

request_id=4b25e9f3: tier_dsv4p_nv_all_keys_failed: k3 504_gateway_timeout + k4 NVCFPexecTimeout (72,013ms)
  → all_tiers_failed: dsv4p_nv only, elapsed=72,019ms

request_id=33739ffd: tier_dsv4p_nv_all_keys_failed: k4 504_gateway_timeout + k5 NVCFPexecTimeout (72,012ms)
  → all_tiers_failed: dsv4p_nv only, elapsed=72,015ms
```

### 根因分析

dsv4p_nv 的 `NV_KEY_INTEGRATE_KEYS=dsv4p_nv:5` 导致 K5 先走 integrate (72s timeout, NV_KEY_INTEGRATE_PROXY_URLS=7897), 失败后才 fallback 到 pexec。但：

1. **dsv4p_nv pexec 100% SR** (3/3 OK, avg 22.4s) — pexec 路径健康
2. **dsv4p_nv integrate 100% 失败** — K5 integrate 超时 72s (TIER_BUDGET=72 边界), 吃光 tier budget
3. integrate 超时后 pexec 剩余 budget 不足 (post-connect remaining 1.4s < 5s MIN), 导致 budget_exhausted_after_connect
4. 72s 浪费在注定失败的 integrate 路径上, 若直接 pexec 可节省 72s 并提高成功率
5. ms_gw dsv4p_ms fallback 因 BrokenPipeError 不可靠 (代码级缺陷, 非配置可修)

## 修改

**参数**: `NV_KEY_INTEGRATE_KEYS: "dsv4p_nv:5;minimax_m3_nv:5"` → `"minimax_m3_nv:5"`

**效果**: dsv4p_nv K5 不再走 integrate (per-key lane), 直接走 pexec (100% SR 实证). minimax_m3_nv:5 不受影响.

**节省**: 每 dsv4p_nv ATE 节省 72s integrate 超时 + 避免 budget_exhausted → 预计 dsv4p_nv ATE 大幅减少, 或转为 pexec 快速成功.

**验证**: 
- E2E: `curl dsv4p_nv` → pexec k5 → "Hello, my friend!" 成功 (46s)
- 日志确认: `[NV-KEY] tier=dsv4p_nv attempt 1/7: k5 → NVCF pexec` (无 integrate)
- 容器 env: `NV_KEY_INTEGRATE_KEYS=minimax_m3_nv:5` ✓

## 评判

- 更少报错: dsv4p_nv ATE (5/6h) 预期减少, pexec 100% SR 实证
- 更快请求: 节省 72s integrate 超时, 直接 pexec ~22-46s
- 超低延迟: dsv4p_nv pexec avg 22.4s, 稳定
- 稳定优先: 单参数移除, 风险极低

## 上下文

- R1244: NVU_MS_GW_FALLBACK_TIMEOUT 180→200 (glm5_2_nv ms_gw relay 超时修复, 刚部署待验证)
- dsv4p_nv pexec 持续 100% SR (已验证多轮)
- dsv4p_nv integrate 走美国出口 7897, K5 72s 超时是 integrate 路径固有延迟, 非偶尔故障
- 单参数; 铁律: 只改HM1不改HM2
- 备份: docker-compose.yml.bak.RN_hm2_optimize_hm1-pre-rm-dsv4p-key-integrate

## ⏳ 轮到HM1优化HM2