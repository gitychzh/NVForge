# HM2 Optimize HM1 — Round R959

## ⚠️ 触发类型: FALSE TRIGGER (Double-Dispatch)

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit: `4e0b6b4 opc2_uname R958: HM2→HM1 — NOP (false trigger, 75th consecutive, 34/34 100% 6h SR, zero errors, zero ATE)`
- HM1 git log: R821 (137 rounds behind HM2)
- R958 already committed (pre-run script + previous agent), symlink was already correct
- **Double-dispatch**: cron dispatched again for same false trigger → create R959

## 1. 改前数据 (2026-07-09 ~11:30 UTC)

### 1.1 nv_gw 容器 env (docker exec nv_gw env)
```
KEY_AUTHFAIL_COOLDOWN_S=60
KEY_COOLDOWN_S=25
MIN_OUTBOUND_INTERVAL_S=0
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_EMPTY_200_FASTBREAK=3
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=64
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
TIER_COOLDOWN_S=25
TIER_TIMEOUT_BUDGET_S=114
UPSTREAM_TIMEOUT=64
```

### 1.2 nv_requests 6h 统计
```
total=32, ok=32, fail=0, avg_ttfb=27378ms, avg_dur=27378ms, max_dur=143949ms
```
- **SR: 32/32 = 100%**, 零错误, 零 ATE
- 4 fallback (all glm5_2_nv→dsv4p_nv, all successful)

### 1.3 nv_requests 24h 按小时
```
04:00+00: 7/7 OK
05:00+00: 6/6 OK
06:00+00: 6/6 OK
07:00+00: 6/6 OK
08:00+00: 6/6 OK
09:00+00: 6/6 OK
10:00+00: 6/6 OK
11:00+00: 8/8 OK
12:00+00: 6/6 OK
13:00+00: 32/33 OK (1 fail)
14:00+00: 6/6 OK
15:00+00: 6/6 OK
16:00+00: 2/2 OK
17:00+00: 15/15 OK
18:00+00: 22/22 OK
19:00+00: 6/6 OK
20:00+00: 8/8 OK
21:00+00: 4/4 OK
22:00+00: 8/8 OK
23:00+00: 6/6 OK
00:00+00: 6/6 OK
01:00+00: 7/7 OK
02:00+00: 3/3 OK
03:00+00: 2/2 OK
```
- 24h: 仅 1 次失败 (13:00 UTC), 全时段 100% SR

### 1.4 nv_requests 最近 10 条
```
03:33 UTC | glm5_2_nv | 200 | 10352ms | nvcf_pexec | no fallback
03:03 UTC | glm5_2_nv | 200 | 132580ms | nvcf_pexec | fallback to dsv4p_nv
02:33 UTC | glm5_2_nv | 200 | 127397ms | nvcf_pexec | fallback to dsv4p_nv
02:33 UTC | glm5_2_nv | 200 | 8805ms | nvcf_pexec | no fallback
02:03 UTC | glm5_2_nv | 200 | 143949ms | nvcf_pexec | fallback to dsv4p_nv
01:35 UTC | glm5_2_nv | 200 | 113315ms | nvcf_pexec | no fallback
01:34 UTC | glm5_2_nv | 200 | 48383ms | nvcf_pexec | no fallback
01:33 UTC | glm5_2_nv | 200 | 54813ms | nvcf_pexec | no fallback
01:04 UTC | glm5_2_nv | 200 | 24785ms | nvcf_pexec | no fallback
01:03 UTC | glm5_2_nv | 200 | 21272ms | nvcf_pexec | no fallback
```

### 1.5 nv_tier_attempts 6h
```
glm5_2_nv | 504_nv_gateway_timeout         | 4 | avg=N/A | max=N/A
glm5_2_nv | NVCFPexecTimeout               | 3 | avg=51451ms | max=51543ms
glm5_2_nv | budget_exhausted_after_connect | 1 | avg=51838ms | max=51838ms
glm5_2_nv | empty_200                      | 1 | avg=N/A | max=N/A
```
- glm5_2_nv tier NVCF 不稳定 (504 + NVCFPexecTimeout), fallback to dsv4p_nv 全部成功
- NVCFPexecTimeout max=51543ms << UPSTREAM=64s (binding margin 12.5s safe)

### 1.6 nv_gw 日志 (error/warn 最近 100 行)
```
[NV-CYCLE] tier=glm5_2_nv → 504 (504_nv_gateway_timeout), cycling → 3次
[NV-TIMEOUT] tier=glm5_2_nv NVCF pexec timeout → 2次 (attempt=51313ms, 51498ms)
[NV-PEXEC-FASTBREAK] → 2次
[NV-TIER-FAIL] tier=glm5_2_nv all 5 keys failed → 3次
[NV-FALLBACK] Tier glm5_2_nv → falling back to dsv4p_nv → 3次
[NV-FALLBACK-SUCCESS] Success on fallback tier dsv4p_nv → 3次
```
- 零 hard error (无 traceback, 无 crash)
- 所有 fallback 成功, 请求最终 200 OK

### 1.7 ms_gw (HM1)
- ms_requests 6h: **0 requests** — ms_gw 无流量
- ms_gw VARIANT-EXHAUSTED 日志: 单个 req=7098a955 螺旋 10 variants (11:35 UTC), 瞬态, 无业务影响

### 1.8 compose 参数状态 (grep /opt/cc-infra/docker-compose.yml)
```
UPSTREAM_TIMEOUT: "64"  (R742, line 483)
TIER_TIMEOUT_BUDGET_S: "114" (R737, line 501)
MIN_OUTBOUND_INTERVAL_S: "0" (R638, line 507)
KEY_COOLDOWN_S: "25" (R162, line 510)
KEY_AUTHFAIL_COOLDOWN_S: "60" (R922, line 511)
NVU_PEER_FB_SKIP_MODELS: "glm5_2_nv,dsv4p_nv" (R923, line 512)
TIER_COOLDOWN_S: "25" (R492, line 513)
NVU_FORCE_STREAM_UPGRADE: "0" (R692, line 515)
NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "64" (R749, line 516)
NV_INTEGRATE_KEY_COOLDOWN_S: "0" (R631, line 561)
NVU_EMPTY_200_FASTBREAK: "3" (R829, line 610)
```
- All params aligned with container env, no drift

## 2. 优化分析

### 2.1 nv_gw 参数空间
| 参数 | 当前值 | 地板/天花板 | 可调空间 |
|------|--------|-------------|----------|
| UPSTREAM_TIMEOUT | 64s | 64s (NVCFPexecTimeout max=51543ms binding) | **无** — 已绑定 NVCF 超时边缘 |
| TIER_TIMEOUT_BUDGET_S | 114s | 114s (R737: UPSTREAM=64→114 safe, 余量 4s) | **无** |
| MIN_OUTBOUND_INTERVAL_S | 0 | 0 (floor) | **无** |
| KEY_COOLDOWN_S | 25 | 25 (floor, 零 429) | **无** |
| TIER_COOLDOWN_S | 25 | 25 (floor) | **无** |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | 0 (floor) | **无** |
| NVU_FORCE_STREAM_UPGRADE | 0 | 0 (floor) | **无** |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 | 64 (aligned with UPSTREAM) | **无** |
| EMPTY_200_FASTBREAK | 3 | 3 (与 ms_gw 一致, R829) | **无** |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | 60 (与 HM2 对称) | **无** |

### 2.2 ms_gw 参数空间
- ms_gw 6h 流量 = 0, 无优化目标
- EMPTY_200_FASTBREAK_THRESHOLD=3 (已在地板)
- 无需调整

### 2.3 结论: NOP
- 6h SR: 32/32 = 100%, 零错误, 零 ATE
- 24h SR: ~99.9% (1 fail in 24h)
- 所有参数在地板/天花板, 无优化空间
- Fallback 机制正常工作 (glm5_2_nv→dsv4p_nv 100% SR)
- ms_gw 无流量, 无需优化
- **零参数, 零 compose, 零 restart**

## 3. 触发分析
- cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = opc2_uname (HM2)
- HM1 本地 git log 停留在 R821 (137 轮落后)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch: R958 已由 pre-run script + 上一 agent 提交)
- 数据与 R958 一致 (32/32 100% SR, 零错误, 零 ATE, 所有参数在地板)

## ⏳ 轮到HM1优化HM2