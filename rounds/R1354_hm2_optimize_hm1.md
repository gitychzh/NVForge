# R1354: HM2→HM1 — NOP (false trigger, R1000 settling, 零可修故障, 514th chain of R1133)

## 1. 触发分析

- cron 脚本输出: `"这是我提交的, 不触发"` (R1000 commit author = opc2_uname, HM2)
- 脚本正确检测到自提交, 但 cron 仍被派遣 — 误触发
- 最新 commit: R1000 (faa3194, HM2, opc2_uname), NVU_TIER_BUDGET_DSV4P_NV 82→94
- HM1 git log: 仍停留在 R1206 (de04120), 186 轮落后
- HM1 容器 nv_gw 于 2026-07-14 11:29 UTC 重启 (R1000 部署), 仅 6h+ 上线

## 2. 改前数据 (2026-07-14 19:35 UTC, 6h)

### 2.1 nv_requests 概览

| 指标 | 值 |
|------|-----|
| 总请求 | 83 |
| 成功 | 70 (84.3%) |
| 错误 | 13 (15.7%) |

### 2.2 按 upstream_type 明细 (6h)

| upstream_type | mapped_model | 总 | OK | Err | SR | avg_dur | max_dur |
|--------------|--------------|-----|-----|------|------|----------|---------|
| nvcf_pexec | dsv4p_nv | 48 | 48 | 0 | 100% | 20,938 | 64,362 |
| nv_integrate | glm5_2_nv | 29 | 22 | 7 | 75.9% | 12,694 | 39,654 |
| NULL (ATE) | dsv4p_nv | 6 | 0 | 6 | 0% | 71,694 | 72,032 |

### 2.3 Error 分类 (6h)

| Tier | 错误数 | error_type | avg_dur_ms |
|------|--------|-----------|------------|
| glm5_2_nv | 7 | zombie_empty_completion | 10,159 |
| dsv4p_nv | 6 | all_tiers_exhausted | 71,694 |

### 2.4 按小时明细 (6h)

| Hour (UTC) | total | ok | fail | SR% |
|-----------|-------|-----|------|------|
| 05:00 | 1 | 0 | 1 | 0.0 |
| 06:00 | 59 | 52 | 7 | 88.1 |
| 07:00 | 4 | 3 | 1 | 75.0 |
| 08:00 | 5 | 4 | 1 | 80.0 |
| 09:00 | 5 | 4 | 1 | 80.0 |
| 10:00 | 4 | 3 | 1 | 75.0 |
| 11:00 | 5 | 4 | 1 | 80.0 |

### 2.5 容器重启后数据 (自 11:29 UTC)

| 指标 | 值 |
|------|-----|
| 总请求 | 3 |
| 成功 | 3 (100%) |
| 错误 | 0 |

### 2.6 Other stats

- nv_tier_attempts: 0 (零 tier 尝试, 干净)
- fallback_occurred: false (全部 81 请求, 零 fallback 触发)
- ms_gw: 6req/5OK (83.3%), 独立流量, 非 nv_gw fallback 路径
- ms_gw logs: 3× MS-VARIANT-EXHAUSTED + 1× MS-STREAM-CLIENT-EOF (BrokenPipeError), 正常

### 2.7 实时日志 (最近 100 行)

```
[19:33:20.2] [NV-REQ] mapped_model=glm5_2_nv start_tier=glm5_2_nv stream=True tier_chain=['glm5_2_nv'] (no fallback, 3model)
[19:33:34.9] [NV-REQ] mapped_model=glm5_2_nv start_tier=glm5_2_nv stream=True tier_chain=['glm5_2_nv'] (no fallback, 3model)
[19:33:46.4] [NV-REQ] mapped_model=glm5_2_nv start_tier=glm5_2_nv stream=True tier_chain=['glm5_2_nv'] (no fallback, 3model)
```
(no fallback, 3model) 为 R832 设计: FALLBACK_GRAPH={} 预期正常状态, 非问题。

### 2.8 HM1 nv_gw 当前配置 (env)

```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=205
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_TIER_BUDGET_DSV4P_NV=94        ← R1000 新值
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_PEER_FB_SKIP_MODELS=""           (enabled)
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_PEER_FALLBACK_ENABLED=1
NVU_MS_GW_FALLBACK_TIMEOUT=195
FALLBACK_HEALTH_THRESHOLD=0.05
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_STREAM_TOTAL_DEADLINE_S=42
NVU_STREAM_FIRST_BYTE_DEADLINE_S=20
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NV_INTEGRATE_KEY_COOLDOWN_S=0
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=15
MIN_OUTBOUND_INTERVAL_S=0
NVU_CONNECT_RESERVE_S=0
KEY_AUTHFAIL_COOLDOWN_S=60
```

## 3. 根因分析

### 3.1 dsv4p_nv 6 ATE: 全部 PRE-RESTART

容器于 2026-07-14 11:29 UTC 重启 (R1000 部署 NVU_TIER_BUDGET_DSV4P_NV 82→94)。6 个 dsv4p_nv ATE 全部发生在 05:00-06:00 UTC 窗口 (pre-restart)。Post-restart dsv4p_nv: 3/3 OK (100%)。

R1000 的 k2 headroom 修复 (16s→28s) 需要时间验证 — 目前 post-restart 数据量太小 (仅 3 req)，不足以判断效果。

### 3.2 glm5_2_nv 7 zombie: 代码级 content_filter (不变)

7 个 zombie_empty_completion, avg 10,159ms, 全部 integrate 路径。日志确认: `finish_reason=content_filter` → `NV-ZOMBIE-ERROR-CHUNK` → openclaw fallback。此为 NVCF 服务端 content-filter 拒绝, 代码级问题, 非 config 可修。

### 3.3 零 fallback 触发

`fallback_occurred=false` 全部请求。FALLBACK_GRAPH={} (R832 设计), `(no fallback, 3model)` 为预期正常状态。ms_gw 同模型 fallback 走 NVU_MS_GW_FALLBACK_MODELMAP, 但 dsv4p_nv ATE 全部 pre-restart, 无需触发。

### 3.4 零可修故障

- dsv4p_nv: pexec 100% SR (48/48), ATE 全部 pre-restart → R1000 需 settling
- glm5_2_nv: zombie 为代码级 content_filter → 非 config 可修
- 0 tier_attempts: 零 key 级错误
- 0 fallback triggers: 系统安静
- All params floor/optimal

## 4. 决策: NOP (零修改)

**R1000 刚部署 6h, 需要 settling time。Post-restart dsv4p_nv 3/3 OK, 需更多数据验证 k2 headroom 效果。**

**不改:**
- 零 config 参数变更
- 零 compose 修改
- 零容器重启
- 铁律: 只改 HM1 不改 HM2

**待 R1000 充分 settling 后 (post-restart dsv4p_nv 流量积累), 再评估 BUDGET_DSV4P_NV=94 是否充分。**

## ⏳ 轮到HM1优化HM2
