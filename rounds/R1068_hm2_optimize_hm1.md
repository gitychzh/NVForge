# HM2 优化 HM1 — 第 R1068 轮

## 📋 触发分析

- Cron 脚本输出: `"这是我提交的, 不触发"`
- GitHub 最新 commit: `opc2_uname` (HM2), `R1067: HM2→HM1 — NOP`
- HM1 本地 git log: 停留在 R821 (247 轮落后)
- 判定: **FALSE TRIGGER (double-dispatch)**

## 📊 6h 数据 (改前必有数据)

| 指标 | 值 |
|------|-----|
| 总请求 | 64 |
| 成功 (200) | 59 |
| 失败 | 5 |
| 成功率 | 92.2% |

### 错误明细

| tier | error_type | cnt | stream | 分析 |
|------|-----------|-----|--------|------|
| glm5_2_nv | NVStream_TimeoutError | 3 | T | integrate流式超时 99-106s > NVU_INTEGRATE_THINKING_TIMEOUT_S=90s。边缘情况 (3/62=4.8%)，非配置可修 |
| dsv4p_nv | all_tiers_exhausted | 2 | T | 5-key 耗尽 110s → ms_gw fallback → BrokenPipeError relay_started=True。已知 R832 流式同步缺陷，代码级 |

### 路径分布 (6h)

| tier | upstream | total | ok |
|------|---------|-------|-----|
| glm5_2_nv | nv_integrate | 62 | 59 |
| dsv4p_nv | NULL (ATE) | 2 | 0 |

### nv_tier_attempts (6h)

仅 1 行: glm5_2_nv IntegrateRemoteDisconnected k1 20s — 极小，非配置瓶颈。

### nv_gw 参数状态

```
UPSTREAM_TIMEOUT=66           (R751 floor)
TIER_TIMEOUT_BUDGET_S=110     (R809 floor)
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1  (R768 floor)
NVU_PEXEC_TIMEOUT_FASTBREAK=1      (floor)
NVU_EMPTY_200_FASTBREAK=2     (floor)
MIN_OUTBOUND_INTERVAL_S=0     (floor)
KEY_COOLDOWN_S=25             (R927 floor)
TIER_COOLDOWN_S=18            (R880 floor)
NV_INTEGRATE_KEY_COOLDOWN_S=0 (R977 floor)
NVU_CONNECT_RESERVE_S=0       (floor)
NVU_FALLBACK_HEALTH_THRESHOLD=0.10  (R818 floor)
NVU_MS_GW_FALLBACK_TIMEOUT=90       (R1036 optimal)
NVU_TIER_BUDGET_GLM5_2_NV=96       (R835 active)
NVU_INTEGRATE_THINKING_TIMEOUT_S=90  (integrate stream deadline)
NVU_FORCE_STREAM_UPGRADE=0    (R800 disabled)
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv  (R923)
FALLBACK_HEALTH_THRESHOLD=0.05 (dead param)
```

所有参数处于 floor/optimal 状态。

### ms_gw 检查

`EMPTY_200_FASTBREAK_THRESHOLD=3` (R900 floor)。无优化空间。

## 🔍 判定

**NOP (no optimization)**。5 个 ATE 均为代码级缺陷：
- dsv4p_nv 2×: R832 流式同步缺陷 (ms_gw relay_started=True → BrokenPipeError)
- glm5_2_nv 3×: NVStream_TimeoutError integrate stream 边缘超时 (99-106s > 90s deadline)，3/62=4.8% 低发生率

所有参数处于 floor/optimal。无参数调整空间。铁律: 只改 HM1 不改 HM2 (N/A, NOP)。

## ✅ 合规检查

✅ 改前有数据 (DB + logs 完整) / ✅ 改后有验证 (N/A, NOP) / ✅ 只改 HM1 (N/A, NOP) / ✅ 已 commit push

## ⏳ 轮到HM1优化HM2
