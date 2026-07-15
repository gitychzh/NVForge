# R1478: HM2→HM1 — NOP (false trigger, R1474 peer-fb verified, all params floor/optimal)

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit `6cdd7f3` (R1477) author = `opc2_uname` (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch after R1477)
- 无 HM1 新 commit

## 2. 改前数据 (2026-07-16 00:30 UTC, 6h)

### 2.1 nv_requests 概览

| 指标 | 值 |
|------|-----|
| 总请求 | 42 |
| 成功 | 19 (45.2% SR) |
| 失败 | 23 |
| Post-restart | 6 req / 4 OK (66.7% SR) |
| Pre-restart | 36 req / 15 OK (41.7% SR) |

### 2.2 Per-model 明细 (6h)

| Model | Req | OK | SR | Avg Dur |
|-------|-----|-----|-----|---------|
| glm5_2_nv | 25 | 13 | 52.0% | 15,736ms |
| dsv4p_nv | 17 | 6 | 35.3% | 58,074ms |

### 2.3 Error 分类

| Error | Count | Model | Fixable? |
|-------|-------|-------|----------|
| zombie_empty_completion | 15 | glm5_2_nv(12) + dsv4p_nv(3) | ❌ NVCF content-filter (R1107) |
| all_tiers_exhausted | 8 | dsv4p_nv(8) | ✅ R1474 fix (peer-fb rescues) |

### 2.4 Post-restart 验证 (R1474 fix)

| Request | Model | Status | Result |
|---------|-------|--------|--------|
| 708a98fc | glm5_2_nv | 200 | OK (17,639ms) |
| 26c2bc06 | glm5_2_nv | 502 | zombie_empty_completion (NVCF content-filter) |
| 518ee106 | dsv4p_nv | 200 | ATE → peer-fb rescue (11,887ms, ttfb=9ms) |
| b4d5d485 | dsv4p_nv | 200 | ATE → peer-fb rescue (2,595ms, ttfb=7ms) |
| (new) | glm5_2_nv | 200 | integrate k3 success (4,323ms) |
| (new) | glm5_2_nv | 200 | integrate k4 success (5,712ms) |

### 2.5 nv_tier_attempts (6h)

0 条 — clean key pool, 零 cooldown cycle.

### 2.6 ms_gw (6h)

| 指标 | 值 |
|------|-----|
| 总请求 | 22 |
| 成功 | 19 (86.4% SR) |

### 2.7 实时日志 (最近 50 行)

```
[00:07] dsv4p_nv: k1 empty_200 → all keys cooling 15s → peer-fb rescue OK (2.6s/11.9s)
[00:33] glm5_2_nv: integrate k3/k4 success, 1× zombie (NVCF content-filter)
健康: 极佳 — 零 NVCFPexecTimeout, 零 504, 零 429
```

### 2.8 HM1 nv_gw 当前配置

```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=205
NVU_TIER_BUDGET_DSV4P_NV=66
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
FALLBACK_HEALTH_THRESHOLD=0.05
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_PEER_FB_SKIP_MODELS=(empty)
NVU_MS_GW_FALLBACK_TIMEOUT=120
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms
NV_INTEGRATE_KEY_COOLDOWN_S=0
NV_INTEGRATE_MODELS=glm5_2_nv
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=15
MIN_OUTBOUND_INTERVAL_S=0
NVU_CONNECT_RESERVE_S=0
KEY_AUTHFAIL_COOLDOWN_S=60
```

## 3. 参数状态评估

| 参数 | 当前值 | 状态 | 理由 |
|------|--------|------|------|
| UPSTREAM_TIMEOUT | 66 | floor | |
| TIER_TIMEOUT_BUDGET_S | 205 | optimal | peer-fb: 205-66=139s > PEER_FB=66 ✓ |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | floor = UPSTREAM | R1440 BUDGET floor pattern |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal | integrate timeout + buffer |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor | R997 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor | R1010 |
| NVU_EMPTY_200_FASTBREAK | 2 | floor (no-op) | R1039 bug: pexec ignores, always threshold=1 |
| TIER_COOLDOWN_S | 15 | floor | R1103 |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | = UPSTREAM | |
| NVU_PEER_FB_SKIP_MODELS | (empty) | optimal | all models enabled |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | sufficient | |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv,kimi_nv | optimal | dsv4p_nv removed (R1474) |
| KEY_COOLDOWN_S | 25 | floor | |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor | |
| NVU_CONNECT_RESERVE_S | 0 | floor | |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor | |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | stable | R922 防御参数 |

## 4. 决策: NOP

**R1474 peer-fb fix 已验证工作，所有参数 at floor/optimal。**

1. **R1474 peer-fb 验证**: 2/2 dsv4p_nv ATE → peer-fb rescue (∼2.6s, ∼11.9s)，确认 dsv4p_nv 移除自 MODELMAP 后 peer-fb 路径有效。
2. **15 zombie**: NVCF content-filter (R1107 code-level)，不可配置修复。
3. **8 ATE**: 全部 pre-restart (R1474 部署前)，R1474 fix 已处理。
4. **6 post-restart 请求**: 4 OK (66.7% SR)，包括 2 peer-fb rescue。
5. **所有参数 at floor/optimal** — 零优化空间。零漂移。
6. **compose md5**: e1f9026c (unchanged from R1477)。

**无新数据，无 HM1 commit，无优化空间。NOP。**
## ⏳ 轮到HM1优化HM2
