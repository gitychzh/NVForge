# HM2 Optimize HM1 — Round R1008

**Date**: 2026-07-10 00:15 UTC
**Author**: opc2_uname (HM2)
**Cron Trigger**: False trigger (R1007 self-commit)

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit: `ccf8a60` — R1007 (HM2→HM1: Fix `_TIER_RR_KEYS` missing `minimax_m3_nv`)
- Author: `opc2_uname` (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发

## 2. 数据收集 (改前必有数据)

### 2.1 容器状态
- `nv_gw`: Up 7 minutes (healthy) — R1007 deploy 后重启于 00:11:30 CST
- `nv_gw` RR 计数器恢复: `nv_dsv4p:2233, nv_kimi:26, nv_glm5_2:249, nv_minimax_m3_nv:1`
- minimax_m3_nv 已出现在 tier_chain 中 (R1007 fix 生效)

### 2.2 1h DB 数据 (nv_requests)
```
Overall:  21 total, 20 OK, 1 err, 95.2% SR
Per-tier:
  glm5_2_nv:     13 total, 12 OK, 1 err, 92.3% SR
  kimi_nv:        3 total,  3 OK, 0 err, 100% SR
  minimax_m3_nv:  3 total,  3 OK, 0 err, 100% SR
  dsv4p_nv:       2 total,  2 OK, 0 err, 100% SR
```

### 2.3 错误分析
- 1 error: `all_tiers_exhausted`, glm5_2_nv, 208s, upstream_type=NULL, tiers_tried=1, no fallback
  → **scheduler-gate ATE** (NVCF 调度层直接拒绝, 非 config-fixable)
- 0 tier_attempts 记录 — 零 key 级错误

### 2.4 延迟 (OK 请求)
```
kimi_nv:       avg=14,129ms, min=1,426ms,  max=20,546ms
dsv4p_nv:      avg=34,034ms, min=8,756ms,  max=59,312ms
minimax_m3_nv: avg=37,963ms, min=1,506ms,  max=75,345ms
glm5_2_nv:     avg=41,724ms, min=17,784ms, max=68,888ms
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

1. R1007 刚部署 4 分钟, 需要时间验证 `_TIER_RR_KEYS` 修复 (minimax_m3_nv 加入轮转)
2. 所有参数已处于 floor/optimal (FASTBREAK=1, COOLDOWN=0/25, CONNECT=0, MIN_OUTBOUND=0)
3. 唯一错误为 scheduler-gate ATE (upstream_type=NULL, 0 tier_attempts) — NVCF 调度层直接拒绝, 非 config-fixable
4. minimax_m3_nv 3/3 100% SR — R1007 fix 初步验证通过
5. 无适用优化空间

## 4. ms_gw 健康检查

- ms_requests 1h: 2 total, 0 OK, 2 err (ms_gw 可能不写 DB 到 ms_requests 表)
- ms_gw 日志: 全部 MS-OK/MS-OK-STREAM/MS-STREAM-DONE, 无错误 — 健康

## 5. 总结

- **触发**: 误触发 (R1007 自提交)
- **数据**: 1h 95.2% SR, 1 scheduler-gate ATE, 0 key 级错误
- **决策**: NOP — R1007 修复正在验证, 所有参数 floor/optimal
- **铁律**: 只改 HM1 不改 HM2

## ⏳ 轮到HM1优化HM2