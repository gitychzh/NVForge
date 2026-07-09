# HM2 Optimize HM1 — Round R948

**Time:** 2026-07-09 09:05 UTC  
**Trigger:** False trigger (double-dispatch). Cron pre-run script detected `"这是我提交的, 不触发"` but agent was still dispatched. R947 already committed (NOP) with symlink fixed.  
**Decision:** **NOP** — all nv_gw params at floor, 41/41 100% SR 6h, zero errors, zero ATE 6h. 65th consecutive false trigger.

---

## 1. 触发分析

cron 脚本输出:
```
From github.com:gitychzh/NVForge
 * branch            main       -> FETCH_HEAD
HEAD is now at 8b5ec53 R947: HM2→HM1 — NOP (false trigger, 64th consecutive, 38/38 100% 6h SR, all params at floor, zero errors, zero ATE)
[2026-07-09 09:05:18] 这是我提交的, 不触发
```

- 最新 commit = R947 (HM2/opc2_uname 提交的 NOP)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch: R947 已提交+push+symlink 已修复)
- HM1 本地 git log 停留在 R821 (127 轮落后，非阻塞)
- 确认：false trigger

## 2. HM1 nv_gw 数据收集

### 2.1 Docker Logs (最近 100 行)
零 ERROR/WARN/Exception/Traceback。全部请求正常。

### 2.2 容器 Env Vars (关键参数)
```
UPSTREAM_TIMEOUT: 64
TIER_TIMEOUT_BUDGET_S: 114
KEY_COOLDOWN_S: 25
TIER_COOLDOWN_S: 25
MIN_OUTBOUND_INTERVAL_S: 0
NV_INTEGRATE_KEY_COOLDOWN_S: 0
NVU_CONNECT_RESERVE_S: 0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT: 64
NVU_EMPTY_200_FASTBREAK: 3
NVU_PEXEC_TIMEOUT_FASTBREAK: 1
NVU_SSLEOF_RETRY_DELAY_S: 1.0
FALLBACK_HEALTH_THRESHOLD: 0.05
KEY_AUTHFAIL_COOLDOWN_S: 60
NVU_PEER_FB_SKIP_MODELS: glm5_2_nv,dsv4p_nv
NV_INTEGRATE_MODELS: (empty)
NVU_FORCE_STREAM_UPGRADE: 0
```
全部与 R947 一致。

### 2.3 DB — 6h 总体统计
```
total | ok | fail
    41 | 41 |    0
```
100% SR (+3 reqs vs R947 的 38)。

### 2.4 DB — 6h 按路径
```
upstream_type | cnt | ok | avg_ttfb | avg_dur | max_dur
nvcf_pexec    |  41 | 41 |     8255 |    8255 |   67241
```
全部 pexec，零 integrate。avg TTFB=8.3s（正常波动，vs R947 的 7.4s）。max_dur 67.2s 同一 NVCF upstream slow outlier。

### 2.5 DB — 6h 错误分类
```
(0 rows)
```
零错误。

### 2.6 DB — 最近 10 条请求
```
ts               | model       | mapped  | status | ttfb_ms | dur_ms | upstream | 429s
2026-07-09 01:04:02 | glm5_2_nv   | glm5_2_nv | 200 |  24785 |  24785 | nvcf_pexec | 0
2026-07-09 01:03:40 | glm5_2_nv   | glm5_2_nv | 200 |  21271 |  21272 | nvcf_pexec | 0
2026-07-09 01:03:37 | glm5_2_nv   | glm5_2_nv | 200 |   2991 |   2991 | nvcf_pexec | 0
2026-07-09 01:03:21 | glm5_2_nv   | glm5_2_nv | 200 |  12350 |  12351 | nvcf_pexec | 0
2026-07-09 00:33:43 | glm5_2_nv   | glm5_2_nv | 200 |   2678 |   2678 | nvcf_pexec | 0
2026-07-09 00:33:30 | glm5_2_nv   | glm5_2_nv | 200 |  12075 |  12075 | nvcf_pexec | 0
2026-07-09 00:33:21 | glm5_2_nv   | glm5_2_nv | 200 |   5766 |   5767 | nvcf_pexec | 0
2026-07-09 00:03:38 | glm5_2_nv   | glm5_2_nv | 200 |   1916 |   1917 | nvcf_pexec | 0
2026-07-09 00:03:27 | glm5_2_nv   | glm5_2_nv | 200 |  10273 |  10273 | nvcf_pexec | 0
2026-07-09 00:03:21 | glm5_2_nv   | glm5_2_nv | 200 |   3535 |   3536 | nvcf_pexec | 0
```
全部 glm5_2_nv, 全 200 OK, 全 key_cycle_429s=0。p50~3.5s, p95~24.8s。与 R947 相比新增 3 条请求在 01:03-01:04 UTC（3 条均在 21-25s 范围）。

### 2.7 DB — 6h Fallback
```
fallback_occurred | cnt
f                 |  41
```
零 fallback。

### 2.8 DB — 24h 错误全景
```
error_type         | cnt
all_tiers_exhausted |   1
```
仅 1 ATE（与 R947 相同，NVCF 上游侧，非本地 config 可修）。

### 2.9 nv_tier_attempts — 6h
```
(0 rows)
```
零 tier attempts — 所有请求首次即成功。

### 2.10 ms_gw 数据
```
EMPTY_200_FASTBREAK_THRESHOLD=3 (已优化)
KEY_COOLDOWN_S=60
MIN_OUTBOUND_INTERVAL_S=1.0
UPSTREAM_TIMEOUT=300
ms_requests 6h: 0 请求 — 无优化空间
Docker logs: 零 ERROR/WARN
```
与 R947 相同 — 无优化目标。

## 3. 优化分析

### 3.1 Floor 参数检查
所有可调参数已至 floor，与 R947 完全一致。

### 3.2 决策
**NOP（无需优化）**：
1. 6h 41/41 100% SR，零错误，零 ATE，零 key_cycle_429s
2. 所有 floor 参数已在最激进取值无法再降
3. UPSTREAM_TIMEOUT=64 和 BUDGET=114 保持安全余量
4. 24h 仅 1 ATE (NVCF 上游 server-side)
5. Docker logs 零 ERROR/WARN
6. ms_gw 零请求，无优化目标
7. 所有参数与 R947 完全一致，无需任何配置修改

**铁律遵守**: 只改 HM1 不改 HM2。本回合 false trigger + 数据完美，不需任何配置修改。

## 4. 参数状态总结

| 参数 | 当前 | 状态 |
|------|------|------|
| UPSTREAM_TIMEOUT | 64 | 稳定 |
| TIER_TIMEOUT_BUDGET_S | 114 | 稳定 |
| MIN_OUTBOUND_INTERVAL_S | 0 | Floor |
| KEY_COOLDOWN_S | 25 | Floor |
| TIER_COOLDOWN_S | 25 | Floor (dead param) |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | Floor |
| NVU_CONNECT_RESERVE_S | 0 | Floor |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 | 与 UPSTREAM 对齐 |
| NVU_EMPTY_200_FASTBREAK | 3 | 已优化 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 已优化 |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | 已优化 |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | R922 已添加 |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv,dsv4p_nv | R923 已添加 |

## ⏳ 轮到HM1优化HM2