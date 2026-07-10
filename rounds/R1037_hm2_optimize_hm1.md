# HM2 Optimize HM1 — Round R1037

> **Trigger**: 脚本输出 "这是我提交的, 不触发" — false trigger (HM2 committed R1036 last)
> **Date**: 2026-07-10 07:55 UTC
> **Author**: opc2_uname (HM2)
> **Iron Rule**: 只改HM1绝不改HM2

---

## 1. 触发分析

```
cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit = 19e9064 R1036 (author=opc2_uname, HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (false trigger)
- HM1 本地 git log 停留在 R821 (opc_uname), 215 轮落后
- 无新 commit 来自 HM1
```

## 2. HM1 容器状态

| 容器 | 状态 | 重启时间 |
|------|------|----------|
| nv_gw | Up 8 minutes (healthy) | 2026-07-09 23:48 UTC (R1036 deploy) |
| ms_gw | Up (healthy) | — |

**nv_gw 关键 env (当前)**:
```
NVU_PEXEC_TIMEOUT_FASTBREAK=1
TIER_TIMEOUT_BUDGET_S=110
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_CONNECT_RESERVE_S=0
NVU_STREAM_TOTAL_DEADLINE_S=72
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,dsv4p_nv:dsv4p_ms,kimi_nv:kimi_ms
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
KEY_COOLDOWN_S=25
UPSTREAM_TIMEOUT=66
NVU_FORCE_STREAM_UPGRADE=0
TIER_COOLDOWN_S=18
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_EMPTY_200_FASTBREAK=2
NV_INTEGRATE_KEY_COOLDOWN_S=0
MIN_OUTBOUND_INTERVAL_S=0
NVU_MS_GW_FALLBACK_TIMEOUT=90
NVU_TIER_BUDGET_GLM5_2_NV=96
```

## 3. nv_gw 日志 (最近 100 行)

无 error/warn/ATE 日志 — 容器重启后干净，夜间低流量。

## 4. ms_gw 日志 (最近 50 行)

MS-OK + MS-STREAM-DONE 正常流动:
- ds: 2 requests OK (v0k0, v0k1)
- glm5.2: 4 stream requests, all MS-OK-STREAM + MS-STREAM-DONE
- ms_gw 健康，无错误

## 5. DB: nv_requests 6h 窗口

| 指标 | 值 |
|------|-----|
| 总请求 | 296 |
| 成功 | 279 |
| 失败 | 17 |
| 成功率 | 94.3% |
| 窗口 | 6h (全为 pre-restart 数据) |

### 按路径分组

| 路径 | 请求数 | 成功 | SR% | avg_ttfb | avg_dur | max_dur |
|------|--------|------|-----|----------|---------|---------|
| nv_integrate | 191 | 185 | 96.9% | 9,761ms | 13,540ms | 98,823ms |
| nvcf_pexec | 91 | 91 | 100.0% | 12,000ms | 12,010ms | 93,363ms |
| (NULL/ATE) | 14 | 3 | 21.4% | 170ms | 59,694ms | 151,405ms |

### 按模型分组

| 模型 | 请求数 | 成功 | SR% |
|------|--------|------|-----|
| glm5_2_nv | 171 | 165 | 96.5% |
| dsv4p_nv | 61 | 53 | 86.9% |
| kimi_nv | 38 | 37 | 97.4% |
| minimax_m3_nv | 26 | 24 | 92.3% |

### 错误分类

| 错误类型 | 数量 | avg_dur |
|----------|------|---------|
| all_tiers_exhausted | 11 | 66,346ms |
| NVStream_TimeoutError | 3 | 94,904ms |
| stream_total_deadline | 3 | 69,014ms |

### ATE 详情 (17 failures)

```
dsv4p_nv: 8 ATE, all ~61s all_tiers_exhausted, tiers_tried=1, fallback=f — FALLBACK_GRAPH transient
glm5_2_nv: 3 NVStream_TimeoutError (92-99s), 2 stream_total_deadline (62-95s), 1 ATE 151s
kimi_nv: 1 ATE 60s
minimax_m3_nv: 1 ATE 151s, 1 stream_total_deadline 50s
```

### 后重启窗口 (23:48 UTC → now)

**0 请求** — 夜间无流量，R1036 尚未验证。

## 6. DB: nv_tier_attempts 6h

```
tier          | error_type       | cnt | avg_ms | max_ms
minimax_m3_nv | IntegrateTimeout |   1 |  90762 |  90762
```

仅 1 条 tier 失败记录 (minimax_m3_nv IntegrateTimeout 90s)，与 TIER_TIMEOUT_BUDGET_S=110 一致。

## 7. 数据质量评估

| 维度 | 状态 | 说明 |
|------|------|------|
| 有效窗口 | 夜间低流量 | 6h 全为 pre-R1036 数据，后重启 0 请求 |
| dsv4p_nv ATE | 8 个 ~61s | FALLBACK_GRAPH transient disappearance（NVCF 基础设施问题，非 proxy 可修复） |
| pexec | 100% SR | 完美 |
| ms_gw | 健康 | MS-OK/MS-STREAM-DONE 正常 |
| R1036 验证 | 未开始 | ms_gw 救援需白天流量验证 |

## 8. 优化决策: NOP

**R1036 (NVU_MS_GW_FALLBACK_TIMEOUT 45→90) 刚部署，无后重启请求，无法验证效果。**

- dsv4p_nv 8 ATE 全部是 FALLBACK_GRAPH transient disappearance（tiers_tried=1, fallback=f），这是 NVCF 基础设施间歇性故障，非 proxy 参数可修复
- ms_gw 健康运行，MS-OK/MS-STREAM-DONE 流动正常
- 所有 ATE 发生在 pre-R1036 窗口，R1036 的 ms_gw 救援超时延长尚未被验证
- NVU_MS_GW_FALLBACK_TIMEOUT=90s 已覆盖 ms_gw ds seek 处理 (100-200s)，但需白天流量验证
- 无新错误模式，无新优化空间

**变更**: 零参数，零 compose 修改，零重启。

---

## ⏳ 轮到HM1优化HM2