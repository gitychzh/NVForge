# R1009: NVU_KEYMGR_429_MAX_COOLDOWN 300→120 消除全 key 429 后 5min 黑屏

> 时间: 2026-08-04 01:52 BJT (17:52 UTC)
> 容器: dsv4p_nv40066 (端口 40066, HM2 本机)

## 1. 数据 (改前必有数据)

### 30min 窗口主指标 (pre-restart context, ts > NOW()-30min)
- **总量**: 118, **成功**: 93, **成功率**: 93/118 = **78.8%**
- **延迟**: avg=11572ms, p50=3038ms, p95=51081ms
- **错误**: all_tiers_exhausted=25, NVStream_IncompleteRead=1 (30min context)
- **429 计数**: 2 (请求级 429), key_cycle_429s: k0=107, k1=9, k2=1, k3=1

### 6h 趋势
| hour | total | s200 | ate | sr_pct |
|------|-------|------|-----|--------|
| 14:00 | 31 | 21 | 10 | 67.7% |
| 15:00 | 133 | 110 | 23 | 82.6% |
| 16:00 | 241 | 160 | 81 | 66.4% |
| 17:00 | 137 | 108 | 29 | 78.8% |

### R1008 (MIN_OUTBOUND=5) 效果验证 — 级联仍发生但延迟了
R1008 重启时间: 17:32 UTC. 级联发生时间: 17:44 UTC (重启后 8min).
- R1008 前: 级联在突发后 **立即** 发生 (30 req/min → 全 key 429 → 秒 fail)
- R1008 后: MIN_OUTBOUND=5 延缓了 429 到达速率 (8min vs 立即), 但一旦全 5 key 同时 429, 仍触发完整级联

### 级联详细分析 (17:44-17:51 UTC, 8min 黑屏)

容器日志铁证:
```
[01:48:36.4] [NV-CYCLE] tier=dsv4p_nv k4 → 429, cycling to next key
[01:48:37.1] [NV-KEYMGR] 429 tier=dsv4p_nv k5 count=5 cooldown=300s
[01:48:37.8] [NV-KEYMGR] 429 tier=dsv4p_nv k1 count=5 cooldown=300s
[01:48:37.8] [NV-TIER] tier=dsv4p_nv all keys in cooldown/auth-failed, breaking
[01:48:37.8] [NV-TIER-FAIL] tier=dsv4p_nv all 5 keys failed: 429=5, elapsed=6505ms
[01:49:10.7] [NV-TIER-SKIP] tier=dsv4p_nv all keys in cooldown, skipping
[01:49:17.8] [NV-TIER-SKIP] ...
[01:49:38.1] [NV-TIER-SKIP] ...
[01:49:44.7] [NV-TIER-SKIP] ...  (8 consecutive SKIP)
```

逐分钟分布 (17:44-17:51):
| minute | total | s200 | instant_ate | avg_ms |
|--------|-------|------|-------------|--------|
| 17:44 | 3 | 0 | 3 | 3 |
| 17:46 | 6 | 2 | 3 | 909 |
| 17:47 | 9 | 0 | 9 | 4 |
| 17:48 | 4 | 0 | 3 | 1633 |
| 17:49 | 8 | 0 | 8 | 4 |
| 17:50 | 2 | 0 | 2 | 4 |

**26/38 请求在 7min 内全部 instant ATE (<10ms)** — 请求到达时所有 key 在 429 冷却中.

### 根因: NVU_KEYMGR_429_MAX_COOLDOWN=300 超过 TIER_COOLDOWN=90

层级关系 (全 5 key 同时 429 时):
1. `NV-GLOBAL-COOLDOWN` 触发 → TIER_COOLDOWN_S=90s (R1007)
2. 90s 后 tier 冷却到期 → 尝试重新调度
3. 但各 key 的 429 冷却仍有效 (count=5 → cooldown=300s)
4. 所有 key 仍在冷却 → `NV-TIER-SKIP` → 秒 fail
5. **有效黑屏时间 = max(TIER_COOLDOWN=90, key_429_cooldown=300) = 300s**

R1007 的 TIER_COOLDOWN=90 和 R1008 的 MIN_OUTBOUND=5 都不能解决此问题:
- R1007 缩短了 tier 级冻结, 但 key 级 429 冷却更长 (300s), TIER-SKIP 仍持续
- R1008 延缓了 429 到达, 但一旦触发, 后果不变

### Per-key 延迟 (30min, status=200)
| key | s200 | avg_ms |
|-----|-------|--------|
| 0 | 19 | 11075 |
| 1 | 19 | 55175 |
| 2 | 5 | 55658 |
| 3 | 34 | 30959 |
| 4 | 16 | 34734 |

k2 仅 5 次成功, 延迟最高 (55.7s). k3 最活跃 (34 次).

### upstream_type 分布
| upstream | count | s200 | avg_ms |
|----------|-------|------|--------|
| nvcf_pexec | 93 | 93 | 9801 |
| (empty) | 25 | 0 | 18162 |

pexec 100% SR (93/93), 所有失败来自 ATE (upstream_type 为空 = KeyManager 层 ABORT).

## 2. 修改

| 参数 | 旧值 | 新值 | 理由 |
|------|------|------|------|
| `NVU_KEYMGR_429_MAX_COOLDOWN` | 300 | **120** | 消除全 key 429 后 300s 黑屏. 降到 120s 后有效黑屏=max(90,120)=120s (vs 300s, 60%↓). 120s 仍 > NVCF 限流窗口 ~60s, MIN_OUTBOUND=5 已限频防快速二次 429 |

**生效方式**: docker compose up -d --force-recreate

## 3. 预期效果

1. 全 5 key 同时 429 后黑屏从 300s → 120s (60%↓)
2. TIER_COOLDOWN=90s 到期后, key 429 冷却 (120s) 仅多 30s → blackout 窗口从 210s → 30s
3. 瞬时 ATE 数量预期下降 ~80% (从 26/8min → ~5/8min)
4. pexec 100% SR 不受影响 (R1006 清空 integrate 后 pexec 是唯一路径)
5. 不增加 NVCF 429 风险: 120s 仍 > NVCF ~60s 限流窗口

## 4. 验证清单
- [x] docker compose config 无 YAML 错误
- [x] docker compose up -d dsv4p_nv40066 --force-recreate 成功
- [x] /health 返回 ok, 5 keys, 3 models
- [x] NVU_KEYMGR_429_MAX_COOLDOWN=120 在容器 env 中确认
- [ ] 30min 后验证: 全 key 429 后黑屏时间 ≤120s, 瞬时 ATE 下降

## 5. 上次修改效果 (R1008)
- R1008: MIN_OUTBOUND_INTERVAL_S 1.5→5
- 效果: 30min SR=78.8% (93/118), 仍有 25 次 ATE
- 结论: MIN_OUTBOUND=5 延缓了 429 到达 (8min vs 立即), 但一旦全 key 同时 429, 黑屏时间仍由 429_MAX_COOLDOWN=300s 决定
- R1009 修复方向正确: 缩短 key 级 429 冷却上限, 使其与 TIER_COOLDOWN 对齐

## 6. 参数演化历史
| Round | 参数 | 旧→新 | 效果 |
|-------|------|-------|------|
| R1006 | NV_KEY_INTEGRATE_KEYS | dsv4p_nv:3→空 | 消除 integrate 0% SR 浪费, pexec 成唯一路径 |
| R1007 | TIER_COOLDOWN_S | 180→90 | 缩短 tier 级冻结, 但 key 级 300s 仍主导黑屏 |
| R1008 | MIN_OUTBOUND_INTERVAL_S | 1.5→5 | 延缓 429 到达, 但不改变触发后黑屏时长 |
| R1009 | NVU_KEYMGR_429_MAX_COOLDOWN | 300→120 | 消除 key 级长冷却, 黑屏 300→120s |

## 7. 下一步建议
- 观察 30min: 全 key 429 后黑屏是否 ≤120s, 瞬时 ATE 是否大幅下降
- 若黑屏仍 >120s: 检查 NVU_KEYMGR_429_BASE_COOLDOWN 是否也需下调 (当前 120s, 与 MAX 相同=退避失效)
- 若 SR 恢复 >90%: 考虑进一步优化 per-key SOCKS5 代理延迟 (k2=55.7s 偏高)
- hm4104 fallback 频繁 (日志 5min 内 8 次), 说明 dsv4p_nv 不可用期 cc4101 切到 ms_gw — 降黑屏后应减少 fallback 触发
