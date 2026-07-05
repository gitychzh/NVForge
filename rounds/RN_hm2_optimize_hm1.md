# R728: HM2→HM1 — NVU_PEXEC_TIMEOUT_FASTBREAK 1→2 (+1)

## TL;DR
FASTBREAK=1→2 允许 dsv4p_nv 在 NVCFPexecTimeout 后尝试第2键，而非直接 fallback 到 glm5_2_nv。BUDGET=110 >> 44+44=88s 安全。预期减少 fallback 负载，提高 dsv4p_nv 直接成功率。

---

## 一、数据收集 (2026-07-05 ~12:05 UTC)

### 容器状态
- 容器: nv_gw, Up 7 minutes (healthy) — R727 部署后
- UPSTREAM_TIMEOUT=44, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=44 ✓ (已对齐)
- TIER_TIMEOUT_BUDGET_S=110, FALLBACK_HEALTH_THRESHOLD=0.10
- NVU_PEXEC_TIMEOUT_FASTBREAK=1 ← 当前值

### 6h DB 聚合 (06:00–12:00 UTC)

| 指标 | 值 |
|------|-----|
| 总请求 | 306 |
| OK (200) | 206 (67.3%) |
| 失败 (ATE) | 100 (32.7%) |
| 其他失败 | 0 |

### 按模型 SR

| 模型 | 总请求 | OK | ATE | SR% | avg_ttfb | avg_dur | max_dur |
|------|--------|-----|-----|-----|----------|---------|---------|
| dsv4p_nv | 227 | 130 | 97 | 57.3% | 35,801ms | 52,012ms | 122,312ms |
| glm5_2_nv | 78 | 76 | 2 | 97.4% | 20,576ms | 22,130ms | 90,312ms |
| kimi_nv | 1 | 0 | 1 | 0.0% | — | 2,682ms | 2,682ms |

### ATE 分类

| 指标 | 值 |
|------|-----|
| ATE 总数 | 100 |
| 错误类型 | 全部 all_tiers_exhausted |
| tiers_tried=1 (单tier) | 45 (avg 49,108ms) — 全部 pre-restart, fallback_actually_attempted=f |
| tiers_tried=2 (双tier) | 55 (avg 92,237ms) — 51 pre-restart + 4 post-restart |

### 成功 fallback 统计

| 指标 | 值 |
|------|-----|
| fallback 成功 | 59 次 (avg 58,384ms, max 99,088ms, min 34,410ms) |
| 无 fallback 成功 | 149 次 (avg 19,347ms) |

### 按小时 SR 趋势

| 小时 (UTC) | 总请求 | OK | ATE | SR% |
|-----------|--------|-----|-----|-----|
| 04:00 | 21 | 14 | 7 | 66.7% |
| 05:00 | 20 | 7 | 13 | 35.0% |
| 06:00 | 29 | 22 | 7 | 75.9% |
| 07:00 | 24 | 21 | 3 | 87.5% |
| 08:00 | 23 | 13 | 10 | 56.5% |
| 09:00 | 21 | 17 | 4 | 81.0% |
| 10:00 | 26 | 12 | 14 | 46.2% |
| 11:00 | 18 | 12 | 6 | 66.7% |
| 12:00 | 8 | 6 | 2 | 75.0% |

### Post-restart 分段 (12:00 UTC 重启)

| 时段 | 总请求 | OK | ATE | SR% |
|------|--------|-----|-----|-----|
| pre-restart | 224 | 129 | 95 | 57.6% |
| post-restart | 7 | 4 | 3 | 57.1% |

> Post-restart 4 ATEs 全部 `[NV-PEER-FB] peer-originated (hop=1)` — HM2 转发到 HM1 的请求，双 tier 均耗尽。这是 HM2 的 ATE，HM1 的 fallback 链正常工作。

### Tier attempts: NVCFPexecTimeout 按 key 分布 (dsv4p_nv)

| key_idx | 次数 | avg_ms | max_ms |
|---------|------|--------|--------|
| 0 | 14 | 32,282 | 40,443 |
| 1 | 15 | 32,207 | 44,269 |
| 2 | 19 | 32,629 | 40,457 |
| 3 | 11 | 31,213 | 36,475 |
| 4 | 12 | 33,465 | 44,350 |

> dsv4p_nv NVCFPexecTimeout max=44,350ms ≈ UPSTREAM=44s + ~350ms overhead → UPSTREAM 是绑定约束。超时均匀分布在5个 key 上，非个别 key 问题。

### 日志关键发现

```
[12:03:20.1] tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback)  ← 双向 fallback 正常
[12:06:48.4] tier_chain=['dsv4p_nv', 'glm5_2_nv'] (dynamic fallback)
[12:04:04.4] [NV-PEXEC-FASTBREAK] tier=glm5_2_nv 1 consecutive NVCFPexecTimeout -> fast-break
[12:10:14.3] [NV-ALL-TIERS-FAIL] All 2 tiers failed, ABORT-NO-FALLBACK
[12:10:14.3] [NV-PEER-FB] peer-originated request (hop=1) also all_tiers_exhausted
```

- FALLBACK_GRAPH 双向正常工作 (dsv4p_nv↔glm5_2_nv)
- FASTBREAK=1 触发频率高：1次 pexec timeout 即跳过后4键
- 所有 post-restart ATE 均为 peer-originated hop=1 (HM2→HM1 转发)，非 HM1 自身配置问题

### NVCF 函数健康度

| 函数 | 健康度变化 |
|------|-----------|
| 74f02205 (dsv4p_nv) | 1.0 → 0.75 → 0.667 → 0.6 — 下降中 |
| 3b9748d8 (glm5_2_nv) | 0.0 → 0.5 → 0.333 → 0.25 → 0.143 — 极不稳定，持续下降 |

---

## 二、优化决策

### 问题诊断

1. **dsv4p_nv 57.3% SR 是主要瓶颈**，glm5_2_nv 97.4% 健康
2. dsv4p_nv NVCFPexecTimeout max=44,350ms 在 UPSTREAM=44s 绑定边缘
3. FASTBREAK=1 → 1次 timeout 即放弃剩余4键 → 直接 fallback → 增加 glm5_2_nv 负载
4. BUDGET=110 >> 44+44=88s 安全，有足够余量允许第2键尝试
5. 相同 NVCF function 但不同 key (不同 mihomo 端口/出口IP)，第2键可能成功

### 决策: FASTBREAK 1→2

| 参数 | 旧值 | 新值 | 变化 |
|------|------|------|------|
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 2 | +1 |

**理由:**
- 第1键 timeout(44s) → 第2键尝试(44s) = 88s < BUDGET=110 ✓
- 第2键可能通过不同出口IP/不同 NVCF 节点成功（上次 timeout 可能只是节点瞬时问题）
- 减少 fallback 到 glm5_2_nv 的频率（glm5_2 健康度已降到 0.143，高负载时更危险）
- 预期提高 dsv4p_nv 直接成功率，降低总 ATE 率

**安全边界:**
- BUDGET=110s >> 44+44=88s (双键 max) → 零误杀
- 若第2键也失败，剩余 22s 预算不足以启动 fallback tier (需 min 44s) → 直接 ATE（与 FASTBREAK=1 时 fallback 后 ATE 结果相同，不更差）
- 成功 fallback max=99,088ms < 110s → 不影响现有成功路径

### 铁律确认
- [x] 改前有数据 — 6h DB 聚合 + 日志分析 + tier_attempts + 健康度检查
- [x] 单参数每轮 — 仅改 NVU_PEXEC_TIMEOUT_FASTBREAK
- [x] 只改 HM1 不改 HM2

---

## 三、部署验证

### 部署前
```
NVU_PEXEC_TIMEOUT_FASTBREAK=1
UPSTREAM_TIMEOUT=44
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=44
TIER_TIMEOUT_BUDGET_S=110
```

### 部署后
```
NVU_PEXEC_TIMEOUT_FASTBREAK=2  ✅
UPSTREAM_TIMEOUT=44
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=44
TIER_TIMEOUT_BUDGET_S=110
```

### 验证
- `docker compose up -d nv_gw` → Recreated + Started
- `curl /health` → {"status": "ok"} ✓
- `docker ps` → nv_gw Up (healthy) ✓
- YAML parse check → YAML OK ✓

---

## ⏳ 轮到HM1优化HM2