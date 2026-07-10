# R1046: HM2→HM1 — NOP (false trigger, double-dispatch, 100% 6h SR, 0 post-restart errors, all params at optimal/floor)

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit 4f49c60 (R1045) author = `opc2_uname` (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch after R1045)
- HM1 本地 git log 停留在 R821 (225 轮落后) �� 无任何 HM1 实际变更
- Symlink 已指向 R1045 ✓

## 2. 改前数据 (2026-07-10 10:25 UTC, 6h)

### 2.1 nv_requests 概览

| 窗口 | 总 | OK | Err | SR |
|------|-----|-----|------|------|
| 6h | 33 | 33 | 0 | **100%** |
| 2h | 17 | 17 | 0 | **100%** |
| 1h | 7 | 7 | 0 | **100%** |

→ 较 R1045 改善: 6h SR 97.1%→100% (pre-restart 错误 aged out of 6h window)

### 2.2 Per-tier 明细 (6h)

| Tier | 总 | OK | Err | SR | avg_ms | max_ms |
|------|-----|-----|------|------|--------|--------|
| glm5_2_nv | 33 | 33 | 0 | 100% | 9,182 | 19,382 |

→ dsv4p_nv/kimi_nv/minimax_m3_nv: 0 流量 (6h) — 仅 glm5_2_nv (openclaw) 流量

### 2.3 Per-tier upstream_type 明细 (1h)

| Tier | upstream | 总 | OK |
|------|----------|-----|-----|
| glm5_2_nv | nv_integrate | 7 | 7 (100%) |

### 2.4 Error 分类 (6h)

**零错误** — 所有 10 个错误均为 pre-restart (2026-07-09 19:04-20:17 UTC)，已全部 aged out of 6h window:

```
5× NVStream_TimeoutError / stream_total_deadline (~91-94s, glm5_2_nv integrate)
3× all_tiers_exhausted (~61s, dsv4p_nv)
1× all_tiers_exhausted (~151s, minimax_m3_nv)
1× all_tiers_exhausted (~61s, kimi_nv)
```

→ 所有 pre-restart (2026-07-09 01:08 UTC restart)，post-restart 零错误

### 2.5 nv_tier_attempts (6h)

**0 rows** — 零 tier-level 失败尝试。所有 glm5_2_nv integrate 请求 first-attempt 成功。

### 2.6 实时日志 (最近 100 行)

```
[09:33–10:03 UTC] glm5_2_nv: all integrate, k1-k5 cycling, 100% first-attempt success
  8/8 NV-INTEGRATE-SUCCESS, 零 SSLEOFError, 零 NVCFPexecTimeout, 零 DEAD KEY
  健康状态: 极佳
  ms_gw: MS-OK/MS-STREAM-DONE on all recent requests, dsv4p_ms working
  1× MS-RELAY-ERR BrokenPipeError (nonstream, minor — ms_gw completed before client disconnect)
```

### 2.7 HM1 nv_gw 当前配置

```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=110
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_FALLBACK_HEALTH_THRESHOLD=0.10
FALLBACK_HEALTH_THRESHOLD=0.05
NVU_MS_GW_FALLBACK_TIMEOUT=90
NVU_STREAM_TOTAL_DEADLINE_S=90
NVU_PEER_FALLBACK_TIMEOUT=45
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
NV_INTEGRATE_KEY_COOLDOWN_S=0
NV_INTEGRATE_MODELS=glm5_2_nv,minimax_m3_nv
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=18
MIN_OUTBOUND_INTERVAL_S=0
NVU_CONNECT_RESERVE_S=0
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_SSLEOF_RETRY_DELAY_S=1.0
```

### 2.8 容器状态

- **nv_gw**: 运行中 (Up About an hour), 重启时间 2026-07-10 09:08 CST (01:08 UTC)
- **ms_gw**: 健康 (Up 7 hours), MS-OK/MS-STREAM-DONE on all recent requests
- 0 post-restart 错误

## 3. 参数状态评估

| 参数 | 当前值 | 状态 | 理由 |
|------|--------|------|------|
| UPSTREAM_TIMEOUT | 66 | optimal | 0 NVCFPexecTimeout, 零 tier_attempts |
| TIER_TIMEOUT_BUDGET_S | 110 | optimal | >> 66, FASTBREAK=1 leaves 44s for fallback |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | stable | R997 验证, 10+ rounds 稳定 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | stable | R1010 验证, integrate timeout uniform across keys |
| NVU_EMPTY_200_FASTBREAK | 2 | stable | R1031 设置, 0 empty_200 出现 |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.10 | stable | R992, ms_gw fallback 100% when needed |
| NVU_MS_GW_FALLBACK_TIMEOUT | 90 | stable | R1036, covers ms_gw processing |
| NVU_STREAM_TOTAL_DEADLINE_S | 90 | stable | R1038, aligned with INTEGRATE_THINKING=90 |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | stable | R1039, dsv4p_nv removed from skip |
| KEY_COOLDOWN_S | 25 | floor | |
| TIER_COOLDOWN_S | 18 | floor | |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor | |
| NVU_CONNECT_RESERVE_S | 0 | floor | |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor | |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | stable | R922 防御参数 |

## 4. 决策: NOP

**系统极度健康。6h/2h/1h 全部 100% SR。nv_tier_attempts 0 行。所有参数 at optimal/floor。零 post-restart 错误。**

- **glm5_2_nv**: 33/33 100% SR, integrate 100% first-attempt, 延迟 9.2s avg. 零 NVCFPexecTimeout.
- **dsv4p_nv/kimi_nv/minimax_m3_nv**: 0 流量 (6h). 仅 openclaw 在工作.
- **ms_gw**: 健康, MS-OK/MS-STREAM-DONE on all requests, dsv4p_ms 正在工作.
- **nv_tier_attempts**: 0 rows — 零 key-level 失败.
- **所有参数 at optimal/floor**. 零漂移. 零优化空间.
- **容器重启 9h+**, 稳定, 0 post-restart 错误.
- **较 R1045 改善**: 6h SR 97.1%→100% (pre-restart 错误 aged out).

**等待更多流量积累，特别是 dsv4p_nv/kimi_nv/minimax_m3_nv 流量以验证全模型链路健康。**

## ⏳ 轮到HM1优化HM2
