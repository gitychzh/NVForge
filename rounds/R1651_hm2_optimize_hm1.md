# R1651 — HM2→HM1: Restart nv_gw to activate R1646+R1648 compose changes (stale container)

## 触发

Cron detected HM1 commit to GitHub — HM2→HM1 optimization triggered.

## 数据 (HM1 6h)

### 6h 总览

| Metric | Value |
|--------|-------|
| Total requests | 27 |
| Success rate | 15/27 (55.6%) |
| glm5_2_nv OK | 8 (avg 6,552ms, max 8,298ms) |
| glm5_2_nv zombie | 7 (NVCF server-side content-filter) |
| dsv4p_nv OK | 7 (avg 24,555ms, max 37,153ms) |
| dsv4p_nv ATE | 5 (avg 62,279ms, all tiers_tried=1, no peer-fb) |

### dsv4p_nv ATE 详情

| ts | duration_ms | tiers_tried | key_cycle_429s | fallback_occurred |
|----|-------------|-------------|----------------|-------------------|
| 18:04:07 | 64,280 | 1 | 0 | f |
| 18:03:58 | 61,652 | 1 | 0 | f |
| 18:02:56 | 61,533 | 1 | 0 | f |
| 18:01:45 | 61,822 | 1 | 0 | f |
| 18:00:40 | 62,107 | 1 | 0 | f |

### tier_attempts 6h

| tier | error_type | count |
|------|-----------|-------|
| glm5_2_nv | pexec_success | 15 |

零 tier-level 错误。

### 关键发现: 容器未重启 → stale config

**nv_gw 容器 StartedAt**: 2026-07-16T19:34:07Z (R1648 deploy 时间)
**compose 修改时间**: 1784230441 (later than container start)

日志证据:
```
[02:01:42.7] [NV-TIER-BUDGET] tier=dsv4p_nv budget 66.0s remaining 3.9s < 5s minimum, breaking
[02:01:42.7] [NV-PEER-FB] model=dsv4p_nv in peer-fb skip list (NVCF DEGRADING, peer same function also bad)
```

但 compose 中:
- `NVU_TIER_BUDGET_DSV4P_NV: "76"` (R1648)
- `NVU_PEER_FB_SKIP_MODELS: ""` (R1646)

容器运行的是旧配置:
- budget=66s (旧值, 可能是 UPSTREAM_TIMEOUT 或旧 compose 值)
- dsv4p_nv still in peer-fb skip list

**影响**: 5 dsv4p ATE 全部无救援路径:
- 66s budget → 66-62=4s < 5s minimum → 2nd key never attempted
- peer-fallback blocked → 无 HM2 key rescue

## 修改

**HM1**: `docker compose up -d --force-recreate nv_gw` — 重启容器以激活当前 compose 配置。

compose 当前值无变更:
- `NVU_TIER_BUDGET_DSV4P_NV: "76"` (R1648)
- `NVU_PEER_FB_SKIP_MODELS: ""` (R1646)
- 所有其他参数不变

## 验证

```
docker exec nv_gw env | grep NVU_TIER_BUDGET_DSV4P_NV → 76 ✓
docker exec nv_gw env | grep NVU_PEER_FB_SKIP_MODELS → "" (empty) ✓
/health → {"status": "ok"} ✓
```

### 容器内预算验证

| tier | env | budget | peer-fb budget | total |
|------|-----|--------|----------------|-------|
| dsv4p_nv | 76 | 76s | 76+72=148 | < 195 ✓ |
| glm5_2_nv | 120 | 120s | 120+72=192 | < 195 ✓ |
| kimi_nv | (none) | 195s (global) | N/A | = 195 ✓ |

### 2nd-key rescue 验证

- 76-62=14s > 5s minimum ✓
- 14s > 13.6s minimum healthy dsv4p_nv response ✓

### Peer-fallback 验证

- `NVU_PEER_FB_SKIP_MODELS=""` → parsed set() → dsv4p_nv NOT in skip ✓
- `NVU_PEER_FALLBACK_TIMEOUT=72` ≥ HM2 BUDGET=70+2 ✓
- HM2 /health: `{"status": "ok"}` ✓

## 评判

本质是运维修复(restart stale container), 非参数变更。旧容器运行 R1646/R1648 之前的配置导致 dsv4p_nv ATE 无 2nd-key rescue 且 peer-fallback 被误封。重启后 dsv4p_nv BUDGET=76 提供 14s 2nd-key rescue window, peer-fallback 重新启用 → HM2 独立 key pool 救援可用。

预期: dsv4p_nv ATE 从 100% 失败(无救援) → 部分恢复(2nd-key rescue + peer-fallback), 52%→目标 70%+。

不可修错误: glm5_2_nv zombie (NVCF server-side content-filter, 非本地参数可修)。

铁律: 只改HM1不改HM2 改前有数据改后有验证 所有修改写入仓库
## ⏳ 轮到HM1优化HM2