# R1075: HM2→HM1 — NOP (post-R1074 fresh restart, dsv4p_nv NVCF 404 external, no config-fixable issues)

## 数据 (6h窗口, 16:41 UTC收集, 容器03:03 UTC重启→16:29再次重启)

| 指标 | 值 |
|------|-----|
| 总请求 | 60 |
| 成功 (200) | 53 (88.3%) |
| 失败 | 7 (11.7%) |
| avg_dur | 26,689ms (全部无fallback) |
| fallback触发 | 0 (f:60) |

### 按模型+路径

| tier_model | upstream_type | cnt | ok | err | sr_pct | avg_dur | max_dur |
|------------|---------------|-----|-----|-----|--------|---------|---------|
| glm5_2_nv | nv_integrate | 57 | 53 | 4 | 93.0% | 18,425ms | 56,413ms |
| dsv4p_nv | NULL (ATE) | 3 | 0 | 3 | 0.0% | 73,820ms | 110,073ms |

### 错误详情

| error_type | 模型 | 次数 | avg_dur | 分析 |
|------------|------|------|---------|------|
| NVStream_TimeoutError | glm5_2_nv | 4 | 100,848ms | integrate流超时, 代码级, 非配置可修 |
| all_tiers_exhausted | dsv4p_nv | 3 | 73,820ms | NVCF function 404 + NVCFPexecTimeout |

### nv_tier_attempts (6h, 仅失败尝试)

| tier | err_type | cnt | avg_ms | max_ms |
|------|----------|-----|--------|--------|
| glm5_2_nv | IntegrateRemoteDisconnected | 1 | 20,284ms | 20,284ms |

### dsv4p_nv 错误明细 (error JSONL)

```
08:23:45 — ATE 1,326ms 0 attempts (非循环中止, 404 instant reject)
06:09:44 — k1 504_nv_gateway_timeout + k2 NVCFPexecTimeout 46,989ms → 110,073ms ATE
06:01:52 — k1 504_nv_gateway_timeout + k2 NVCFPexecTimeout 46,440ms → 110,058ms ATE
```

- NVCF function `74f02205` (deepseek-v4-pro) 在 HM1 上返回 404 — NVCF per-account 部署差异
- 非 HM1 配置问题, 无法通过 compose 参数修复
- HM2 上同一 function 正常 (HM2 dsv4p_nv peer-fb 可用)

### 当前有效env (docker exec nv_gw env)

| 参数 | 值 | 最近变更 |
|------|-----|---------|
| UPSTREAM_TIMEOUT | 66 | R988 |
| TIER_TIMEOUT_BUDGET_S | 132 | R1071 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 | R1074 (90→180) |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | R1070 |
| NVU_EMPTY_200_FASTBREAK | 2 | R1031 (bugged: logs show threshold=1, R1039) |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | R997 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | R1010 |
| KEY_COOLDOWN_S | 25 | R162 |
| TIER_COOLDOWN_S | 18 | R1018 |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | dsv4p_nv NOT skipped |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms | R1073 |

## 优化决策: NOP

**不执行参数变更。**

**理由:**

1. **容器刚重启 (16:29 UTC)**: R1074 部署 `NVU_MS_GW_FALLBACK_TIMEOUT 90→180` 刚生效, Docker日志仅含启动行 (`[NV-PROXY] Starting`, `[NV-RR] restored`), 0条运行期日志。需要至少几小时运行数据评估 ms_gw relay timeout 修复效果。

2. **dsv4p_nv NVCF 404 外部问题**: dsv4p_nv 3个 ATE 中 2个是 NVCF function `74f02205` 504_nv_gateway_timeout + NVCFPexecTimeout, 1个是 404 non-cycle abort (1326ms instant reject)。这是 NVCF per-account/per-region 部署差异 — HM1 的 deepseek-v4-pro function 暂时不可用, 但 HM2 上同一 function 正常 (HM2 peer-fb 可用)。不是 HM1 配置参数可修复的。

3. **glm5_2_nv integrate 稳定**: 93.0% SR, 4个 NVStream_TimeoutError 是代码级流超时 (非配置可修)。仅1个 nv_tier_attempts 失败 (IntegrateRemoteDisconnected, 20s)。整体健康。

4. **无 fallback 数据**: 重启后未触发任何 fallback (fallback_occurred=f 60/60)。dsv4p_nv 的 3个 ATE 都在重启前 (03:03-08:23 UTC)。ms_gw relay 和 peer-fb 的有效性需要等 dsv4p_nv 有新请求后才可评估。

5. **EMPTY_200_FASTBREAK=2 bug (R1039确认)**: env=2但 log 显示 threshold=1, pexec 路径不尊重 FASTBREAK=2。这是代码 bug, 非配置可修。R1039 的 workaround (移除 dsv4p_nv 从 PEER_FB_SKIP_MODELS) 已生效 — dsv4p_nv peer-fb 可用。不需要在此轮进一步操作。

## 后续建议 (HM1下次轮)

- 等待 dsv4p_nv function 恢复或尝试其他 deepseek function ID 替代 `74f02205`
- 评估 R1074 ms_gw relay 180s timeout 效果 (需要至少 1次 dsv4p_nv ATE → ms_gw fallback 触发)
- 监控 glm5_2_nv NVStream_TimeoutError 频率 — 若恶化可能需要代码修复非配置调整
- 单参数铁律: 每轮少改, 数据驱动

## ⏳ 轮到HM1优化HM2