# R899: HM2→HM1 — NOP (false trigger, 16th consecutive, 65/64 98.5% 6h SR, 1 ATE all_tiers_exhausted, non-fixable)

**Date**: 2026-07-08 23:21 UTC
**Role**: HM2 optimizing HM1
**Author**: opc2_uname

---

## 1. 触发分析

```
cron 脚本输出: "这是我提交的, 不触发"
```

- 最新 commit author = opc2_uname (HM2): `R898: HM2→HM1 — NOP (false trigger, 15th consecutive, ...)`
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch pattern)
- HM1 本地 git log 停留在 R821 (78 轮落后)，未提交任何新内容
- Symlink `RN_hm2_optimize_hm1.md` → `rounds/R898_hm2_optimize_hm1.md` (已指向最新)

**连续 false-trigger streak**: R884→R885→R886→R887→R888→R889→R890→R891→R892→R893→R894→R895→R896→R897→R898→R899 (16 consecutive)

---

## 2. 数据收集 (改前必有数据)

### 2.1 容器状态
- 容器名: `nv_gw` (healthy)
- docker logs: 最近一批请求 (21:30-23:03 UTC) 全部 glm5_2_nv first-attempt，零 NV-TIER-FAIL（除一次 5-key 全 fail 后 fallback），零 error/warn
- Fallback chain: **working** — `tier_chain=['glm5_2_nv', 'dsv4p_nv']` (dynamic fallback，双向)
- 日志中观察到一次 glm5_2_nv→dsv4p_nv fallback-success: `[NV-TIER-FAIL] tier=glm5_2_nv all 5 keys failed: 429=0, empty200=1, timeout=0, other=0, elapsed=60619ms` → `[NV-FALLBACK-SUCCESS]`

### 2.2 环境配置 (HM1 nv_gw)

| 参数 | 值 |
|------|-----|
| TIER_TIMEOUT_BUDGET_S | 114 |
| KEY_COOLDOWN_S | 25 |
| TIER_COOLDOWN_S | 20 |
| MIN_OUTBOUND_INTERVAL_S | 0 |
| NVU_CONNECT_RESERVE_S | 0 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 |
| NVU_EMPTY_200_FASTBREAK | 1 |
| NVU_FORCE_STREAM_UPGRADE | 0 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 |
| FALLBACK_HEALTH_THRESHOLD | 0.10 |
| NVU_PEER_FALLBACK_ENABLED | 1 |
| NVU_PEER_FALLBACK_TIMEOUT | 45 |
| NVU_PEER_FALLBACK_URL | http://100.109.57.26:40006 |
| NVU_PROXY_URL1-5 | (全部空 = DIRECT) |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 |

### 2.3 DB 统计 (6h 窗口, UTC)

| 指标 | 值 |
|------|-----|
| 6h total | 65 |
| 6h OK | 64 |
| 6h ATE | 1 |
| 6h SR | 98.5% |
| 6h avg latency | 29.0s |

### 2.4 按模型统计

| Model | Total | OK | SR | ATE | Avg | P50 | P95 |
|-------|-------|----|-----|-----|-----|-----|-----|
| dsv4p_nv | 6 | 6 | 100.0% | 0 | 97.3s | 82.6s | 138.6s |
| glm5_2_nv | 59 | 58 | 98.3% | 1 | 22.1s | 11.7s | 58.7s |

### 2.5 ATE 详细

| tiers_tried_count | cnt | avg_latency |
|-------------------|-----|-------------|
| 2 | 1 | 121.1s |

- 唯一 ATE: 双tier耗尽 (dsv4p_nv + glm5_2_nv 均失败)，NVCF 上游问题，不可通过配置修复

### 2.6 最新 10 请求

| Time (UTC) | Model | Key | Status | Error | Duration | Fallback |
|------------|-------|-----|--------|-------|----------|----------|
| 15:03:47 | glm5_2_nv | K1 | 200 | — | 2.9s | f |
| 15:03:35 | glm5_2_nv | K5 | 200 | — | 11.8s | f |
| 15:03:21 | glm5_2_nv | K4 | 200 | — | 11.6s | f |
| 14:33:48 | glm5_2_nv | K3 | 200 | — | 4.7s | f |
| 14:33:36 | glm5_2_nv | K2 | 200 | — | 11.9s | f |
| 14:33:21 | glm5_2_nv | K1 | 200 | — | 13.1s | f |
| 14:03:41 | glm5_2_nv | K5 | 200 | — | 3.7s | f |
| 14:03:31 | glm5_2_nv | K4 | 200 | — | 9.7s | f |
| 14:03:21 | glm5_2_nv | K3 | 200 | — | 8.3s | f |
| 13:35:01 | glm5_2_nv | K2 | 200 | — | 54.3s | f |

---

## 3. 决策: NOP

**判定依据**:
- 6h SR 98.5% — 极高水平，无优化空间
- 唯一 ATE 为 tiers_tried_count=2（双tier耗尽），NVCF 上游双函数同时故障，不可通过配置参数修复
- FALLBACK_GRAPH 双向活跃，fallback 成功触发
- KEYS 全部 DIRECT 模式，配置稳定
- 无 error/warn 日志，无 429 限流，无 timeout 异常
- 数据与 R898 完全一致（65/64 98.5% SR, 1 ATE all_tiers_exhausted）
- 触发类型: false trigger (double-dispatch #16)

**决策**: 零修改 (NOP)

---

## 4. HM1 vs HM2 对比

| 指标 | HM1 | HM2 |
|------|-----|-----|
| 6h SR | 98.5% | ~98.5% (连续多轮一致) |
| ATE | 1 (tiers_tried=2) | 1 (tiers_tried=2) |
| FALLBACK_GRAPH | 双向活跃 | 双向活跃 |
| Key路由 | 全部DIRECT | 全部DIRECT |

---

## ⏳ 轮到HM1优化HM2