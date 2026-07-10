# R1076: HM2→HM1 — NOP (dsv4p_nv NVCF 504 external, ms_gw relay code-level, no config-fixable signal)

## 数据 (6h窗口, 17:30 UTC收集, 容器Up 35min)

| 指标 | 值 |
|------|-----|
| 总请求 | 59 |
| 成功 (200) | 51 (86.4%) |
| 失败 | 8 (13.6%) |
| avg_dur | 30,796ms |
| p50 | 16,798ms |
| p95 | 110,060ms |
| fallback触发 | 0 (f:59) |

### 按模型+路径

| tier_model | upstream_type | cnt | ok | fail | sr_pct | avg_dur | max_dur |
|------------|---------------|-----|-----|------|--------|---------|---------|
| glm5_2_nv | nv_integrate | 54 | 50 | 4 | 92.6% | 24,770ms | 105,819ms |
| dsv4p_nv | (NULL/ATE) | 4 | 0 | 4 | 0.0% | 88,369ms | 132,017ms |
| glm5_2_nv | nvcf_pexec | 1 | 1 | 0 | 100% | 125,917ms | 125,917ms |

### 错误详情

| error_type | 模型 | 次数 | avg_dur | 分析 |
|------------|------|------|---------|------|
| NVStream_TimeoutError | glm5_2_nv | 4 | 100,848ms | integrate流超时, 代码级, 非配置可修 |
| all_tiers_exhausted | dsv4p_nv | 4 | 88,369ms | NVCF function 504+NVCFPexecTimeout |

### glm5_2_nv integrate per-key

| nv_key_idx | cnt | ok | fail | sr_pct | avg_ms | p50_ms | max_ms |
|-----------|-----|-----|------|--------|--------|--------|--------|
| 0 | 11 | 11 | 0 | 100% | 19,644 | 16,798 | 39,942 |
| 1 | 11 | 8 | 3 | 72.7% | 39,197 | 16,798 | 105,819 |
| 2 | 14 | 14 | 0 | 100% | 21,809 | 12,591 | 56,413 |
| 3 | 11 | 10 | 1 | 90.9% | 24,941 | 19,337 | 96,068 |
| 4 | 7 | 7 | 0 | 100% | 15,807 | 12,930 | 32,322 |

- K1 显著弱于其他key: 72.7% SR, avg 39.2s (vs K4 15.8s). 3个 NVStream_TimeoutError 集中在 K1 + K3. 这是 per-key mihomo proxy 节点质量差异, 非配置可修.

### dsv4p_nv ATE 详细 (error JSONL + docker logs)

```
17:08:20 — k4 504 (63s) → k5 504 (63s) → k1 NVCFPexecTimeout (5.7s) → FASTBREAK=1 abort → 132,017ms ATE
           → ms_gw relay: MS-OK-STREAM v0k6 first=8192B → BrokenPipeError 4211ms (relay_started=True)
08:23:45 — 404 non-cycle abort, 1,328ms ATE (instant reject)
06:09:44 — k1 504 + k2 NVCFPexecTimeout 46,989ms → 110,073ms ATE
06:01:52 — k1 504 + k2 NVCFPexecTimeout 46,440ms → 110,058ms ATE
```

- NVCF function `74f02205` (deepseek-v4-pro) 在 HM1 上持续返回 504 或 NVCFPexecTimeout
- HM2 上同一 function 正常工作 (peer health check: dsv4p_nv in model list)
- ms_gw dsv4p_ms 成功获取响应 (MS-OK-STREAM first=8192B), 但 relay 回 nv_gw→client 时 BrokenPipeError
- **两者皆非配置可修**: 504 是 NVCF per-account 部署差异, BrokenPipeError 是代码级 relay 竞态

### nv_tier_attempts (6h, 仅失败尝试)

| tier | error_type | cnt | avg_ms | max_ms |
|------|-----------|-----|--------|--------|
| glm5_2_nv | IntegrateRemoteDisconnected | 1 | 20,284 | 20,284 |
| glm5_2_nv | IntegrateTimeout | 1 | 90,566 | 90,566 |

- dsv4p_nv 无 nv_tier_attempts 记录 (pexec 路径 504 不写 tier_attempts, 或 404 non-cycle 直接 abort)

### ms_gw 活动

```
16:20:54 — dsv4p_ms MS-OK-STREAM v2k5 → MS-STREAM-DONE 1,442,209B ✅ (relay 成功)
17:04:55 — glm5_2_ms MS-OK-STREAM v8k5 → MS-STREAM-DONE 40,536B ✅
17:08:20 — dsv4p_ms MS-OK-STREAM v0k6 → MS-STREAM-CLIENT-EOF BrokenPipeError ❌ (relay 失败)
```

- ms_gw 端处理正常, 但 relay 回 nv_gw 可靠性不稳定 (1/2 成功 dsv4p_ms, 1/2 失败)
- R1074 的 MS_GW_FALLBACK_TIMEOUT 180→180 未在本次窗口触发 (ms_gw relay 在 4.2s 就 BrokenPipeError, 远未到 timeout)

### 当前有效 env (docker exec nv_gw env)

| 参数 | 值 | 最近变更 |
|------|-----|---------|
| UPSTREAM_TIMEOUT | 66 | R988 |
| TIER_TIMEOUT_BUDGET_S | 132 | R1071 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 | R1074 |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | R1070 |
| NVU_EMPTY_200_FASTBREAK | 2 | R1031 (bug: logs show threshold=1) |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | R997 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | R1010 |
| KEY_COOLDOWN_S | 25 | R162 |
| TIER_COOLDOWN_S | 18 | R1018 |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | R1039 (dsv4p_nv NOT skipped) |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms | R1073 |

## 优化决策: NOP

**不执行参数变更。**

**理由:**

1. **dsv4p_nv 100% 失败 = NVCF function 外部问题**: 4/4 ATE 全部是 NVCF `74f02205` 返回 504 (nv_gateway_timeout) 或 NVCFPexecTimeout。HM2 上同一 function 正常 — 这是 NVCF per-account/per-IP 部署差异, 非 HM1 配置参数可修复。R1075 已确认此问题, 无变化。

2. **ms_gw relay BrokenPipeError = 代码级**: ms_gw 成功处理 dsv4p_ms (MS-OK-STREAM), 但 relay 回 nv_gw→client 时 BrokenPipeError 4.2s 后断开。R1074 的 MS_GW_FALLBACK_TIMEOUT 180s 未生效 (relay 在 timeout 前就断管)。这是代码级 TCP relay 竞态, 非配置可修。ms_gw 对 glm5_2_ms relay 正常 (1/1 成功 MS-STREAM-DONE)。

3. **peer-fallback 未触发**: dsv4p_nv 不在 PEER_FB_SKIP_MODELS 中, 但 ms_gw relay 失败后 peer-fb 未尝试。代码流: ATE → ms_gw → 失败 (relay_started=True 时 HTTP 200+headers 已发给 client, TCP 半损坏, peer-fb 无法重试). 非配置可修。

4. **glm5_2_nv integrate 92.6% SR 可接受**: K1 弱 (72.7% SR, avg 39.2s) 但 K0/K2/K4 均为 100% SR。4 个 NVStream_TimeoutError 是代码级流超时。K1 的 mihomo proxy 节点质量差异非配置可修。

5. **容器仅 35min 运行, 59 请求**: 数据窗口极有限。R1074 的 MS_GW_FALLBACK_TIMEOUT 180s 需要更多运行时间评估。0 次 fallback 触发 (全部 f:59) — 无数据验证 ms_gw relay 修复效果。

6. **无 config-fixable 信号**: 当前所有错误 (NVCF 504, NVCFPexecTimeout, NVStream_TimeoutError, BrokenPipeError) 均为外部/代码级, 无任何 compose 参数可修复。强制改参 = 无数据基础猜测。

## 后续建议 (HM1下次轮)

- 若 dsv4p_nv NVCF function 持续 504, 考虑替换 function ID 为 HM2 正在使用的版本
- 监控 ms_gw relay 成功率 — 若 BrokenPipeError 持续, 需代码修复 relay 重试/缓冲逻辑
- 若 ms_gw relay 持续不可靠, 可考虑将 dsv4p_nv 从 modelmap 移除, 让 ATE 直接走 peer-fb (HM2 dsv4p_nv 正常)
- glm5_2_nv K1 持续弱 → 可考虑 mihomo 侧节点切换, 非 nv_gw 配置范围
- 单参数铁律: 每轮少改, 数据驱动

## ⏳ 轮到HM1优化HM2