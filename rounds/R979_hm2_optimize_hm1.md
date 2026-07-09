# HM2 Optimize HM1 — Round R979

> **Trigger**: False trigger (double-dispatch after R978). Cron script output: "这是我提交的, 不触发"
> **Author**: opc2_uname (HM2) · **Date**: 2026-07-09 08:30:19 UTC
> **Decision**: NOP — all params at floor/optimal, no config change needed
> **铁律**: 只改HM1不改HM2 ✓

---

## 1. 触发分析

- Cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = `opc2_uname` (HM2)
- HM1 git log 停留在 R821 (158 轮落后)
- Symlink 已指向 R978 → 此为 double-dispatch
- 改前必有数据 → 收集 6h 窗口数据

## 2. HM1 nv_gw 当前配置

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 64 | floor (R976 +2s) |
| TIER_TIMEOUT_BUDGET_S | 112 | safe (112>>64) |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor (adaptive) |
| NVU_EMPTY_200_FASTBREAK | 3 | floor |
| KEY_COOLDOWN_S | 25 | floor |
| TIER_COOLDOWN_S | 25 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | floor |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | defensive |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 | aligned (64≥64) |
| NVU_FORCE_STREAM_UPGRADE | 0 | off |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv,dsv4p_nv | R923 |
| NVU_PEER_FALLBACK_ENABLED | 1 | peer on |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | peer timeout |

**Routing**: All 5 keys DIRECT (no SOCKS5 proxy) — NVU_PROXY_URL1-5 all empty.

## 3. 6h 数据摘要

| 指标 | 值 |
|------|-----|
| 总请求 | 34 |
| 成功 | 31 |
| 错误 | 3 (all ATE) |
| 成功率 | 91.18% |
| Fallback | 21 (61.8%) |
| Fallback 成功率 | 100% |

## 4. 错误分析

3 ATE = all_tiers_exhausted, all glm5_2_nv:

| # | 模式 | 根因 |
|---|------|------|
| 1 | k1→504 + k2→NVCFPexecTimeout(49s) → fast-break → budget exhaust(112s) | NVCF platform 504 |
| 2 | k2→504 + k3→NVCFPexecTimeout(49s) → fast-break → budget exhaust(112s) | NVCF platform 504 |
| 3 | k3→504 + k4→NVCFPexecTimeout(49s) → fast-break → budget exhaust(112s) | NVCF platform 504 |

**Tier attempt breakdown (glm5_2_nv)**:
- NVCFPexecTimeout: uniform across K0-K4 (2-5 each, 55-62s) → NVCF function-level, not per-key
- 504_nv_gateway_timeout: K0-K3 (1-3 each) → NVCF platform degradation
- empty_200: K1, K4 (1-2 each) → minor, within FASTBREAK=3 threshold

**密钥**: NVCFPexecTimeout max=62,606ms < UPSTREAM=64,000ms — 超时发生在函数层而非网关层,无法通过 UPSTREAM_TIMEOUT 增加来捕获。FASTBREAK=1 正确工作: 第一个 NVCFPexecTimeout 后立即 fast-break 节省剩余 keys。BUDGET=112 足够 (112>>64), 但 504+timeout 组合消耗 ~109s 接近预算上界。

## 5. dsv4p_nv 延迟 (6h, 成功请求)

| Key | Count | Avg(ms) | P50(ms) | P95(ms) | Max(ms) |
|-----|-------|---------|---------|---------|---------|
| K1 | 6 | 91,823 | 98,537 | 126,733 | 127,397 |
| K2 | 6 | 93,601 | 98,546 | 137,492 | 139,129 |
| K3 | 4 | 85,562 | 78,971 | 160,798 | 173,278 |
| K4 | 4 | 83,645 | 81,702 | 120,076 | 126,524 |
| K5 | 5 | 73,120 | 79,212 | 111,784 | 116,973 |

**观察**: K5 最优 (P50 79s, P95 112s), K2 最差 (P95 137s)。所有 key P50 在 79-99s 范围 — 正常 NVCF 推理延迟。样本量小 (4-6/键), 差异不显著。

## 6. ms_gw 检查

ms_gw 6h 窗口: **0 请求** — 完全空闲。无优化空间。

## 7. 决策

**NOP** — 所有参数已在 floor/optimal:

- FASTBREAK=1: 正确工作, 每次 ATE 都节省 3 个 key 的无效尝试
- EMPTY_200=3: 3 个 ATE 中只出现 2 次 empty_200 (均在阈值内)
- BUDGET=112: 安全 (112>>64), 但 504+timeout 组合接近预算上界
- UPSTREAM=64: 已是最优, NVCFPexecTimeout max=62,606ms 在窗口内
- 3 ATE 均为 NVCF 平台级问题 (504 + function timeout), 非配置问题
- 21/21 fallback 100% SR — 弹性完全覆盖

**无参数调整空间。等待 HM1 提交新数据。**

---

## ⏳ 轮到HM1优化HM2
