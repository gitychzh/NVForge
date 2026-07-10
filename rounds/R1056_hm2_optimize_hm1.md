# HM2 Optimize HM1 — Round R1056

**Date**: 2026-07-10 12:10  
**Trigger**: cron dispatch (false trigger, double-dispatch)  
**Author**: opc2_uname (HM2)  
**Decision**: NOP — zero param, zero compose, zero restart

---

## 1. 触发分析

- **cron 脚本输出**: `"这是我提交的, 不触发"`
- **最新 commit author**: `opc2_uname` (HM2) — R1055
- **HM1 本地 git log**: 停在 R821 (234 轮落后)
- **判定**: 误触发 / double-dispatch — HM1 未提交任何新内容

---

## 2. HM1 数据收集 (改前必有数据)

### 2.1 6h 总体统计
```
total | ok | fail | sr_pct
    38 | 38 |    0 | 100.0
```

### 2.2 6h 按 tier
```
tier_model | total | ok | fail | sr_pct
glm5_2_nv  |    38 | 38 |    0 | 100.0
```

### 2.3 6h 按 upstream
```
tier_model | upstream     | total | ok | avg_ms | max_ms
glm5_2_nv  | nv_integrate |    38 | 38 |   9642 |  39617
```

### 2.4 nv_tier_attempts (6h)
```
0 rows — 零失败尝试
```

### 2.5 最近错误 (DB)
```
全部 12h+ 过时 (2026-07-09 19:04-20:17):
- dsv4p_nv ATE 61249ms (all_tiers_exhausted)
- glm5_2_nv integrate timeout 94360ms (NVStream_TimeoutError)
- glm5_2_nv integrate deadline 61948ms (stream_total_deadline)
- dsv4p_nv ATE 61105ms (all_tiers_exhausted)
- glm5_2_nv integrate timeout 91529ms (NVStream_TimeoutError)
- minimax_m3_nv integrate deadline 50505ms (stream_total_deadline)
- minimax_m3_nv ATE 151405ms (all_tiers_exhausted)
- glm5_2_nv ATE 151242ms (all_tiers_exhausted)
- kimi_nv ATE 60811ms (all_tiers_exhausted)
- dsv4p_nv ATE 61151ms (all_tiers_exhausted)
```

### 2.6 docker logs nv_gw (最近100行)
```
[10:34:12.9] [NV-INTEGRATE-ERR] tier=glm5_2_nv k2 SSLEOFError: UNEXPECTED_EOF_WHILE_READING
[10:34:12.9] [NV-INTEGRATE-SSL-CYCLE] tier=glm5_2_nv k2 SSL error (5002ms) — cycle
```
- 仅 2 次 SSLEOF (k2, 良性, 自循环到 k3 OK)
- 0 NV-TIER-FAIL

### 2.7 HM1 nv_gw env (关键参数)
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=110
TIER_COOLDOWN_S=18
KEY_COOLDOWN_S=25
KEY_AUTHFAIL_COOLDOWN_S=60
MIN_OUTBOUND_INTERVAL_S=0
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_CONNECT_RESERVE_S=0
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_STREAM_TOTAL_DEADLINE_S=90
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006
NVU_PEER_FALLBACK_TIMEOUT=45
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,dsv4p_nv:dsv4p_ms,kimi_nv:kimi_ms
NVU_MS_GW_FALLBACK_TIMEOUT=90
NVU_FALLBACK_HEALTH_THRESHOLD=0.10
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NV_INTEGRATE_MODELS=glm5_2_nv,minimax_m3_nv
```

---

## 3. 分析

完美状态:
- 6h 100% SR, 0 错误, 0 nv_tier_attempts
- 仅 2 SSLEOF (k2, 良性自循环, 不影响)
- 0 NV-TIER-FAIL
- 所有参数已处于 optimal/floor
- 无优化空间

---

## 4. 决策

**NOP** — zero param, zero compose, zero restart.

铁律: 只改HM1不改HM2 ✅

---

## ⏳ 轮到HM1优化HM2
