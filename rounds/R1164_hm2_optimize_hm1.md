# HM2 Optimize HM1 — Round R1164 (R1133→33rd false trigger, zombie-only, zero param)

## ⏱️ 判定: NOP (false trigger, 33rd chain of R1133, zombie-only, zero param)

**触发类型**: FALSE TRIGGER — cron 脚本输出 "这是我提交的, 不触发"
**前轮**: R1163 (同样NOP, zombie-only, zero param)

### 铁律: 只改HM1不改HM2 ✓

---

## 1. 6h 数据快照 (2026-07-11 ~11:15 UTC)

```
6h: 38req/14OK(36.8%)/24zombie
  └─ glm5_2_nv: 38/14/24 (36.8% SR) — nv_integrate only
  └─ dsv4p_nv: 0 traffic
  └─ kimi_nv: 0 traffic
  └─ minimax_m3_nv: 0 traffic
  └─ ms_gw: 0 traffic (through nv_gw fallback path)
```

| 维度 | 数值 |
|------|------|
| 总请求 | 38 |
| 成功 | 14 (36.8%) |
| 失败 | 24 (100% zombie_empty_completion) |
| 上游类型 | nv_integrate (100%) |
| fallback_occurred | 0 (全部 f) |
| nv_tier_attempts | 3× 429_integrate_rate_limit (仅) |
| ms_requests | 0 |

## 2. 12h 全景 (含 zombie 前正常窗口)

| request_model | cnt | ok | sr |
|---|---|---|---|
| glm5_2_nv | 140 | 105 | 75.0% |
| dsv4p_nv | 29 | 26 | 89.7% |
| minimax_m3_nv | 9 | 9 | 100.0% |
| kimi_nv | 7 | 7 | 100.0% |

## 3. Hourly SR (12h)

| hour (UTC) | model | cnt | ok | sr |
|---|---|---|---|---|
| 2026-07-11 03:00 | glm5_2_nv | 2 | 1 | 50.0% |
| 2026-07-11 02:00 | glm5_2_nv | 4 | 2 | 50.0% |
| 2026-07-11 01:00 | glm5_2_nv | 4 | 2 | 50.0% |
| 2026-07-11 00:00 | glm5_2_nv | 7 | 1 | 14.3% |
| 2026-07-10 23:00 | glm5_2_nv | 9 | 4 | 44.4% |
| 2026-07-10 22:00 | glm5_2_nv | 9 | 1 | 11.1% | ← zombie 开始
| 2026-07-10 21:00 | glm5_2_nv | 9 | 9 | 100.0% |
| 2026-07-10 20:00 | glm5_2_nv | 7 | 7 | 100.0% |
| 2026-07-10 19:00 | dsv4p_nv | 4 | 4 | 100.0% |
| 2026-07-10 19:00 | glm5_2_nv | 2 | 2 | 100.0% |
| 2026-07-10 18:00 | dsv4p_nv | 6 | 5 | 83.3% |
| 2026-07-10 18:00 | glm5_2_nv | 3 | 3 | 100.0% |
| 2026-07-10 17:00 | glm5_2_nv | 20 | 11 | 55.0% |
| 2026-07-10 16:00 | dsv4p_nv | 1 | 0 | 0.0% |
| 2026-07-10 16:00 | glm5_2_nv | 6 | 5 | 83.3% |
| 2026-07-10 15:00 | dsv4p_nv | 18 | 17 | 94.4% |
| 2026-07-10 15:00 | glm5_2_nv | 58 | 57 | 98.3% |
| 2026-07-10 15:00 | kimi_nv | 7 | 7 | 100.0% |
| 2026-07-10 15:00 | minimax_m3_nv | 9 | 9 | 100.0% |

**关键发现**: 22:00 UTC 前 glm5_2_nv = 98.3% SR (heavy traffic, 58req/h)。22:00 UTC 开始 zombie 爆发 (1/9=11.1%)，input_chars 从 164K 持续增长至 168K。NVCF content-filter 阈值被触发。

## 4. Error 明细 (6h)

| error_type | cnt | finish_reason | avg_input_chars | avg_duration_ms |
|---|---|---|---|---|
| zombie_empty_completion | 24 | stop | 164K→168K (growing) | 3,500-4,700 |

**所有24个失败均为 NVCF content-filter 行为**: glm5_2_nv integrate 模式, NVCF 返回 finish_reason=stop, content_chars=12, input_chars=164K-168K (持续增长: R1162 164K→167K, R1163 165K→168K, R1164 165K→168K)。Gateway zombie 检测正确 — 3-5s 快速中止返回 502+error-chunk (`[NV-ZOMBIE-EMPTY]` + `[NV-ZOMBIE-ERROR-CHUNK]`)。代码级特性，非配置可修复。

## 5. 实时日志

```
glm5_2_nv integrate: 每30min一波2×请求（openclaw 循环, msgs 持续 +1/轮）
交替 zombie + 成功（~63% zombie 率, R1163 55%→R1164 63% zombie 率上升）
input_chars 持续增长: 165385→164969→165559→165646→165733→166427→166410→167104→167613→168388
dsv4p_nv: 0 traffic (6h窗口)
kimi_nv / minimax_m3_nv: 0 traffic
ms_gw: 0 traffic through nv_gw fallback
```

## 6. 容器状态

- 重启时间: 2026-07-10T19:03:27Z (~16h 前)
- 运行状态: Up 8 hours (healthy)
- compose md5: 7975939c245761e451a8813852dcb9bf (自 R1133 未变, 48h+)

## 7. 当前参数 (全部 floor/optimal)

```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=198
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
NVU_MS_GW_FALLBACK_TIMEOUT=180
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms
NVU_TIER_BUDGET_DSV4P_NV=72
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_STREAM_TOTAL_DEADLINE_S=42
NVU_STREAM_FIRST_BYTE_DEADLINE_S=20
NVU_INTEGRATE_KEY_COOLDOWN_S=0
```

## 8. 决策: NOP (Zero Param)

**理由**:
1. 所有失败 = zombie_empty_completion (NVCF content-filter, 代码级特性) — 非配置可修复
2. 12h 全景: 15:00-21:00 UTC glm5_2_nv=98.3% SR (58req/h), dsv4p=94.4% — 正常运作
3. 22:00 UTC 起 zombie 爆发: input_chars 跨过 NVCF content-filter 阈值 (164K+)
4. Gateway zombie 检测正确 — 3-5s 快速中止，error-chunk 注入触发 openclaw fallback 链
5. 0 fallback_occurred (nv_gw 层级) — fallback 由 openclaw provider 链处理, nv_gw 不管理
6. compose md5 自 R1133 未变 (48h+) — 无配置漂移
7. 所有参数在 floor/optimal — 无优化空间
8. NVCF content-filter 对 164K+ 输入返回空响应的行为 — 不可通过 nv_gw 配置修复

**Zero param changes. 铁律: 只改HM1不改HM2 ✓**

## 9. 触发分析

- cron 脚本输出: "这是我提交的, 不触发"
- 脚本正确检测到自提交 (author=opc2_uname) 并标记 "不触发"
- cron 仍被派遣 — 误触发 (R1133 chain 第33轮 false-trigger)
- HM1 compose 未变更，zombie 模式与 R1162/R1163 一致，input_chars 持续增长
- R1133→R1164: 33轮连续 false-trigger NOP, compose md5 不变 48h+
- 前轮锚点: R1161→R1163, 尾部换行修复 (R1162)

## ⏳ 轮到HM1优化HM2