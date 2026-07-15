# HM2 Optimize HM1 — Round R1447

## 触发分析

cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2)
- R1446 已提交并推送，symlink 已指向 R1446
- cron 仍被派遣 — 误触发 (double-dispatch, R1395 chain 第 52 次)
- 铁律确认: 只改HM1不改HM2

## 数据收集 (改前必有数据)

### 6h 窗口 (2026-07-15 13:05:07 UTC → 19:05:07 UTC)

| 指标 | 值 |
|------|-----|
| 总请求 | 52 |
| 200 OK | 32 |
| 失败 | 20 |
| SR | 61.5% |
| zombie | 11 (10 glm5_2_nv + 1 dsv4p_nv, NVCF content-filter) |
| ATE | 9 (8 dsv4p_nv 502 + 1 glm5_2_nv) |
| tier_attempts | 0 (clean key pool) |
| compose md5 | 51079b89019ddfb1a08f65e79e847b51 |
| 容器重启 | 2026-07-15T10:49:16Z (R1445 deploy) |

### 按模型

| 模型 | 请求 | OK | 失败 | SR | avg_dur |
|------|------|-----|------|-----|---------|
| glm5_2_nv | 42 | 31 | 11 | 73.8% | 18177ms |
| dsv4p_nv | 10 | 1 | 9 | 10.0% | 78386ms |

### dsv4p_nv ATE 详情 (8×502, 0 recovered)

| 时间 | duration | 备注 |
|------|----------|------|
| 06:05 | 112049ms | 预-R1445 BUDGET=124 |
| 07:05 | 124070ms | 预-R1445 BUDGET=124 |
| 07:35 | 124052ms | 预-R1445 BUDGET=124 |
| 09:06 | 63937ms | 预-R1445, 但 BUDGET=66 生效中 |
| 09:35 | 62793ms | BUDGET=66 |
| 10:07 | 64077ms | BUDGET=66 |
| 10:35 | 66074ms | BUDGET=66 |
| 11:05 | 63981ms | BUDGET=66, MS-FB relay_started=True → FAILED |

### ms_gw

| 指标 | 值 |
|------|-----|
| 总请求 | 36 |
| ok | 32 |
| error | 4 (无 error_type) |
| SR | 88.9% |

### NV-GW 日志关键信号

```
[NV-ALL-TIERS-FAIL] All 1 tiers failed (ring tiers tried: ['dsv4p_nv']), elapsed=63980ms, ABORT-NO-FALLBACK
[NV-MS-FB] local all_tiers_exhausted (model=dsv4p_nv), attempting same-model fallback to http://ms_gw:40007 as dsv4p_ms
[NV-MS-FB] ms_gw same-model fallback FAILED for model=dsv4p_nv, (relay_started=True)
```

ms_gw 日志同请求:
```
[MS-RR] req=ac77bc7d model=dsv4p_ms start_variant=5 start_key=3
[MS-OK-STREAM] req=ac77bc7d v5k3 backend=deepseek-ai/Deepseek-v4-Pro first=8192B
[MS-STREAM-DONE] req=ac77bc7d forwarded [DONE], closing client stream after 21262b
```

ms_gw 成功交付但 NV-GW relay 断裂 (BrokenPipeError) — 代码级缺陷，不可配置修复。

### 容器环境 (当前参数)

```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=205
NVU_TIER_BUDGET_DSV4P_NV=66       ← floor (UPSTREAM_TIMEOUT, R1440)
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
NVU_PEXEC_TIMEOUT_FASTBREAK=1     ← floor
NVU_EMPTY_200_FASTBREAK=2         ← no-op bug (R1039)
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1  ← floor
NVU_MS_GW_FALLBACK_TIMEOUT=280     ← max safe (R1445)
NVU_PEER_FB_SKIP_MODELS=           ← empty (peer-fb enabled)
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_STREAM_FIRST_BYTE_DEADLINE_S=20
NVU_STREAM_TOTAL_DEADLINE_S=42
NVU_CONNECT_RESERVE_S=0
NV_INTEGRATE_KEY_COOLDOWN_S=0
```

## 决策

**NOP — 所有参数已达 floor/optimal，无优化空间。**

- dsv4p_nv ATE 根本原因: NVCF 504 gateway timeout → key cycling → ATE → ms_gw relay BrokenPipeError
- ms_gw 成功交付请求但 NV-GW relay 断裂 — 代码级缺陷，不可配置修复
- BUDGET=66 (R1440) 已证实有效: ATE 从 ~124s 降至 ~64s
- MS_GW_FALLBACK_TIMEOUT=280 (R1445) 已达最大安全余量
- 11 zombie = NVCF content-filter — 不可配置修复
- 所有 FASTBREAK 参数已 floor
- 所有 COOLDOWN 参数已优化
- 0 tier_attempts — 干净 key pool

**铁律: 只改HM1不改HM2** ✅

## ⏳ 轮到HM1优化HM2

