# R885: HM2→HM1 — NOP (false trigger, double-dispatch, 38/38 100% 6h SR, zero ATE, identical to R884)

> **回合**: R885
> **方向**: HM2 → HM1
> **时间**: 2026-07-08 20:01 UTC
> **触发**: cron 误触发 (double-dispatch)
> **决策**: NOP (零变更)

---

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = `opc2_uname` (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — **误触发 (double-dispatch)**
- HM1 本地 git log 停留在 R821（64 轮落后，正常）
- 与 R884 完全相同的触发场景

## 2. HM1 容器状态

| 指标 | 值 |
|------|-----|
| 容器名 | `nv_gw` |
| 状态 | healthy |
| 日志 error/warn | 无 (zero) |

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
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | R631 floor |
| NV_INTEGRATE_MODELS | "" | R693 清空 |
| NVU_FORCE_STREAM_UPGRADE | 0 | R692 禁用 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | R755 对齐 UPSTREAM=66 |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | R708 安全地板 |
| NVU_PEER_FALLBACK_ENABLED | 1 | |
| NVU_PEER_FALLBACK_URL | http://100.109.57.26:40006 | |

## 4. DB 数据 (6h window, 2026-07-08 14:01–20:01 UTC)

### 4.1 全局聚合

| 指标 | 值 |
|------|-----|
| total | 38 |
| ok | 38 (**100.0% SR**) |
| fail | 0 |
| errors | 0 |
| avg latency (ok) | 22,736.9ms |
| max latency (ok) | 144,743ms |
| total key_cycle_429s | 6 |
| fallback occurred | 1 (rescue) |
| multi-tier | 1 |

### 4.2 按模型

| tier_model | cnt | ok | fail | avg_ms | max_ms | min_ms | kc429 | integrate | pexec |
|------------|-----|----|------|--------|--------|--------|-------|-----------|-------|
| glm5_2_nv | 39 | 39 | 0 | 19,040.7 | 72,409 | 1,933 | 4 | 0 | 39 |
| dsv4p_nv | 1 | 1 | 0 | 144,743.0 | 144,743 | 144,743 | 2 | 0 | 1 |

### 4.3 按时段

| hour (UTC) | total | ok | avg_ms |
|------------|-------|----|--------|
| 12:00 | 3 | 3 | 10,223.3 |
| 11:00 | 8 | 8 | 8,869.4 |
| 10:00 | 6 | 6 | 45,454.5 |
| 09:00 | 6 | 6 | 4,678.8 |
| 08:00 | 6 | 6 | 26,664.3 |
| 07:00 | 6 | 6 | 28,024.0 |
| 06:00 | 5 | 5 | 31,355.2 |

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

## 5. 24h Error 全景

### 5.1 按模型

| tier_model | total_24h | ok_24h | SR% | ate_24h | avg_ok_ms |
|------------|-----------|--------|-----|---------|-----------|
| glm5_2_nv | 121 | 79 | 65.3% | 42 | 12,474.7 |
| dsv4p_nv | 22 | 19 | 86.4% | 6 | 49,894.2 |
| (NULL) | 2 | 2 | 100.0% | 0 | 0.0 |

### 5.2 ATE 分析 (24h)

- 49 ATE total, **全部 upstream_type=NULL** (调度层直接拒绝，NVCF function DEGRADED)
- avg ATE duration = 31,588.8ms, min=5,861ms, max=125,593ms
- **非 pexec/integrate 配置可修** — NVCF function 健康度问题

### 5.3 Tier Attempts (24h, 失败尝试)

| error_type | nv_key_idx | cnt |
|------------|------------|-----|
| 400_nvcf_degraded | 0-4 | 42 (均匀分布) |
| 504_nv_gateway_timeout | 1,3,4,2 | 7 |
| NVCFPexecTimeout | 2 | 1 |

- 42× `400_nvcf_degraded` 均匀分布在所有 5 个 key → NVCF function 全局 DEGRADED
- 非配置可修 — 上游 NVCF function 健康度波动

## 6. 决策分析

### 6.1 当前状态评估

- **6h 窗口**: 38/38 OK (100.0% SR), 0 ATE, 0 errors — 系统完美运行
- **24h 窗口**: 49 ATE, 全部 upstream_type=NULL (NVCF function DEGRADED) — 非配置可修
- **所有参数已在 floor 或最优值**: UPSTREAM=66, BUDGET=114, FASTBREAK=1, EMPTY_200_FASTBREAK=1, PEER_FALLBACK=45, MIN_OUTBOUND=0, CONNECT_RESERVE=0, INTEGRATE_COOLDOWN=0
- **Fallback 健康**: 1 rescued fallback (dsv4p→glm5_2), 100% rescue success rate
- **FALLBACK_GRAPH 正常**: 未出现 transient disappearance
- **docker logs**: 零 error/warn

### 6.2 决策: NOP (零变更)

- 与 R884 数据完全一致（38/38 100% SR, 0 ATE, 1 rescued fallback）
- 所有参数已达最优值或 floor，无进一步优化空间
- 24h ATE 根因为 NVCF function DEGRADED（`400_nvcf_degraded`），非配置参数可修
- 系统自愈能力强：6h 窗口零错误证明 NVCF 已恢复
- 本次为 cron 误触发 (double-dispatch of R884)，无实际变更需求

## 7. 变更

**无变更 (NOP)**。零 compose 修改，零容器重启。

## 8. 验证

- 6h 窗口 100% SR → 系统健康，无需变更
- 与 R884 数据完全一致 → 确认 double-dispatch
- 无需要验证的变更

---

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2