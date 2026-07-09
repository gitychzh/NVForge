# HM2 Optimize HM1 — Round R994

## 1. 触发分析

HM1 push commit 9c18c18 (R993 round file): `"R993: HM2→HM1 — NOP (false trigger, double-dispatch after R992). 6h: 59/51 86.4% SR, 8 ATE (all pre-restart glm5_2_nv upstream_type=NULL). Post-restart 2/2 100% SR, 0 ATE. dsv4p_nv 11/11 100%. ms_gw normal. All params at floor/optimal."`

Cron 正确检测到 HM1 提交 → 触发 R994。

## 2. 数据收集 (改前必有数据 — 6h 窗口, DB time ~20:15 CST)

### 2.1 nv_requests 请求概览
| 指标 | 值 |
|------|-----|
| Total | 56 |
| Success | 48 (85.7%) |
| Error | 8 (14.3%) |

Post-restart (12:00 UTC / 20:00 CST): 2 req, 2 success, 100% SR, 0 error.

### 2.2 Per-tier 明细
| tier_model | cnt | ok | err | avg_ms | p95_ms |
|------------|-----|----|-----|--------|--------|
| glm5_2_nv | 47 | 39 | 8 | 10,032 | 41,592 |
| dsv4p_nv | 9 | 9 | 0 | 92,272 | 139,129 |

### 2.3 Error 分类
| error_type | cnt | upstream_type | fallback | period |
|------------|-----|---------------|-----------|--------|
| all_tiers_exhausted | 8 | NULL | false | 15:36–19:05 CST, pre-restart |

全部 8 error 均为 `upstream_type=NULL` dispatch 层拒诊 — 从未发起到上游，zero tier_attempts。与 R992/R993 数据完全一致。Post-restart 0 error。

### 2.4 nv_tier_attempts (ATE, 1h)
0 rows — post-restart 零 ATE。R992 NVU_FALLBACK_HEALTH_THRESHOLD 0.05→0.10 settling。

### 2.5 docker logs
```
[NV-PROXY] Starting NV-unified proxy on 0.0.0.0:40006
[NV-PROXY] Listening on 0.0.0.0:40006 (role=passthrough, default_tier=dsv4p_nv, fallback_chain=['kimi_nv', 'dsv4p_nv', 'glm5_2_nv'])
```
零 error/warn/fail。容器 healthy (Up 14 minutes)。

### 2.6 ms_gw
正常 — MS-OK-STREAM/MS-STREAM-DONE, 零 MS-EXHAUSTED。17:10–19:04 时段全部成功。

### 2.7 HM1 nv_gw 当前配置 (全部 at floor/optimal)
```
NVU_FALLBACK_HEALTH_THRESHOLD=0.10  ← R992 settling
UPSTREAM_TIMEOUT=66                  ← floor
TIER_TIMEOUT_BUDGET_S=112            ← >> 66 充足
NVU_PEXEC_TIMEOUT_FASTBREAK=2        ← floor
NVU_EMPTY_200_FASTBREAK=3            ← floor
KEY_COOLDOWN_S=25                    ← floor
TIER_COOLDOWN_S=25                   ← floor
MIN_OUTBOUND_INTERVAL_S=0            ← floor
NVU_CONNECT_RESERVE_S=0              ← floor
NV_INTEGRATE_KEY_COOLDOWN_S=0        ← floor
KEY_AUTHFAIL_COOLDOWN_S=60           ← R922 防御
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv  ← R923
NVU_FORCE_STREAM_UPGRADE=0           ← off
NVU_SSLEOF_RETRY_DELAY_S=1.0         ← floor
NVU_MS_GW_FALLBACK_TIMEOUT=45        ← standard
NVU_PEER_FALLBACK_TIMEOUT=45         ← standard
```

## 3. 优化决策

**NOP** — R992 变更 (NVU_FALLBACK_HEALTH_THRESHOLD 0.05→0.10) 正在 settling。Post-restart 数据: 2/2 100% SR, 0 error, 0 ATE。所有参数 at floor/optimal:

- UPSTREAM_TIMEOUT=66, buffer 3.4s ≥ 3s ✓ (R988)
- TIER_TIMEOUT_BUDGET_S=112 >> 66 充足
- 全部 floor 参数已达最优值 (cooldown=0/25, fastbreak=2/3)
- dsv4p_nv 9/9 100% SR (avg 92,272ms 为 deepseek 流式正常耗时)
- ms_gw 正常

8 个 pre-restart ATE 均为 glm5_2_nv upstream_type=NULL → all_tiers_exhausted，dispatch 层拒诊。R992 通过提升 NVU_FALLBACK_HEALTH_THRESHOLD 拓宽 ms_gw fallback 救援窗口应对此问题。Post-restart 数据不足 (2 req) 无法验证 R992 效果，但零错误已是正向信号。

无参数可调 — 所有 floor/optimal 值已达。唯一可优化项 (UPSTREAM_TIMEOUT 从 66 降至更低) 会压缩 buffer 低于 3s 安全阈值，违反 R751 规则。

**决策**: NOP, 所有参数维持不变。等待更多流量验证 R992 效果。

## ⏳ 轮到HM1优化HM2