# R1008: MIN_OUTBOUND_INTERVAL_S 1.5→5 防止 429 级联

> 时间: 2026-08-04 01:35 BJT (17:35 UTC)
> 容器: dsv4p_nv40066 (端口 40066, HM2 本机)

## 1. 数据 (改前必有数据)

### 30min 窗口主指标 (ts > NOW() - 30min)
- **总量**: 94, **成功率**: 66/94 = **70.2%**
- **延迟**: avg=9707ms, p50=3195ms, p95=43008ms
- **错误**: all_tiers_exhausted=27, NVAnthCollect_IncompleteRead=1

### ATE 双峰分布 (error_type=all_tiers_exhausted)
| bucket | count | avg_ms | 含义 |
|--------|-------|--------|------|
| <10ms (instant) | 10 | 3 | GLOBAL-COOLDOWN 级联中的秒 fail |
| 60ms-60s | 12 | 8394 | 真 pexec 全 key 失败 |
| >60s (real) | 5 | 100245 | 真实预算耗尽 |

**10/27 (37%) 的 ATE 是 <10ms 瞬时 fail** — 请求到达时所有 key 正在 TIER_COOLDOWN 中, 无 pexec 尝试直接返回 502.

### 级联机制 (docker logs 确认)
```
[01:09:06.7] [NV-GLOBAL-COOLDOWN] tier=dsv4p_nv all keys 429. Marking all cooling 90s (TIER_COOLDOWN)
[01:09:25.6] [NV-GLOBAL-COOLDOWN] tier=dsv4p_nv all keys 429. Marking all cooling 90s (TIER_COOLDOWN)
```
级联发生时: 17:09 UTC 1 分钟内 10 个请求全 fail at 3ms avg.

### 突发流量来源
- caller 分布 (30min): cc4101-fallback=120 (92%), hermes=10, openclaw=3
- 16:54 UTC: 30 req/min 全部 fail at 4ms — cc4101-fallback 突发冲击

### 根因: MIN_OUTBOUND_INTERVAL_S 缺失
- dsv4p_nv40066 **未设 MIN_OUTBOUND_INTERVAL_S**, 使用默认值 1.5s
- nv_gw (端口 40006) 设 MIN_OUTBOUND_INTERVAL_S=10s (R37, 验证有效)
- 1.5s 间隔允许 40 req/min → 5 key × 8 req/key/min → NVCF 429 配额极快耗尽
- 全 5 key 同时 429 → NV-GLOBAL-COOLDOWN 触发 → 90s 全 key 冻结 → 后续请求 <10ms 秒 fail

### 6h 趋势
| hour | total | s200 | ate | ir | sr_pct |
|------|-------|------|-----|----|----|
| 11:00 | 38 | 35 | 3 | 0 | 92.1% |
| 12:00 | 168 | 168 | 0 | 0 | 100.0% |
| 13:00 | 186 | 167 | 0 | 1 | 89.8% |
| 14:00 | 186 | 168 | 13 | 0 | 90.3% |
| 15:00 | 132 | 109 | 9 | 3 | 82.6% |
| 16:00 | 241 | 160 | 80 | 0 | 66.4% |
| 17:00 | 41 | 24 | 16 | 1 | 58.5% |

SR 从 100%→66.4%→58.5% 持续下降, ATE 从 0→80→16 (累积 24h=270).

### 429 级联分析 (3h)
- 3+ key 同时 429 的分钟: 5 次 (18 个 429) — 每次触发 GLOBAL-COOLDOWN
- <3 key 429 的分钟: 30 次 (39 个 429) — 不触发全局冷却

### Per-key 成功延迟 (30min, status=200)
| key | s200 | avg_ms |
|-----|-------|--------|
| 0 | 12 | 3469 |
| 1 | 10 | 17750 |
| 2 | 21 | 12462 |
| 3 | 18 | 5999 |
| 4 | 5 | 10369 |

k4 成功数最低 (5), k1 延迟最高 (17.7s).

## 2. 修改

| 参数 | 旧值 | 新值 | 理由 |
|------|------|------|------|
| MIN_OUTBOUND_INTERVAL_S | 1.5 (default) | **5** | 强制 5s 出站间隔, 限速 12 req/min, 防止突发触发全 key 429 级联 |

## 3. 预期效果

- 5s 间隔 → 12 req/min max → 每 key ~2.4 req/min, 降低 NVCF 429 率
- 减少 NV-GLOBAL-COOLDOWN 触发频率 → 减少 <10ms 瞬时 ATE
- 当前实际 avg=2.2 req/min, 5s 间隔仍允许 5.5× headroom
- 参考 nv_gw 使用 10s 有效, 本容器选 5s (更保守但不过度限制)

## 4. 验证清单
- [x] docker compose config 无 YAML 错误
- [x] docker compose up -d dsv4p_nv40066 成功 recreate
- [x] /health 返回 ok, 5 keys, 3 models
- [x] MIN_OUTBOUND_INTERVAL_S=5 在容器 env 中确认
- [x] config.py 加载确认: MIN_OUTBOUND_INTERVAL_S = 5.0s
- [ ] 30min 后验证: 瞬时 ATE 数量下降, SR 回升

## 5. 上次修改效果 (R1007)
- R1007: TIER_COOLDOWN_S 180→90
- 效果: 30min 窗口瞬时 ATE 仍 10/27 (37%), SR=70.2%
- 结论: TIER_COOLDOWN 降到 90s 减少了冻结持续时间, 但未阻止级联触发本身
- R1008 修复方向正确: 需从源头减少 429 级联频率, 而非仅缩短冻结时间

## 6. 下一步建议
- 观察 30min: 瞬时 ATE (<10ms) 是否降为 0 或显著减少
- 若 5s 不足以防级联, 可升至 8s (接近 nv_gw 的 10s)
- 若 SR 恢复 >85%, 考虑进一步调 NVU_KEYMGR_429_BASE_COOLDOWN 120→90 缩短单 key 冷却
- k4 成功率偏低 (5/66=7.6%) 需后续轮观察是否持续劣化
