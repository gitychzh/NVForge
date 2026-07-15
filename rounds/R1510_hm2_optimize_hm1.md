# R1510: HM2→HM1 — NOP (false trigger, zero post-restart traffic, R1507 untested)

**Timestamp**: 2026-07-16 06:00 UTC

## 触发判定
- 脚本输出: `"[2026-07-16 06:00:23] 这是我提交的, 不触发"` — HM2 自身 commit
- 最新 commit: `c29966b R1509: HM2→HM1 — NOP` — author=opc2_uname (HM2)
- 判定: **FALSE TRIGGER** — HM1 未提交新 commit, cron 检测到 HM2 自身 commit (R1508→R1509→R1510 triple-dispatch)

## 数据收集 (HM1)

### 容器状态
- 容器: nv_gw, 重启于 2026-07-15T21:46:15Z (~8.3h前)
- **零重启后流量** — 所有 6h 数据均为重启前
- compose md5: `f77f0381e8ceb6eb5ba522143f992a99` (R1507 变更后, 与 R1508/R1509 一致)

### 6h 总体 (75 req, 52 OK, 23 fail → 69.3% SR)

| 模型 | 请求 | OK | 失败 | SR% | Avg Dur |
|------|------|-----|------|-----|---------|
| dsv4p_nv | 49 | 40 | 9 | 81.6% | 16.6s |
| glm5_2_nv | 26 | 12 | 14 | 46.2% | 12.0s |

### 错误分类 (23 失败)

| 错误类型 | 数量 | 模型 | 路径 | Avg Dur | 根因 |
|---------|------|------|------|---------|------|
| zombie_empty_completion | 21 | glm5_2_nv(12) + dsv4p_nv(9) | integrate/pexec | 9.4s | NVCF content-filter, code-level, 不可配置 |
| all_tiers_exhausted | 2 | dsv4p_nv | pexec | 62.7s | 预重启, num_attempts=1, empty_200/504 |

### Tier Attempts (2)
- 2× glm5_2_nv 429_integrate_rate_limit (k1, k2) — 瞬时, 网关正确处理

### ms_gw: 15 total, 14 OK → 93.3% healthy

### Tier Attempts 详情 (2)
- glm5_2_nv k1: 429_integrate_rate_limit — transient
- glm5_2_nv k2: 429_integrate_rate_limit — transient

### 错误详情 (nv_error_detail.2026-07-16.jsonl)
- dsv4p_nv ATE 均为 num_attempts=1 (BUDGET=66 floor pattern, 1st key empty_200/504 → budget exhausted → immediate ATE)
- 1× glm5_2_nv IntegrateProxyConnectionError (22:03 UTC, SOCKS5 proxy DNS failure, all 5 keys + pexec fallback → 14 attempts → 8.4s → ATE) — 宿主机级 DNS failure, 非配置可修复

### 6h 按小时 SR

| Hour (UTC) | Total | OK | Fail | SR% |
|-----------|-------|-----|------|-----|
| 16:00 | 9 | 6 | 3 | 66.7% |
| 17:00 | 8 | 4 | 4 | 50.0% |
| 18:00 | 18 | 14 | 4 | 77.8% |
| 19:00 | 9 | 5 | 4 | 55.6% |
| 20:00 | 10 | 6 | 4 | 60.0% |
| 21:00 | 21 | 17 | 4 | 81.0% |

### 按路径

| upstream_type | cnt | ok | avg_ttfb | avg_dur | max_dur |
|---------------|-----|-----|----------|---------|---------|
| nvcf_pexec | 49 | 40 | 15343 | 16601 | 64263 |
| nv_integrate | 24 | 12 | 11970 | 11970 | 29382 |
| (ATE) | 2 | 0 | — | 62720 | 64263 |

### 环境配置 (与 R1507-R1509 一致)

| 参数 | 值 | 状态 |
|------|-----|------|
| `NVU_MS_GW_FALLBACK_MODELMAP` | `glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms` | R1507 变更 |
| `NVU_MS_GW_FALLBACK_TIMEOUT` | 120 | R1507 变更 |
| `NVU_PEER_FB_SKIP_MODELS` | (empty) | ✓ all models enabled |
| `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | ✓ Floor |
| `NVU_INTEGRATE_TIMEOUT_FASTBREAK` | 1 | ✓ Floor |
| `NVU_EMPTY_200_FASTBREAK` | 2 | ✓ Key-specific |
| `TIER_COOLDOWN_S` | 15 | ✓ |
| `UPSTREAM_TIMEOUT` | 66 | ✓ |
| `TIER_TIMEOUT_BUDGET_S` | 205 | ✓ |
| `NVU_TIER_BUDGET_DSV4P_NV` | 66 | ✓ Budget floor |
| `NVU_TIER_BUDGET_GLM5_2_NV` | 96 | ✓ |
| `NVU_TIER_BUDGET_MINIMAX_M3_NV` | 100 | ✓ |
| `NVU_STREAM_TOTAL_DEADLINE_S` | 42 | ✓ |
| `NVU_STREAM_FIRST_BYTE_DEADLINE_S` | 20 | ✓ |
| `KEY_COOLDOWN_S` | 25 | ✓ |
| `MIN_OUTBOUND_INTERVAL_S` | 0 | ✓ |
| `NVU_PEER_FALLBACK_TIMEOUT` | 66 | ✓ |

## 决策: NOP (零参数变更)

### 失败分析
1. **21 zombie_empty_completion** (11 glm5_2_nv integrate + 9 dsv4p_nv pexec, avg 9.4s): NVCF server-side content-filter returns `finish_reason=stop` with empty content (content_chars=12 < 50). Gateway correctly detects via `NV-ZOMBIE-EMPTY` and sends error chunk for fallback. **Not config-fixable** — NVCF-side content filtering.
2. **2 ATE** (dsv4p_nv pexec, 62.7s): 全部预重启数据。num_attempts=1 — BUDGET=66 floor pattern correctly triggers immediate ATE on first-key empty_200/504. R1507 ms_gw fallback for dsv4p_nv 未触发 (重启后零流量).
3. **1 IntegrateProxyConnectionError** (22:03 UTC): 宿主机级 SOCKS5 proxy DNS failure (`host.docker.internal` resolution failed for all 5 keys). 非容器配置可修复。

### R1507 变更验证状态
- R1507 变更 (`dsv4p_nv→dsv4p_ms` in MS_GW_FALLBACK_MODELMAP, FALLBACK_TIMEOUT 195→120) 已于 21:46 UTC 部署
- **零重启后流量** → 变更未经验证
- 需等待流量恢复后 HM1 验证

### 综合判断
- False trigger: HM2 自身 commit (R1509) 被 cron 检测为 HM1 提交
- 全部 23 失败为预重启数据 (zombie=NVCF content-filter, ATE=BUDGET floor pattern)
- 零重启后流量, R1507 变更未经验证
- 全部参数 floor/optimal
- 铁律: 只改HM1不改HM2

## 变更: 无
- 零参数变更, 零 compose 编辑, 零容器重启
- 铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
