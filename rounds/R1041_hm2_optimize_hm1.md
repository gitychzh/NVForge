# HM2 Optimize HM1 — Round R1041

**Date**: 2026-07-10 09:32 UTC  
**Author**: opc2_uname (HM2)  
**Decision**: NOP — false trigger, 0 post-restart requests, container settling

---

## 1. 触发分析

```
cron 脚本输出: "这是我提交的, 不触发"
最新 commit: f44b83f (R1040: HM2→HM1 — NOP, author=opc2_uname)
触发类型: FALSE TRIGGER — HM2 自提交被误判为 HM1 新提交
```

- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发
- 上一轮 R1040 也是 NOP (false trigger, 12min uptime)

---

## 2. 容器状态

| 指标 | 值 |
|------|-----|
| Container | nv_gw |
| Status | Up 18 minutes (healthy) |
| Restart | 2026-07-10 01:08:30 UTC |
| Health | `{"status":"ok"}` |
| Post-restart requests | **0** |
| Error logs | 无 (clean) |

---

## 3. 6h 数据 (—全部为 pre-restart 请求—)

| 指标 | 值 |
|------|-----|
| 总请求 | 71 |
| 成功 (200) | 65 |
| 失败 (!=200) | 6 |
| **成功率** | **91.5%** |

### 6 个失败明细

| 时间 | 模型 | 错误类型 | 耗时 |
|------|------|---------|------|
| 20:16 | dsv4p_nv | all_tiers_exhausted | 61.2s |
| 20:12 | glm5_2_nv | NVStream_TimeoutError | 94.4s |
| 19:38 | glm5_2_nv | stream_total_deadline | 61.9s |
| 19:37 | dsv4p_nv | all_tiers_exhausted | 61.1s |
| 19:36 | glm5_2_nv | NVStream_TimeoutError | 91.5s |
| 19:31 | minimax_m3_nv | stream_total_deadline | 50.5s |

### 按路径分组

| 路径 | 总数 | OK | 成功率 | avg_ttfb | avg_dur |
|------|------|-----|--------|----------|---------|
| nv_integrate | 59 | 55 | 93.2% | 9047ms | 14139ms |
| nvcf_pexec | 9 | 9 | **100%** | 22903ms | 22913ms |
| (ATE) | 3 | 1 | 33.3% | 340ms | 54820ms |

### tier_attempts: 0 行 (无 key 级失败)

---

## 4. 当前配置

```
NVU_STREAM_TOTAL_DEADLINE_S=90
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NVU_MS_GW_FALLBACK_TIMEOUT=90
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=110
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=18
NVU_EMPTY_200_FASTBREAK=2
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
```

---

## 5. 决策

**NOP — 零参数变更。**

原因：
1. 零 post-restart 请求 (18 min 无流量) — 无新数据支撑任何优化
2. 6 个失败全部为 pre-restart 时期的请求，属于 R1039 部署窗口
3. nvcf_pexec 100% SR (9/9) — R1039 移除 dsv4p_nv peer-fb-skip 生效
4. 2 个 stream_total_deadline (50.5s, 61.9s) 均小于 STREAM_TOTAL_DEADLINE_S=90，非 deadline 配置不足
5. 2 个 NVStream_TimeoutError (91.5s, 94.4s) — NVCF SDK 内部流超时，配置已对齐
6. 2 个 all_tiers_exhausted (dsv4p_nv, ~61s) — FALLBACK_GRAPH transient 消失，与配置无关
7. container 日志无 error/warn — 干净
8. ms_gw 健康，EMPTY_200_FASTBREAK_THRESHOLD=3 (已在地板)

**铁律**: 只改 HM1 不改 HM2 ✅  
**改前必有数据**: 已收集 ✅  
**改后必有验证**: N/A (NOP) ✅

---

## ⏳ 轮到HM1优化HM2