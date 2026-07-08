# HM2 Optimize HM1 — Round R939

## ⏱️ 时间
- 触发: cron 2026-07-09 07:55 UTC (预运行脚本判定: HM1新commit eb73459)
- 执行: 2026-07-09 ~07:56 UTC
- 数据收集窗口: 6h (01:55-07:55 UTC)

## 🔍 触发分析
cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2自身)
- 最新 commit = eb73459 R938: HM2→HM1 — NOP
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (第56次连续false trigger)
- 预运行脚本已写入R938 NOP，symlink已指向R938
- agent到达时symlink正确，R938已committed → 双次派遣(double-dispatch)

## 📊 HM1 nv_gw 数据

### Docker Logs (最近100行)
- error/warn/traceback/fail/exception: **0条** — 完全干净

### 容器env (docker exec nv_gw env)
- 参数全部已确认:
  - UPSTREAM_TIMEOUT: 64
  - TIER_TIMEOUT_BUDGET_S: 114
  - MIN_OUTBOUND_INTERVAL_S: 0 (floor ✓)
  - KEY_COOLDOWN_S: 25 (floor ✓)
  - TIER_COOLDOWN_S: 25 (floor ✓)
  - NV_INTEGRATE_KEY_COOLDOWN_S: 0 (floor ✓)
  - NVU_CONNECT_RESERVE_S: 0 (floor ✓)
  - NVU_FORCE_STREAM_UPGRADE_TIMEOUT: 64 (aligned with UPSTREAM=64 ✓)
  - NVU_EMPTY_200_FASTBREAK: 3 (floor ✓)
  - NVU_PEXEC_TIMEOUT_FASTBREAK: 1
  - NVU_SSLEOF_RETRY_DELAY_S: 1.0 (floor ✓)
  - FALLBACK_HEALTH_THRESHOLD: 0.05 (near floor ✓)
  - NVU_PEER_FALLBACK_TIMEOUT: 45 (aligned ✓)
  - KEY_AUTHFAIL_COOLDOWN_S: 60 (already added R922 ✓)
  - NVU_PEER_FB_SKIP_MODELS: glm5_2_nv,dsv4p_nv

### DB (hermes_logs)

| 窗口 | 总请求 | 成功 | 失败 | SR% |
|------|--------|------|------|-----|
| 6h | 54 | 54 | 0 | **100.0%** |
| 24h | 197 | 196 | 1 | 99.5% |

- **6h错误**: 0条 (zero-error regime)
- **24h错误**: 1条 ATE @ 2026-07-08 13:21 UTC — glm5_2_nv all_tiers_exhausted (与R938-R927同一事件，NVCF upstream transient)
- **tier_attempts 6h**: dsv4p_nv NVCFPexecTimeout ×1 (52849ms), dsv4p_nv empty_200 ×1
- All upstream via nvcf_pexec (NV_INTEGRATE_MODELS="" — 全pexec)

### 延迟分布 (6h, status=200, nvcf_pexec)
| p50 | p90 | p95 | p99 | min | max |
|-----|-----|-----|-----|-----|-----|
| 5908ms | 33987ms | 54636ms | 120515ms | 1920ms | 120515ms |

- 最近10条: 全部 glm5_2_nv → nvcf_pexec, status=200, ttfb 1919-67241ms, key_cycle_429s=0
- NVCFPexecTimeout max=52849ms < UPSTREAM=64s safe

### ms_gw (6h/24h)
- 总请求: 0 — 无fallback需求, ms_gw闲置
- ms_gw env: ALL_EXHAUSTED_COOLDOWN_S=30, EMPTY_200_FASTBREAK_THRESHOLD=3, KEY_COOLDOWN_S=60, UPSTREAM_TIMEOUT=300

## 🎯 决策: NOP — 无可优化参数

### 参数诊断
所有可调参数皆已至 floor 或最优值:

| 参数 | 当前值 | floor/optimal | 剩余优化空间 |
|------|--------|---------------|-------------|
| UPSTREAM_TIMEOUT | 64 | aligned | 0 — NVCFPexecTimeout max=52849ms < 64s, 无需扩展; 不可缩减(64s已为tier budget约束) |
| TIER_TIMEOUT_BUDGET_S | 114 | optimal | 0 — UPSTREAM=64 → 2-tier minimum=128s, BUDGET=114 already tight (1 tier full + 50s partial) |
| MIN_OUTBOUND_INTERVAL_S | 0 | **floor** | 0 ✓ |
| KEY_COOLDOWN_S | 25 | **floor** | 0 ✓ |
| TIER_COOLDOWN_S | 25 | **floor** | 0 ✓ |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | **floor** | 0 ✓ |
| NVU_CONNECT_RESERVE_S | 0 | **floor** | 0 ✓ |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 | aligned=UPSTREAM | 0 ✓ |
| NVU_EMPTY_200_FASTBREAK | 3 | **floor** | 0 ✓ |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | optimal | 0 — per FASTBREAK tuning decisions, 1 is calibrated |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | **floor** | 0 ✓ |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | near-floor | 0 — 0.05 is near floor; 0.0 would disable all fallback filtering |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | aligned | 0 — 45 = UPSTREAM(40 on HM2 peer) + reserve |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | **floor** | 0 ✓ (R922 added, already at floor) |

**结论**: nv_gw 所有参数已达 floor/optimal。零错误持续regime (54/54 100% 6h SR, 0 log errors)。唯一24h失败为昨天的单一NVCF upstream事件(非本地可修)。无任何优化操作空间。

### ms_gw
- 0请求24h — 无需优化

## 🏷️ 本次操作
- **NOP** — 无参数修改
- 仅记录R939回合文件（数据收集+分析, 确认无可优化参数）
- 第56次连续false trigger dispatch

## 🔒 铁律遵守
- ✅ 改前必有数据: SSH到HM1收集docker logs/env + DB 6h/24h数据
- ✅ 改后必有验证: N/A (NOP, 无修改)
- ✅ 聚焦nv_gw: 仅检查nv_gw+ms_gw数据
- ✅ 所有修改写入仓库: 本回合记录写入R939
- ✅ 只改HM1不改HM2: 本回合无任何修改

## ⏳ 轮到HM1优化HM2
