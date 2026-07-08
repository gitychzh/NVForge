# R886: HM2→HM1 — NOP (false trigger, double-dispatch, 38/38 100% 6h SR, zero ATE, 1 rescued fallback, identical to R885)

> **回合**: R886
> **方向**: HM2 → HM1
> **时间**: 2026-07-08 20:13 UTC
> **触发**: cron 误触发 (double-dispatch)
> **决策**: NOP (零变更)

---

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = `opc2_uname` (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被���遣 — **误触发 (double-dispatch)**
- HM1 本地 git log 停留在 R821（64 轮落后，正常）
- 与 R885 完全相同的触发场景

## 2. HM1 容器状态

| 指标 | 值 |
|------|-----|
| 容器名 | `nv_gw` |
| 状态 | healthy |
| StartedAt | 2026-07-08 04:12:50 UTC |
| tier_chain | `['glm5_2_nv', 'dsv4p_nv']` (dynamic fallback) |
| 日志 error/warn | 无 (zero) |
| 日志 NV-CYCLE 504 | 4 (glm5_2_nv k2/k4/k5 均匀分布) |
| 日志 NVCFPexecTimeout | 1 → FASTBREAK → fallback → SUCCESS |

## 3. HM1 环境变量 (docker exec nv_gw env)

| 参数 | 值 | 说明 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | R754 |
| TIER_TIMEOUT_BUDGET_S | 114 | R737 |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | R697 floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | R768 floor |
| NVU_EMPTY_200_FASTBREAK | 1 | R774 floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | R638 floor |
| KEY_COOLDOWN_S | 25 | 长期稳定 |
| TIER_COOLDOWN_S | 25 | 长期稳定 |
| NVU_CONNECT_RESERVE_S | 0 | R657 floor |
| NVU_FORCE_STREAM_UPGRADE | 0 | R692 禁用 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | R755 对齐 UPSTREAM=66 |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | R708 安全地板 |
| NVU_PEER_FALLBACK_ENABLED | 1 | |
| NVU_PEER_FALLBACK_URL | http://100.109.57.26:40006 | |

## 4. DB 数据 (6h window, 2026-07-08 06:14–12:14 UTC)

### 4.1 全局聚合

| 指标 | 值 |
|------|-----|
| total | 38 |
| ok | 38 (**100.0% SR**) |
| fail | 0 |
| errors | 0 |
| avg latency (ok) | 21,711ms |
| p50 latency | 7,575ms |
| p95 latency | 68,339ms |
| max latency | 144,743ms |
| fallback occurred | 1 (rescue) |
| integrate | 8 (avg TTFB=71,235ms) |
| pexec | 30 (avg TTFB=8,503ms) |

### 4.2 按模型

| tier_model | cnt | ok | fail | avg_ms | max_ms | min_ms | integrate | pexec |
|------------|-----|----|------|--------|--------|--------|-----------|-------|
| glm5_2_nv | 37 | 37 | 0 | 18,386 | 72,409 | 1,933 | 8 | 29 |
| dsv4p_nv | 1 | 1 | 0 | 144,743 | 144,743 | 144,743 | 0 | 1 |

### 4.3 按时段

| hour (UTC) | total | ok | avg_ms |
|------------|-------|----|--------|
| 06:00 | 3 | 3 | 31,486 |
| 07:00 | 6 | 6 | 28,024 |
| 08:00 | 6 | 6 | 26,664 |
| 09:00 | 6 | 6 | 4,679 |
| 10:00 | 6 | 6 | 45,455 |
| 11:00 | 8 | 8 | 8,869 |
| 12:00 | 3 | 3 | 10,223 |

### 4.4 最近 10 条请求

| created_at | tier_model | status | duration_ms | upstream_type | nv_key_idx |
|------------|------------|--------|-------------|---------------|------------|
| 12:03:54 | glm5_2_nv | 200 | 3,827 | nvcf_pexec | 0 |
| 12:03:50 | glm5_2_nv | 200 | 4,528 | nvcf_pexec | 4 |
| 12:03:44 | glm5_2_nv | 200 | 22,315 | nvcf_pexec | 3 |
| 11:34:21 | glm5_2_nv | 200 | 3,058 | nvcf_pexec | 2 |
| 11:34:18 | glm5_2_nv | 200 | 21,878 | nvcf_pexec | 1 |
| 11:33:56 | glm5_2_nv | 200 | 2,975 | nvcf_pexec | 0 |
| 11:33:52 | glm5_2_nv | 200 | 6,766 | nvcf_pexec | 4 |
| 11:33:44 | glm5_2_nv | 200 | 22,806 | nvcf_pexec | 3 |
| 11:03:36 | glm5_2_nv | 200 | 2,787 | nvcf_pexec | 2 |
| 11:03:33 | glm5_2_nv | 200 | 6,851 | nvcf_pexec | 1 |

全部 200 OK，零错误。

### 4.5 按 key 分布 (glm5_2_nv)

| nv_key_idx | cnt | ok | avg_ms | p50_ms |
|------------|-----|----|--------|--------|
| 0 | 10 | 10 | 24,513 | 11,317 |
| 1 | 5 | 5 | 10,128 | 6,851 |
| 2 | 8 | 8 | 17,466 | 5,482 |
| 3 | 7 | 7 | 19,335 | 20,924 |
| 4 | 7 | 7 | 15,633 | 7,106 |

## 5. 24h Error 全景

- 48 ATE total (all_tiers_exhausted), **全部来自 04:12 UTC 容器重启前**
- 容器重启后 (04:12+ UTC): 0 ATE, 100% SR
- 24h 窗口被重启前 ATE 污染 — 与 R884/R885 完全一致

## 6. 决策分析

### 6.1 当前状态评估

- **6h 窗口**: 38/38 OK (100.0% SR), 0 ATE, 0 errors — 系统完美运行
- **Fallback 健康**: 1 rescued fallback (glm5_2→dsv4p_nv), 100% rescue success rate
- **FALLBACK_GRAPH 正常**: tier_chain 包含双 tier，未出现 transient disappearance
- **所有参数已在 floor 或最优值**: UPSTREAM=66, BUDGET=114, FASTBREAK=1, EMPTY_200_FASTBREAK=1, PEER_FALLBACK=45, MIN_OUTBOUND=0, CONNECT_RESERVE=0
- **docker logs**: 零 error/warn，4× NV-CYCLE 504 (NVCF gateway 瞬时波动，key 轮转成功处理)
- **Integrate 延迟**: 8 请求 avg TTFB=71s，全成功，非配置问题（NVCF integrate 慢响应）
- **Pexec 延迟**: 30 请求 avg TTFB=8.5s，p95=22s — 健康

### 6.2 决策: NOP (零变更)

- 与 R885 数据完全一致（38/38 100% SR, 0 ATE, 1 rescued fallback）
- 所有参数已达最优值或 floor，无进一步优化空间
- 24h ATE 根因为 NVCF function DEGRADED（重启前），重启后 8h 零 ATE
- 系统自愈能力强：6h 窗口零错误证明 NVCF 已恢复
- 本次为 cron 误触发 (double-dispatch of R885)，无实际变更需求

## 7. 变更

**无变更 (NOP)**。零 compose 修改，零容器重启。

## 8. 验证

- 6h 窗口 100% SR → 系统健康，无需变更
- 与 R885 数据完全一致 → 确认 double-dispatch
- 容器重启后 8h 零 ATE → R819 代码修复 (400 cycle removal) 持续生效
- 无需要验证的变更

---

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2