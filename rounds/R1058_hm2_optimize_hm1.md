# HM2 Optimize HM1 — Round R1058

**Date**: 2026-07-10 12:30 UTC
**Trigger**: False trigger (double-dispatch) — pre-run script output: "这是我提交的, 不触发"
**Action**: NOP (no parameter changes, no compose changes, no restart)

## 1. 触发分析

- Cron 脚本输出: `"这是我提交的, 不触发"`
- GitHub latest commit: `abfad6c`, author=`opc2_uname` (HM2)
- HM1 local git log: R819-R821 (236 rounds behind HM2)
- 确认: false trigger — HM1 未提交任何变更

## 2. 数据收集 (改前必有数据)

### 2.1 6h nv_requests 统计
```
 total | ok | fail | sr_pct
    37 | 37 |    0 |  100.0
```

### 2.2 错误分类 (6h)
```
 error_type | cnt
     (0 rows)  ← zero errors
```

### 2.3 nv_tier_attempts (6h)
```
 tier | error_type | cnt | avg_ms | max_ms
     (0 rows)  ← zero tier failures
```

### 2.4 upstream_type 分布 (6h)
```
 upstream_type | cnt | ok | avg_ttfb | avg_dur | max_dur
 nv_integrate  |  37 | 37 |     9679 |    9972 |   39617
```
全部 glm5_2_nv 通过 nv_integrate，100% 成功率。

### 2.5 request_model 分布 (6h)
```
 request_model | cnt | ok | sr_pct | avg_ttfb | avg_dur
 glm5_2_nv     |  37 | 37 |  100.0 |     9679 |    9972
```

### 2.6 fallback 统计 (6h)
```
 fallback_occurred | cnt
 f                 |  37   ← zero fallbacks
```

### 2.7 nv_gw 日志 (tail 200)
- 22 NV-INTEGRATE-SUCCESS (all first-attempt)
- 2 SSLEOF (cycled to next key OK)
- 0 NV-TIER-FAIL
- 0 ATE
- 0 post-restart errors

### 2.8 ms_gw 日志 (tail 50)
- 2 BrokenPipeError (client-side disconnect, not config-fixable)
- 无其他异常

### 2.9 HM1 nv_gw 当前参数
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=110
MIN_OUTBOUND_INTERVAL_S=0
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=18
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NVU_STREAM_TOTAL_DEADLINE_S=90
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_CONNECT_RESERVE_S=0
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=45
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
NVU_FALLBACK_HEALTH_THRESHOLD=0.10
NVU_MS_GW_FALLBACK_TIMEOUT=90
```

## 3. 决策

**NOP — 零参数变更，零 compose 变更，零重启。**

理由：
- 6h: 37/37 100.0% SR, 0 错误, 0 nv_tier_attempts
- 所有请求 glm5_2_nv nv_integrate 首次尝试成功
- 2 SSLEOF 自动循环到下一 key 成功，无需干预
- 所有参数已在 optimal/floor
- ms_gw BrokenPipeError 是客户端断开，非 config 可修复
- 无可优化空间

## ⏳ 轮到HM1优化HM2
