# R934: HM2→HM1 NOP — 全参数地板, 63/63 100% SR 6h, 零错误, 零 ATE

## 触发分析

cron 脚本输出: `[2026-07-09 06:55:14] 这是我提交的, 不触发`
- 最新 commit = `5929adb` R933 (author=opc2_uname, HM2自提交)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (false trigger, 51st consecutive NOP: R884→R934)
- HM1 本地 git log 停留在 R821, 112 轮落后 (R822→R934)

## 数据收集 (HM1)

### 容器状态
- `nv_gw` Up since 2026-07-08T20:42:53Z (~10h), healthy
- `logs_db` Up 4 days
- 所有9容器正常

### 容器环境变量
| 参数 | 值 | 判定 |
|------|-----|------|
| `UPSTREAM_TIMEOUT` | 64 | 地板 — NVCFPexecTimeout max=52,849ms (pre-restart) << 64, 非绑定 |
| `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 64 | ✓ 对齐 UPSTREAM=64 |
| `TIER_TIMEOUT_BUDGET_S` | 114 | 充裕 — 64×1=64 << 114 |
| `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | 地板 |
| `NVU_EMPTY_200_FASTBREAK` | 3 | 地板 (R829止血) |
| `KEY_COOLDOWN_S` | 25 | 地板 |
| `TIER_COOLDOWN_S` | 25 | 地板 |
| `NVU_CONNECT_RESERVE_S` | 0 | 地板 |
| `MIN_OUTBOUND_INTERVAL_S` | 0 | 地板 |
| `NVU_PEER_FALLBACK_ENABLED` | 1 | 启用 |
| `NVU_PEER_FALLBACK_TIMEOUT` | 45 | 标准 |
| `NVU_SSLEOF_RETRY_DELAY_S` | 1.0 | 标准 |
| `NVU_FORCE_STREAM_UPGRADE` | 0 | 关闭 |
| `FALLBACK_HEALTH_THRESHOLD` | 0.05 | **dead param** (R919) — 实际阈值=NVU_FALLBACK_HEALTH_THRESHOLD=0.10 (func_health.py default) |
| `NV_INTEGRATE_MODELS` | "" | integrate 已禁用 |
| `NV_INTEGRATE_KEY_COOLDOWN_S` | 0 | 地板 |

### 6h 窗口统计 (DB)
```
total=63, ok=63, fail=0, SR=100.0%
avg_dur=12,311ms, 1 fallback_occurred, 1 req_with_429 (total 2 kc429)
```

| 模型 | 请求数 | 成功 | SR | avg_dur | max_dur |
|------|--------|------|-----|---------|---------|
| glm5_2_nv | 57 | 57 | 100.0% | 9,159ms | 44,815ms |
| dsv4p_nv | 6 | 6 | 100.0% | 42,255ms | 120,515ms |

与 R932/R933 一致 (63→63, glm5_2_nv 57→57, dsv4p_nv 6→6):
- glm5_2_nv avg: 9,159ms (R933: 9,159ms — 完全一致)
- dsv4p_nv avg: 42,255ms (R933: 42,255ms — 完全一致)
- 同一批次请求 (63 req, 无新请求到达)

- 零 ATE (tiers_tried_count=全部null)
- 零错误 (error_type=全部null)
- Fallback 触发: 1/63 (1.6%) — 双向fallback链完整, 1次 actually_attempted=true (成功)
- 所有上游路径: nvcf_pexec 100%
- key_cycle_429s: 2 total (1 request), 极低

### Post-restart 窗口 (2026-07-08T20:42:53Z+)
```
12/12 OK (100.0%), 零错误
```

### Pre-restart 窗口 (6h 内, 20:42:53Z 之前)
```
51/51 OK (100.0%), 零错误
```

### 日志分析 (最近100行)
- tier_chain=['glm5_2_nv', 'dsv4p_nv'] �� 双向fallback健康
- 所有请求: `NV-REQ` → `NV-TIER` → `NV-KEY` → `NV-SUCCESS`, first key
- latency range: 2.0–15.0s — glm5_2_nv极低延迟
- 零 error/warn/exception/ATE/TIMEOUT/429/503/504
- 日志纯净 — 最近的NV-SUCCESS在 06:33 UTC

### nv_tier_attempts (6h)
- dsv4p_nv: 1×NVCFPexecTimeout (52,849ms, k0, pre-restart), 1×empty_200 (pre-restart)
- 全部 pre-restart artifact — post-restart 零 tier attempt 失败

### HEALTH_THRESHOLD 验证
- `docker exec nv_gw python3 -c '...func_health.HEALTH_THRESHOLD'` → **0.1**
- compose `FALLBACK_HEALTH_THRESHOLD=0.05` → **dead param**, 无效果 (R919确认)
- 实际阈值 0.10 运行正常，双向fallback链完整

### ms_gw 检查
- ms_gw idle (0 requests 6h)
- 无可优化空间

## 候选参数评估

| 参数 | 当前值 | 候选 | 判定 |
|------|--------|------|------|
| UPSTREAM_TIMEOUT | 64 | — | NVCFPexecTimeout max=52,849ms << 64, 非绑定; 降低无意义 |
| FORCE_STREAM_UPGRADE_TIMEOUT | 64 | — | ✓ 已对齐 UPSTREAM=64 |
| TIER_TIMEOUT_BUDGET_S | 114 | — | 64×1=64 << 114 充裕, 不可再缩 (R768: FASTBREAK=1下BUDGET需>UPSTREAM×1) |
| FASTBREAK | 1 | — | 地板 |
| EMPTY_200_FASTBREAK | 3 | — | R829止血, 3 与 ms_gw 一致 |
| KEY_COOLDOWN | 25 | — | 地板 |
| PEER_FALLBACK_TIMEOUT | 45 | — | 匹配 UPSTREAM+reserve, 历史无成功案例 |
| FALLBACK_HEALTH_THRESHOLD | 0.05 (dead) | 0.10 | **dead param** — 改 compose 无效果; 实际阈值=0.10 已生效 |
| MIN_OUTBOUND | 0 | — | 地板 |
| CONNECT_RESERVE | 0 | — | 地板 |

## 判断

**NOP 回合**。全参数地板, 63/63 100% SR, 零错误, 零 ATE。数据与 R932/R933 完全一致 (同批次 63 请求, 无新请求到达)。系统处于理论天花板 — 所有可调参数均在最低安全值。双向fallback链完整。FALLBACK_HEALTH_THRESHOLD=0.05 是 dead param (R919), 实际运行的 NVU_FALLBACK_HEALTH_THRESHOLD=0.10 正确。连续 false-trigger streak: R884→R934 (51 consecutive NOPs)。

**详细判定**:
1. UPSTREAM_TIMEOUT=64 充裕 — NVCFPexecTimeout max=52,849ms << 64, 非绑定约束
2. FORCE_STREAM_UPGRADE_TIMEOUT=64 ✓ 对齐
3. BUDGET=114 >> 64×1 → 充裕headroom
4. FASTBREAK=1 地板
5. EMPTY_200_FASTBREAK=3 — R829止血, 与 ms_gw 一致
6. KEY_COOLDOWN=25 地板 — 低于此值易触发429
7. PEER_FALLBACK_TIMEOUT=45 标准 — 匹配 UPSTREAM+5s reserve
8. 零错误零ATE → 无攻击面

## ⏳ 轮到HM1优化HM2