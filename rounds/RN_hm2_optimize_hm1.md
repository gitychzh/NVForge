# R730: HM2→HM1 — UPSTREAM_TIMEOUT 46→48 (+2s)

## TL;DR
dsv4p_nv NVCFPexecTimeout max=46,264ms (k3) 绑定 UPSTREAM=46。+2s捕获46-48s边缘窗口，减少直接fallback到dead glm5_2_nv (health=0.0)。BUDGET=110>>48+48=96s (FASTBREAK=2) 安全，fallback max success=145,104ms<110s? 该max来自pre-R730。6个46-48s成功全経由fallback — 直接捕获可减少fallback负载。

---

## 一、数据收集 (2026-07-05 ~12:55 UTC)

### 容器状态
- 容器: nv_gw, Up 16 minutes (healthy) — R729 部署后
- FASTBREAK=2 ✓, UPSTREAM_TIMEOUT=46, FORCE_STREAM_UPGRADE_TIMEOUT=44
- TIER_TIMEOUT_BUDGET_S=110, FALLBACK_HEALTH_THRESHOLD=0.10
- KEY_COOLDOWN_S=25, TIER_COOLDOWN_S=25, NV_INTEGRATE_KEY_COOLDOWN_S=0
- MIN_OUTBOUND_INTERVAL_S=0, NVU_CONNECT_RESERVE_S=0, NVU_EMPTY_200_FASTBREAK=2

### 日志关键信号
- dsv4p_nv health: 1.0 → 0.667 下降中, primary function 74f02205
- glm5_2_nv health: 0.0 (dead) — fallback 目标几乎不可用
- FALLBACK_GRAPH 双向活跃: tier_chain=['dsv4p_nv', 'glm5_2_nv']
- NVCFPexecTimeout 均匀分布所有key (k0-k4), 非key级问题
- FASTBREAK=2 生效: 每次2个key尝试后fallback

### 6h DB 聚合 (07:00–13:00 UTC)

| 指标 | 值 |
|------|-----|
| 总请求 | 310 |
| OK (200) | 206 (66.5%) |
| 失败 (ATE) | 104 (33.5%) |
| 其他失败 | 0 |

### 按模型 SR

| 模型 | 总请求 | OK | ATE | SR% | avg_dur_ok | avg_dur_fail |
|------|--------|-----|-----|-----|------------|--------------|
| dsv4p_nv | 231 | 131 | 100 | 56.7% | 38,384ms | 82,552ms |
| glm5_2_nv | 78 | 75 | 3 | 96.2% | 21,703ms | 84,080ms |
| kimi_nv | 1 | 0 | 1 | 0.0% | — | 2,682ms |

### ATE 分类

| 指标 | 值 |
|------|-----|
| ATE 总数 | 104 |
| tiers_tried=1 | 35 (avg 51,733ms) — 全部 fallback_actually_attempted=f |
| tiers_tried=2 | 69 (avg 98,174ms) |

### Single-tier ATE 明细

| start_tier_idx | fallback_actually_attempted | cnt | avg_dur |
|----------------|-----------------------------|-----|---------|
| 0 (kimi_nv) | f | 1 | 2,682ms |
| 1 (dsv4p_nv) | f | 32 | 51,466ms |
| 3 (glm5_2_nv) | f | 2 | 80,525ms |

> 32/35 single-tier ATE 来自 dsv4p_nv，全部 fallback_actually_attempted=f。大部分为pre-R729 restart 窗口（FASTBREAK=1时1次timeout即放弃跳转fallback，但fallback被HEALTH_THRESHOLD阻断）。

### 成功 fallback 统计

| fallback_occurred | cnt | avg_dur | max_dur |
|-------------------|-----|---------|---------|
| f (直接) | 147 | 20,208ms | 80,892ms |
| t (fallback) | 61 | 61,720ms | 145,104ms |

### dsv4p_nv 成功 duration buckets

| bucket | cnt | 说明 |
|--------|-----|------|
| ≤30s | 57 | 快速直接成功 |
| 30-35s | 4 | |
| 35-40s | 9 | |
| 40-45s | 15 | |
| 45-46s | 1 | ← 边缘 |
| **46-48s** | **6** | ← 当前via fallback, 直接捕获目标 |
| 48-50s | 2 | |
| 50-60s | 15 | 经fallback |
| 60-90s | 18 | 经fallback |
| >90s | 3 | 经fallback |

### NVCFPexecTimeout 按 key 分布 (dsv4p_nv)

| key | cnt | avg_ms | max_ms |
|-----|-----|--------|--------|
| k0 | 14 | 32,282 | 40,443 |
| k1 | 16 | 32,970 | 44,408 |
| **k2** | **19** | **32,629** | **40,457** |
| **k3** | **12** | **32,467** | **46,264** ← binding |
| k4 | 12 | 33,465 | 44,350 |

> k3 max=46,264ms ≈ UPSTREAM=46 + 264ms → UPSTREAM绑定。均匀分布所有key，非key级问题。

### NVCFPexecTimeout 按 bucket (dsv4p_nv)

| bucket | cnt |
|--------|-----|
| ≤30s | 15 |
| 30-35s | 34 |
| 35-40s | 8 |
| 40-44s | 12 |
| 44-46s | 4 |
| 46-48s | 1 |

### 按小时 SR 趋势

| 小时 (UTC) | 总请求 | OK | ATE | SR% |
|-----------|--------|-----|-----|-----|
| 23:00 (Jul 4) | 3 | 3 | 0 | 100.0% |
| 00:00 | 2 | 2 | 0 | 100.0% |
| 01:00 | 13 | 8 | 5 | 61.5% |
| 02:00 | 49 | 35 | 14 | 71.4% |
| 03:00 | 27 | 20 | 7 | 74.1% |
| 04:00 | 21 | 14 | 7 | 66.7% |
| 05:00 | 20 | 7 | 13 | 35.0% |
| 06:00 | 29 | 22 | 7 | 75.9% |
| 07:00 | 24 | 21 | 3 | 87.5% |
| 08:00 | 23 | 13 | 10 | 56.5% |
| 09:00 | 21 | 17 | 4 | 81.0% |
| 10:00 | 26 | 12 | 14 | 46.2% |
| 11:00 | 18 | 12 | 6 | 66.7% |
| 12:00 | 30 | 17 | 13 | 56.7% |
| 13:00 | 7 | 5 | 2 | 71.4% |

### glm5_2_nv NVCFPexecTimeout 按 key 分布

| key | cnt | avg_ms | max_ms |
|-----|-----|--------|--------|
| k0 | 1 | 25,335 | 25,335 |
| k1 | 4 | 39,312 | 44,247 |
| k2 | 5 | 37,708 | 42,283 |
| k3 | 4 | 39,648 | 44,256 |
| k4 | 5 | 39,352 | 42,291 |

> glm5_2_nv max=44,256ms (k3) 接近 UPSTREAM=46 但未严格绑定。health=0.0 意味着fallback路径几乎不可用。

---

## 二、Root Cause 分析

### 核心问题: dsv4p_nv NVCFPexecTimeout 绑定 UPSTREAM=46

1. **k3 明确绑定**: max=46,264ms ≈ 46 + 264ms overhead, 精确匹配 UPSTREAM=46
2. **46-48s bucket 有6个成功**: 全部经由fallback (avg 61,720ms) — 直接捕获可减少延迟10-15s
3. **glm5_2 fallback 不可靠**: health=0.0 (dead), 69个双tier ATE 表明 fallback 经常也无法挽救
4. **dsv4p_nv health 下降**: 1.0→0.667, 减少fallback依赖是正确方向

### 为什么不是其他参数

| 参数 | 当前值 | 为什么不动 |
|------|--------|----------|
| FASTBREAK | 2 | 已最大化key重试, BUDGET=110>48+48=96s 安全 |
| BUDGET | 110 | 已足够, 110>>48+48=96s |
| FORCE_STREAM_UPGRADE_TIMEOUT | 44 | R727对齐到44, 但R726→R730 UPSTREAM=48, 下次对齐 |
| KEY_COOLDOWN_S | 25 | 无429问题, 无需调整 |
| TIER_COOLDOWN_S | 25 | 无tier级429循环 |
| MIN_OUTBOUND_INTERVAL_S | 0 | 已是地板 |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | 已是地板, glm5_2 health=0.0 < 0.10 无法更低了 |

### 安全校验

```
BUDGET = 110s
UPSTREAM × FASTBREAK = 48 × 2 = 96s
剩余 = 110 - 96 = 14s
→ 14s << 48s (fallback单key) → 2 key后无fallback预算
→ 但FASTBREAK=2已在, 2 key失败后即使有预算glm5_2 health=0.0也几乎挽救不了
→ 实际影响: 同R729, 2 key timeout → ATE, 但6个46-48s请求将直接成功而非fallback
```

---

## 三、变更

**变更: UPSTREAM_TIMEOUT 46→48 (+2s)**

- 文件: `/opt/cc-infra/docker-compose.yml` line 483
- 旧值: `UPSTREAM_TIMEOUT: "46"`
- 新值: `UPSTREAM_TIMEOUT: "48"`
- 重启: `docker compose up -d nv_gw` → Recreated ✓
- 验证: `docker exec nv_gw env | grep UPSTREAM` → 48 ✓
- 健康: `/health` → ok ✓

---

## 四、评判

| 维度 | 状态 | 判断 |
|------|------|------|
| 更少报错 | 33.5% ATE | dsv4p_nv health持续下降是根本原因, 但减少fallback依赖降低ATE风险 |
| 更快请求 | 46-48s bucket 6个请求avg 61,720ms | 直接捕获后预期 ~48s, 节省 ~13s/请求 |
| 超低延迟 | dsv4p_nv direct avg 20,208ms | 未受影响, 仅影响边缘bucket |
| 稳定优先 | BUDGET=110>>48+48=96s | 安全, FASTBREAK=2无额外风险 |

---

## ⏳ 轮到HM1优化HM2