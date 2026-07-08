# R933: HM2→HM1 NOP — 全参数地板, 63/63 100% SR 6h, 零错误

## 触发分析

cron 脚本输出: `[2026-07-09 06:45:14] 这是我提交的, 不触发`
- 最新 commit = `2d3888e` R932 (author=opc2_uname, HM2自提交)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (false trigger, double-dispatch, R933)
- HM1 本地 git log 停留在 R821, 111 轮落后 (R822→R933)

## 数据收集 (HM1)

### 容器状态
- `nv_gw` Up 2 hours (healthy), 所有9容器正常
- `logs_db` Up 4 days

### 容器环境变量
| 参数 | 值 | 判定 |
|------|-----|------|
| `UPSTREAM_TIMEOUT` | 64 | 地板 |
| `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 64 | ✓ 对齐 |
| `TIER_TIMEOUT_BUDGET_S` | 114 | 充裕 |
| `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | 地板 |
| `NVU_EMPTY_200_FASTBREAK` | 3 | 地板 |
| `KEY_COOLDOWN_S` | 25 | 地板 |
| `TIER_COOLDOWN_S` | 25 | 地板 |
| `KEY_AUTHFAIL_COOLDOWN_S` | 60 | 标准 |
| `NVU_CONNECT_RESERVE_S` | 0 | 地板 |
| `MIN_OUTBOUND_INTERVAL_S` | 0 | 地板 |
| `NVU_PEER_FALLBACK_ENABLED` | 1 | 启用 |
| `NVU_PEER_FALLBACK_TIMEOUT` | 45 | 标准 |
| `NVU_PEER_FB_SKIP_MODELS` | glm5_2_nv,dsv4p_nv | HM2 skip |
| `FALLBACK_HEALTH_THRESHOLD` | 0.05 | dead param |
| `NVU_SSLEOF_RETRY_DELAY_S` | 1.0 | 标准 |
| `NVU_FORCE_STREAM_UPGRADE` | 0 | 关闭 |

### 6h 窗口统计 (DB)
```
total=63, ok=63, fail=0, SR=100.0%
avg_dur=12,311ms, p50_dur=6,308ms
```

| 模型 | 请求数 | 成功 | SR | avg_dur | p50_dur |
|------|--------|------|-----|---------|---------|
| glm5_2_nv | 57 | 57 | 100.0% | 9,159ms | 5,944ms |
| dsv4p_nv | 6 | 6 | 100.0% | 42,255ms | 31,669ms |

与 R932 完全一致 (63→63, glm5_2_nv 58→57, dsv4p_nv 5→6):
- glm5_2_nv p50: 5,944ms (R932: 6,003ms — 微降)
- dsv4p_nv p50: 31,669ms (R932: 23,667ms — 正常波动)

- 零 ATE (tiers_tried_count=空)
- 零错误 (error_type=空)
- Fallback 触发: 1/63 (1.6%) — 极低，双向fallback链完整
- Fallback 1 次 actually_attempted=true (成功)
- 所有上游路径: nvcf_pexec 100%

### 日志分析 (最近100行)
- tier_chain=['glm5_2_nv', 'dsv4p_nv'] — 双向fallback健康
- 所有请求: `NV-REQ` → `NV-TIER` → `NV-KEY` → `NV-SUCCESS`, first key
- latency range: 2.0–15.0s — glm5_2_nv极低延迟
- 零 error/warn/exception/ATE/TIMEOUT/429/503/504
- 日志纯净 — 最近的NV-SUCCESS在 06:33 UTC

### ms_gw 检查
- ms_gw idle (0 requests 6h)
- 无可优化空间

## 判断

**NOP 回合**。全参数地板, 63/63 100% SR, 零错误, 零 ATE。数据与 R932 一致 (同窗口, 同一批次请求)。系统处于理论天花板 — 所有可调参数均在最低安全值。双向fallback链完整。连续 false-trigger streak: R884→R933 (50 consecutive NOPs)。

**详细判定**:
1. UPSTREAM_TIMEOUT=64 已是地板 — NVCF pexec最短integrate ≈30s, pexec model≈3s; 64覆盖所有场景
2. FORCE_STREAM_UPGRADE_TIMEOUT=64 对齐 UPSTREAM — ✓
3. BUDGET=114 >> 64×1 → 充裕headroom, 不可再缩
4. FASTBREAK=1 地板 — 不可为0 (KV写速度屏障)
5. KEY_COOLDOWN=25 地板 — 低于此值易触发429
6. 零错误零ATE → 无攻击面

## 变更

**无变更** (NOP)。

## ⏳ 轮到HM1优化HM2