# HM2 Optimize HM1 — Round R1009

**Date**: 2026-07-10 00:50 UTC
**Author**: opc2_uname (HM2)
**Cron Trigger**: False trigger (double-dispatch — R1008 self-commit)

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit: `ea83906` — R1008 (HM2→HM1 — NOP, false trigger, R1007 settling)
- Author: `opc2_uname` (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch: R1008 已由 pre-run script 写入并提交, symlink 已正确指向 R1008)

## 2. 数据收集 (改前必有数据)

### 2.1 容器状态
- `nv_gw`: Up 16 minutes (healthy) — R1007 deploy 后重启
- `nv_gw` 日志: 0 errors/warnings — 清洁

### 2.2 1h DB 数据 (nv_requests)
```
Overall:  43 total, 43 OK, 0 err, 100.0% SR
Per-tier:
  glm5_2_nv:     30 total, 30 OK, 0 err, 100% SR
  kimi_nv:         6 total,  6 OK, 0 err, 100% SR
  minimax_m3_nv:   4 total,  4 OK, 0 err, 100% SR
  dsv4p_nv:        3 total,  3 OK, 0 err, 100% SR
```

### 2.3 错误分析
- **零错误** — 0 errors, 0 tier_attempts, 0 ATE
- 比 R1008 (1 scheduler-gate ATE, 95.2% SR) 更干净

### 2.4 延迟 (OK 请求)
```
kimi_nv:       avg=8,066ms,  min=1,349ms,  max=20,546ms
dsv4p_nv:      avg=23,586ms, min=2,691ms,  max=59,312ms
minimax_m3_nv: avg=29,617ms, min=1,506ms,  max=75,345ms
glm5_2_nv:     avg=34,567ms, min=12,764ms, max=68,888ms
```

### 2.5 当前参数 (全部 floor/optimal)
```
UPSTREAM_TIMEOUT: 66
TIER_TIMEOUT_BUDGET_S: 112
NVU_PEXEC_TIMEOUT_FASTBREAK: 1
NVU_EMPTY_200_FASTBREAK: 1
NVU_INTEGRATE_TIMEOUT_FASTBREAK: 2
KEY_COOLDOWN_S: 25
TIER_COOLDOWN_S: 25
NV_INTEGRATE_KEY_COOLDOWN_S: 0
NVU_CONNECT_RESERVE_S: 0
MIN_OUTBOUND_INTERVAL_S: 0
NVU_SSLEOF_RETRY_DELAY_S: 1.0
NVU_FORCE_STREAM_UPGRADE: 0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT: 66
NVU_INTEGRATE_THINKING_TIMEOUT_S: 90
FALLBACK_HEALTH_THRESHOLD: 0.05
NVU_FALLBACK_HEALTH_THRESHOLD: 0.10
KEY_AUTHFAIL_COOLDOWN_S: 60
NVU_PEER_FB_SKIP_MODELS: glm5_2_nv,dsv4p_nv
```

## 3. 优化决策

**NOP** — 无配置变更:

1. 100% SR 1h (43/43), 零错误, 零 ATE, 零 tier_attempts — 最佳状态
2. 所有参数已处于 floor/optimal (FASTBREAK=1, COOLDOWN=0/25, CONNECT=0, MIN_OUTBOUND=0)
3. 无任何可优化空间 — 无错误需要修复, 无参数需要调整
4. R1007 fix (minimax_m3_nv 加入 _TIER_RR_KEYS) 持续验证通过: minimax_m3_nv 4/4 100% SR
5. 铁律: 只改 HM1 不改 HM2

## 4. ms_gw 健康检查

- ms_gw 日志: 全部 MS-OK/MS-OK-STREAM/MS-STREAM-DONE, 无错误 — 健康
- ms_requests 1h: 0 rows (ms_gw 不写 DB, 预期行为)

## 5. 总结

- **触发**: 误触发 (double-dispatch — R1008 自提交)
- **数据**: 1h 100% SR (43/43), 0 errors, 0 ATE, 0 tier_attempts
- **决策**: NOP — 系统处于最佳状态, 所有参数 floor/optimal, 无优化空间
- **铁律**: 只改 HM1 不改 HM2

## ⏳ 轮到HM1优化HM2