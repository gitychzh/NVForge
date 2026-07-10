# HM2 Optimize HM1 — Round R1061

## ⚠️ 触发判定: FALSE TRIGGER (double-dispatch)

- **cron 脚本输出**: `"这是我提交的, 不触发"`
- **最新 commit**: `fc4f4b1` — author=opc2_uname (HM2), R1060 NOP
- **判定**: 自提交误触发, HM1 未提交新内容

## 1. 6h 数据概览

| 指标 | 值 |
|------|-----|
| 总请求 | 42 |
| 成功 | 42 (100.0%) |
| 失败 | 0 |
| nv_tier_attempts | 0 行 |
| 容器运行时 | ~4h |

## 2. 上游路径分布

| upstream_type | 请求数 | 成功率 | avg_ttfb | avg_dur | max_dur |
|--------------|--------|--------|----------|---------|---------|
| nv_integrate | 42 | 100% | 9,684ms | 10,467ms | 39,617ms |

## 3. 最近请求 (top 10)

| 时间 | 模型 | 状态 | ttfb | dur | 上游 |
|------|------|------|------|-----|------|
| 05:07:00 | glm5_2_nv | 200 | 10,277ms | 32,322ms | nv_integrate |
| 05:06:57 | glm5_2_nv | 200 | 3,409ms | 3,409ms | nv_integrate |
| 05:06:51 | glm5_2_nv | 200 | 4,760ms | 4,761ms | nv_integrate |
| 05:06:43 | glm5_2_nv | 200 | 7,642ms | 7,642ms | nv_integrate |
| 05:03:59 | glm5_2_nv | 200 | 6,368ms | 6,369ms | nv_integrate |
| 05:03:44 | glm5_2_nv | 200 | 12,929ms | 12,930ms | nv_integrate |
| 05:03:33 | glm5_2_nv | 200 | 7,838ms | 7,839ms | nv_integrate |
| 05:03:24 | glm5_2_nv | 200 | 5,089ms | 5,089ms | nv_integrate |
| 04:33:54 | glm5_2_nv | 200 | 10,013ms | 10,014ms | nv_integrate |
| 04:33:41 | glm5_2_nv | 200 | 12,490ms | 12,490ms | nv_integrate |

## 4. 24h 全景

| 指标 | 值 |
|------|-----|
| 总请求 | 638 |
| 成功 | 592 (92.8%) |
| 失败 | 46 |
| ATE | 40 (pre-restart) |
| NVStream_TimeoutError | 3 (pre-restart) |
| stream_total_deadline | 3 (pre-restart) |

24h 失败均为容器重启前旧数据，重启后 6h 100% SR。

## 5. nv_tier_attempts

0 行 (6h) — 零错误。24h 中所有 16 行均为重启前旧数据。

## 6. 日志关键信号

- 全部 glm5_2_nv integrate 模式，100% 首键成功
- 仅 2 次 SSLEOF (k2) → 立即 cycle 到 k3 OK
- 零 error/warn/fail/timeout/empty/ATE/BrokenPipe
- 容器重启后 ~4h 完美运行
- 连续 10 轮 (R1052-R1061) 均为 NOP false trigger

## 7. 当前 HM1 nv_gw 参数

```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=110
TIER_COOLDOWN_S=18
KEY_COOLDOWN_S=25
KEY_AUTHFAIL_COOLDOWN_S=60
NV_INTEGRATE_KEY_COOLDOWN_S=0
MIN_OUTBOUND_INTERVAL_S=0
NVU_CONNECT_RESERVE_S=0
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_FALLBACK_HEALTH_THRESHOLD=0.10
FALLBACK_HEALTH_THRESHOLD=0.05
NVU_MS_GW_FALLBACK_TIMEOUT=90
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,dsv4p_nv:dsv4p_ms,kimi_nv:kimi_ms
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006
NVU_PEER_FALLBACK_TIMEOUT=45
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
```

## 8. 决策: NOP (Zero Param)

- **铁律**: 只改 HM1，绝不改 HM2
- 6h 数据: 42/42 100% SR, 0 tier_attempts, 0 error
- 所有参数已处于 optimal/floor
- SSLEOF 2/500 (0.4%) on k2, NVU_SSLEOF_RETRY_DELAY_S=1.0 完美处理
- 零参数变更 — 无优化空间，任何改动都是回归
- 连续 10 轮 (R1052-R1061) 均为 NOP false trigger
- 脚本应修复 double-dispatch 检测逻辑，避免 HM2 自提交触发 HM2 优化轮次

## ⏳ 轮到HM1优化HM2