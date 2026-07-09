# HM2 Optimize HM1 — Round R966

**日期**: 2026-07-09 13:15 UTC
**触发**: HM1 提交新 commit → cron 派遣 HM2 执行优化
**类型**: UPSTREAM_TIMEOUT 64→60 (-4s)

---

## 1. 触发分析

- 脚本检测到 HM1 提交了新 commit
- 最新 commit: `2936230 R965: HM2→HM1 — NOP (double-dispatch false trigger)`
- R965 末尾标记 `## ⏳ 轮到HM1优化HM2` — HM1 回合，HM1 已提交
- 按规则，HM1 提交后轮到 HM2 优化 HM1

---

## 2. 改前数据 (HM1)

### 2.1 nv_gw env (当前参数)

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 64 | floor-adjacent |
| TIER_TIMEOUT_BUDGET_S | 114 | floor |
| KEY_COOLDOWN_S | 25 | floor |
| TIER_COOLDOWN_S | 25 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | optimal |
| NVU_EMPTY_200_FASTBREAK | 3 | optimal |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 | sync |
| NVU_FORCE_STREAM_UPGRADE | 0 | disabled |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | defensive |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | standard |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | standard |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv,dsv4p_nv | data-backed |

### 2.2 nv_requests 6h

| 总计 | 200 | 失败 | SR |
|------|-----|------|----|
| 33 | 33 | 0 | **100%** |

### 2.3 按 upstream_type

| 路径 | 总数 | 200 | avg_ttfb | avg_dur | max_dur |
|------|------|-----|----------|---------|---------|
| nvcf_pexec | 33 | 33 | 48677ms | 48679ms | 173278ms |

### 2.4 错误分类 (6h)

零错误。

### 2.5 fallback 统计 (6h)

| fallback_occurred | cnt |
|-------------------|-----|
| f | 26 |
| t | 7 |

7/33 (21.2%) glm5_2_nv→dsv4p_nv fallback，全部成功。

### 2.6 24h 错误

| error_type | cnt |
|------------|-----|
| all_tiers_exhausted | 1 |

1 条 ATE (glm5_2_nv, 121s, tiers_tried_count=2, fallback_tiers_used={glm5_2_nv,dsv4p_nv}) — 真正的双 tier 耗尽，非 config 可修复。

### 2.7 nv_tier_attempts 6h

| tier | error_type | cnt | avg_ms | max_ms |
|------|-----------|-----|--------|--------|
| glm5_2_nv | NVCFPexecTimeout | 6 | 51823 | **53473** |
| glm5_2_nv | 504_nv_gateway_timeout | 5 | - | - |
| glm5_2_nv | empty_200 | 3 | - | - |
| glm5_2_nv | budget_exhausted_after_connect | 1 | 51838 | 51838 |

**关键发现**: NVCFPexecTimeout max=53,473ms << UPSTREAM=64 → **10.5s dead headroom**。

### 2.8 容器日志 (最新 relevant)

```
[13:04:24] [NV-CYCLE] tier=glm5_2_nv k2 → 504 (504_nv_gateway_timeout), cycling
[13:05:15] [NV-PEXEC-FASTBREAK] tier=glm5_2_nv 1 consecutive NVCFPexecTimeout → fast-break
[13:10:06] [NV-PEXEC-FASTBREAK] tier=glm5_2_nv 1 consecutive NVCFPexecTimeout → fast-break
```

### 2.9 ms_gw (40007)

| 6h 总计 | 200 | 失败 | SR |
|---------|-----|------|----|
| 0 | 0 | 0 | N/A |

ms_gw 空闲，无优化空间。

---

## 3. 决策

**UPSTREAM_TIMEOUT 64→60 (-4s)。**

### 3.1 诊断

- NVCFPexecTimeout max=53,473ms << UPSTREAM=64 → 10,527ms dead headroom
- R750 规则: 当 NVCFPexecTimeout max < UPSTREAM 超过 3s 且 fallback 健康时，减少 UPSTREAM 是有效优化
- 7/7 fallback 100% SR → fallback 健康
- 1 ATE 24h (双 tier 耗尽) → 非 config 可修复

### 3.2 安全边界

- 新值 60s: 60,000 - 53,473 = 6,527ms buffer ≥ 3s (R751 规则)
- BUDGET=114 >> 60s 安全
- FASTBREAK=1 不变
- 成功路径不受影响 (avg_ttfb=48,677ms << 60s)

### 3.3 预期收益

- 每个 glm5_2_nv 超时节省 4s → 更快 fallback 到 dsv4p_nv
- 减少 BUDGET 浪费 (10.5s × 6 timeout = 63s 累计节省/6h)

---

## 4. 修改

**文件**: `/opt/cc-infra/docker-compose.yml` (line 483)

```diff
-      UPSTREAM_TIMEOUT: "64"  # R723-R742 history
+      UPSTREAM_TIMEOUT: "60"  # R966: UPSTREAM_TIMEOUT 64→60 (-4s)
```

## 5. 验证

- ✅ YAML 语法检查通过
- ✅ `docker compose stop nv_gw && docker compose up -d nv_gw` 成功
- ✅ `docker exec nv_gw env | grep UPSTREAM_TIMEOUT` → 60
- ✅ `/health` → `{"status": "ok"}`
- ✅ 容器 healthy (Up 17 seconds)

---

## 6. 总结

HM1 数据稳定 (33/33 100% SR)，但 glm5_2_nv 有 10.5s dead headroom。减少 UPSTREAM 64→60 释放 4s 超时等待，加速 fallback 路径。单参数，安全边界充足。

铁律遵守: 只改 HM1 不改 HM2。

---

## ⏳ 轮到HM1优化HM2