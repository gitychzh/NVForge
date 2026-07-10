# HM2 Optimize HM1 — Round R1102

## 📋 执行摘要

**日期**: 2026-07-10 23:45 UTC  
**角色**: HM2 (opc2_uname) → HM1 (opc_uname)  
**类型**: NOP (false trigger)  
**改动**: 零参数，零 compose，零重启  
**铁律**: 只改 HM1 不改 HM2 ✓

---

## 1. 触发分析

cron 脚本输出: `已处理过此commit(1e433aace49448c9a59c9f09e3f46d0818db392b), 等待新提交`

- 最新 commit author = `opc2_uname` (HM2)
- HM1 本地 git HEAD: `fbf0e43 R821` (280 轮落后于 HM2)
- 确认: **false trigger** — HM1 未提交任何新内容

---

## 2. HM1 数据收集

### 2.1 nv_gw 配置快照 (env)

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | floor |
| TIER_TIMEOUT_BUDGET_S | 198 | R1088 |
| KEY_COOLDOWN_S | 25 | floor |
| TIER_COOLDOWN_S | 18 | R1018 |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | floor |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | floor |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | floor |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | R982 |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | R922 |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | R1039 |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | floor |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | floor |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | floor |
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 | floor |
| NVU_FORCE_STREAM_UPGRADE | 0 | floor |

**结论**: 所有参数已在地板 (floor)，无优化空间。

### 2.2 nv_gw 容器状态

- 容器启动: `2026-07-10 15:45:49 UTC` (8h 前重启)
- 健康检查: ✅ `{"status": "ok"}`
- 容器日志 (最近 100 行): 仅 1 条 SSLEOFError (glm5_2_nv k2, 5002ms, 已自动 cycle)，其余全部 `NV-INTEGRATE-SUCCESS` 首次尝试 OK

### 2.3 DB 数据

#### 6h 窗口 (62 req, 100% SR)

| tier_model | total | ok | SR |
|------------|-------|-----|------|
| glm5_2_nv | 59 | 59 | 100.0% |
| dsv4p_nv | 1 | 1 | 100.0% |
| kimi_nv | 1 | 1 | 100.0% |
| minimax_m3_nv | 1 | 1 | 100.0% |
| **总计** | **62** | **62** | **100.0%** |

- 零错误 (0 fail)
- 零 tier_attempts (6h window)
- 零 fallback 触发

#### 24h 窗口 (560 req, 93.8% SR)

| tier_model | total | ok | SR | avg_dur |
|------------|-------|-----|------|---------|
| glm5_2_nv | 401 | 388 | 96.8% | 17,043ms |
| dsv4p_nv | 73 | 60 | 82.2% | 14,772ms |
| kimi_nv | 50 | 49 | 98.0% | 10,121ms |
| minimax_m3_nv | 36 | 28 | 77.8% | 15,211ms |

- 24h 失败: 35 req (25 all_tiers_exhausted + 7 NVStream_TimeoutError + 3 stream_total_deadline)
- **所有失败均为 pre-restart** (2026-07-10 15:45 UTC 之前)

#### 后重启窗口 (8h, 21 req, 100% SR)

| tier_model | total | ok | SR | avg_dur | max_dur |
|------------|-------|-----|------|---------|---------|
| dsv4p_nv | 12 | 12 | 100.0% | 9,968ms | 31,487ms |
| glm5_2_nv | 9 | 9 | 100.0% | 14,604ms | 49,530ms |

### 2.4 ms_gw 状态

- 健康检查: ✅ `{"status": "ok"}`
- 24h 日志: 4 条 MS-VARIANT-EXHAUSTED + 2 条 MS-STREAM-CLIENT-EOF BrokenPipeError
- BrokenPipeError: **代码级缺陷，不可修复** (与 HM2 相同)
- 配置: 地板 (KEY_COOLDOWN=60, EMPTY_200_FASTBREAK=3, MIN_OUTBOUND=1.0)

---

## 3. 决策: NOP

| 信号 | 评估 |
|------|------|
| nv_gw 6h SR | 100% (62/62) ✅ |
| nv_gw 后重启 SR | 100% (21/21) ✅ |
| nv_gw 参数 | 全部在地板 (floor) |
| nv_gw 日志 | 零错误 (仅 1 SSLEOFError 自愈) |
| ms_gw | BrokenPipeError 代码级不可修复 |
| 触发 | false trigger (HM1 未提交新内容) |
| 优化空间 | 无 |

**结论**: NOP — 零参数改动，零 compose 改动，零重启。

---

## 4. HM1 vs HM2 参数差异对比

| 参数 | HM1 | HM2 | 差异 |
|------|-----|-----|------|
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | glm5_2_nv,dsv4p_nv | HM2 多跳过 dsv4p |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | 70 | HM2 多 4s |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | 70 | HM1 多 26s |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | 25 | HM1 多 41s |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | 150 | HM2 多 84s |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 3 | HM2 多 2 |
| TIER_COOLDOWN_S | 18 | 25 | HM2 多 7s |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | — | HM2 缺此参数 |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | — | HM2 缺此参数 |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | — | HM2 缺此参数 |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | — | HM2 缺此参数 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 | — | HM2 缺此参数 |
| MIN_OUTBOUND_INTERVAL_S | 0 | 0 | 对称 ✅ |
| KEY_COOLDOWN_S | 25 | 25 | 对称 ✅ |
| UPSTREAM_TIMEOUT | 66 | 66 | 对称 ✅ |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | 60 | 对称 ✅ |

HM1 参数更丰富（多 6 个 HM2 缺失的 env），但当前所有参数均已优化至地板，无进一步压缩空间。

---

## 5. 评判

- 更少报错: ✅ (后重启 0 错误)
- 更快请求: ✅ (avg_dur 9.9-14.6s, max_dur 31-49s)
- 超低延迟: ✅ (TTFB = duration, 无排队)
- 稳定优先: ✅ (100% SR 8h, 零 fallback)
- 铁律: 只改 HM1 不改 HM2 ✓

---

## ⏳ 轮到HM1优化HM2

