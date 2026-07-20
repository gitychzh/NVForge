# R13 (hermes2, 2026-07-20): 巡检轮 — SR 79.1% 继续上升, KEY_COOLDOWN=180 持续生效, 不改代码

## 本轮模式: 巡检轮 (无代码改动)

## 数据 (30min 窗口, 北京时间 2026-07-20 约 19:10-19:40)

### nv_requests (dsv4p_nv)

| request_model | status | count |
|---------------|--------|-------|
| dsv4p_nv      | 200    | 34    |
| dsv4p_nv      | 502    | 7     |
| dsv4p_nv      | 429    | 2     |

- **总请求**: 43, **成功**: 34, **SR = 79.1%**
- error_type: all_tiers_exhausted × 9 (502=7 + 429=2)

### nv_tier_attempts

| error_type       | count | 按 key 分布 |
|------------------|-------|-------------|
| 429_nv_rate_limit | 51   | k0:12, k1:17, k2:6, k3:2, k4:13 |
| empty_200        | 4     | k0:1, k2:2, k3:1 |
| NVCFPexecTimeout | 2     | k0:1, k2:1 |

### Fallback (hm4104)

- 30min fallback: 158 (R12: 147, +7.5%)
- 原因: nv_gw 18 分钟前重启过 (R12 后?), 重启窗口产生 fallback 峰值
- PRIMARY-BREAKER-SKIP-STREAM: 持续 OPEN (breaker 未恢复)

## R12 → R13 对比

| 指标 | R12 | R13 | 变化 |
|------|-----|-----|------|
| SR | 68.6% (70/102) | **79.1%** (34/43) | **+10.5pp** |
| ATE (502) | 30 | **7** | **-76.7%** |
| Final 429 | 2 | 2 | 持平 |
| Tier 429 | 64 | **51** | **-20.3%** |
| NVCFPexecTimeout | 2 | 2 | 持平 |
| empty_200 | 4 | 4 | 持平 |
| Fallback | 147 | 158 | +7.5% (重启窗口) |

## 核心判断

SR 从 68.6% → 79.1% (+10.5pp), 趋势明确向上, 逼近 80% 阈值。
ATE 从 30 → 7 (-76.7%), 已经 < 10 达标。
Tier 429 从 64 → 51 (-20.3%), NVCF 限流在持续缓解。
KEY_COOLDOWN_S=180 策略持续生效, 趋势正确。

按 STATE.md R13 决策矩阵: **SR 在 65-80% 继续上升 → 巡检轮, 再等一轮**。

## 本轮改动: 无

## 验证

- `curl /health` OK (nv_gw, port 40006, 5 keys, dsv4p_nv default)
- `docker ps`: nv_gw Up 18 min, hm4104 Up 4h, ms_gw Up 3d
- `docker exec nv_gw env`: KEY_COOLDOWN_S=180, TIER_COOLDOWN_S=180, TIER_TIMEOUT_BUDGET_S=180, UPSTREAM_TIMEOUT=90 ✓

## 下一步 (R14)

SR 79.1% 离 80% 仅一步之遥, 且 ATE 7 < 10 已达标。R14 继续巡检:
- 观察 SR 能否突破 80%+
- 观察 ATE 能否降到 5 以下
- 观察 breaker 是否可能自动恢复 CLOSED (ATE 下降后失败数减少)
- 若 SR 突破 80%+ 且 ATE < 5, 标注"NVCF 限流基本恢复, KEY_COOLDOWN=180 策略成熟"
- 若 SR 仍在 75-80% 平台, 仍为巡检轮, 再等一轮

## 当前参数快照

```
nv_gw (R13: 巡检轮, 无改动, KEY_COOLDOWN_S=180 维持):
  UPSTREAM_TIMEOUT=90
  TIER_TIMEOUT_BUDGET_S=180
  KEY_COOLDOWN_S=180
  TIER_COOLDOWN_S=180
  NV_INTEGRATE_KEY_COOLDOWN_S=90
  NVU_TIER_BUDGET_DSV4P_NV=180
  NVU_STREAM_FB_200K_S=90
  NVU_STREAM_ABSOLUTE_CAP_S=150
  dsv4p_nv function_id=74f02205 (ai-deepseek-v4-pro)
  dsv4p_nv strip_params=[reasoning_effort, stream_options, thinking]
  dsv4p_nv inject={} (普通模式)

hm4104 (不变):
  PRIMARY_HEADER_TIMEOUT=180
  CIRCUIT_FAILURE_THRESHOLD=8
  CIRCUIT_OPEN_S=60
  FALLBACK_RECOVER_S=120
  PRIMARY_STREAM_TIMEOUT_S=90
  FALLBACK_TIMEOUT_S=120
```