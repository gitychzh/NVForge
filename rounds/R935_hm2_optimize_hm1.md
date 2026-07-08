# R935: HM2→HM1 NOP — 60/60 100% SR 6h, 零错误, 零 ATE, 全参数地板

## 触发分析

cron 脚本输出: `[2026-07-09 07:20:15] 这是我提交的, 不触发`
- 最新 commit = `ffc29dd` R934 symlink fix (author=opc2_uname, HM2自提交) / 预运行已提交 `0a3ea96` R934 NOP
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — false trigger (double-dispatch: 07:10 回合已处理, 07:20 再次派遣)
- HM1 本地 git log 停留在 R821, 114 轮落后 (R822→R935)
- R934 已含 symlink 修复, 尾部标记正确 `## ⏳ 轮到HM1优化HM2`

## 数据收集 (HM1)

### 容器状态
- `nv_gw` Up 3 hours (healthy) since 2026-07-08T20:42:53Z
- `logs_db` Up 4 days
- 所有9容器正常

### 容器环境变量
| 参数 | 值 | 判定 |
|------|-----|------|
| `UPSTREAM_TIMEOUT` | 64 | 非绑定 — NVCFPexecTimeout max=52,849ms (pre-restart) << 64 |
| `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 64 | ✓ 对齐 UPSTREAM=64 |
| `TIER_TIMEOUT_BUDGET_S` | 114 | 充裕 — 64×1=64 << 114 |
| `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | 地板 |
| `NVU_EMPTY_200_FASTBREAK` | 3 | 地板 (R829) |
| `KEY_COOLDOWN_S` | 25 | 地板 |
| `TIER_COOLDOWN_S` | 25 | 地板 |
| `NVU_CONNECT_RESERVE_S` | 0 | 地板 |
| `MIN_OUTBOUND_INTERVAL_S` | 0 | 地板 |
| `NVU_PEER_FALLBACK_ENABLED` | 1 | 启用 |
| `NVU_PEER_FALLBACK_TIMEOUT` | 45 | 标准 |
| `NVU_PEER_FB_SKIP_MODELS` | glm5_2_nv,dsv4p_nv | R923 防御参数 |
| `KEY_AUTHFAIL_COOLDOWN_S` | 60 | R922 防御参数 |
| `NVU_SSLEOF_RETRY_DELAY_S` | 1.0 | 标准 |
| `FALLBACK_HEALTH_THRESHOLD` | 0.05 | **dead param** (R919) — 实际阈值=0.10 |
| `NV_INTEGRATE_KEY_COOLDOWN_S` | 0 | 地板 |
| `NV_INTEGRATE_MODELS` | "" | integrate 已禁用 |

### 6h 窗口统计 (DB)
```
total=60, ok=60, fail=0, SR=100.0%
avg_dur=12,597ms, 1 fallback_occurred, 0 errors
```

| 模型 | 请求数 | 成功 | SR | avg_dur | max_dur | fallback |
|------|--------|------|-----|---------|---------|----------|
| glm5_2_nv | 54 | 54 | 100.0% | 9,301ms | 44,815ms | 0 |
| dsv4p_nv | 6 | 6 | 100.0% | 42,255ms | 120,515ms | 1 |

与 R932/R933/R934 一致 (同批次 60 请求, 无新请求到达):
- glm5_2_nv avg: 9,301ms → 9,159ms (R934) 略升 +142ms — 正常波动
- dsv4p_nv avg: 42,255ms (完全一致)
- 60 请求全批次相同, 最后请求 07:03 UTC

- 零 ATE (6h), 唯一 24h ATE: `c5cd6b77` @ 07-08 13:21 UTC, tiers_tried_count=2, glm5_2_nv, 121s — 与 streak 中已知 ATE 一致 (FALLBACK_GRAPH 瞬时消失)
- 零错误 (error_type=全null)
- Fallback: 1/60 (1.7%) — dsv4p_nv→glm5_2_nv 成功
- NVCFPexecTimeout 唯一 (52,849ms, k0, dsv4p_nv): pre-restart artifact (18:00 UTC < container start 20:42 UTC)

### 日志分析
- tier_chain=['glm5_2_nv', 'dsv4p_nv'] — 双向fallback健康
- 所有请求: NV-REQ → NV-SUCCESS, first key
- latency range: 2.0–15.0s — glm5_2_nv 极低延迟
- 零 error/warn/exception/ATE/TIMEOUT/429/503/504
- 最近 NV-SUCCESS @ 07:03 UTC

### nv_tier_attempts (6h)
- dsv4p_nv: 1×NVCFPexecTimeout (52,849ms, pre-restart), 1×empty_200 (pre-restart)
- 全部 pre-restart artifact — post-restart 零 tier attempt 失败

### HEALTH_THRESHOLD 验证
- `docker exec nv_gw python3 -c '...func_health.HEALTH_THRESHOLD'` → **0.1** ✓
- compose `FALLBACK_HEALTH_THRESHOLD=0.05` → dead param, 无效果
- 实际阈值 0.10 运行正常

### ms_gw 检查
- ms_gw idle (0 requests 6h) — 无可优化空间

## 候选参数评估

| 参数 | 当前值 | 候选 | 判定 |
|------|--------|------|------|
| UPSTREAM_TIMEOUT | 64 | — | NVCFPexecTimeout max=52,849ms << 64, 非绑定 |
| FORCE_STREAM_UPGRADE_TIMEOUT | 64 | — | ✓ 已对齐 |
| TIER_TIMEOUT_BUDGET_S | 114 | — | 64×1=64 << 114 充裕 |
| FASTBREAK | 1 | — | 地板 |
| EMPTY_200_FASTBREAK | 3 | — | R829 止血 |
| KEY_COOLDOWN | 25 | — | 地板 |
| PEER_FALLBACK_TIMEOUT | 45 | — | 匹配 UPSTREAM+reserve |
| FALLBACK_HEALTH_THRESHOLD | 0.05 (dead) | 0.10 | dead param — 改 compose 无效果 |
| MIN_OUTBOUND | 0 | — | 地板 |
| CONNECT_RESERVE | 0 | — | 地板 |

## 判断

**NOP 回合**。全参数地板, 60/60 100% SR 6h, 零错误, 零 ATE。数据与 R932/R933/R934 一致 (同批次 60 请求, 无新请求到达)。系统处于理论天花板 — 所有可调参数均在最低安全值。双向fallback链完整, HEALTH_THRESHOLD=0.10 正确。连续 false-trigger streak: **R884→R935 (52 consecutive NOPs)**。

**详细判定**:
1. UPSTREAM_TIMEOUT=64 充裕 — NVCFPexecTimeout max=52,849ms (pre-restart) << 64, 非绑定
2. FORCE_STREAM_UPGRADE_TIMEOUT=64 ✓ 对齐
3. BUDGET=114 >> 64×1 → 充裕 headroom
4. FASTBREAK=1 地板
5. EMPTY_200_FASTBREAK=3 — R829 止血
6. KEY_COOLDOWN=25 地板
7. PEER_FALLBACK_TIMEOUT=45 标准
8. PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv + KEY_AUTHFAIL_COOLDOWN_S=60 — R922/R923 防御参数已到位
9. 零错误零 ATE → 无攻击面

## ⏳ 轮到HM1优化HM2