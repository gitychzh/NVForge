# R1646 — HM2→HM1: Clear NVU_PEER_FB_SKIP_MODELS enabling dsv4p_nv peer-fallback

## 数据 (HM1 6h pre-R1645)

| model | total | OK | SR% | avg_latency |
|-------|-------|-----|-----|-------------|
| dsv4p_nv | 12 | 7 | 58.3% | 24,555ms |
| glm5_2_nv | 7 | 4 | 57.1% | 6,620ms |

### dsv4p_nv 失败明细 (5 ATE all_tiers_exhausted)
| ts | duration_ms | key_cycle |
|----|-------------|------------|
| 18:04:07 | 64,280 | [] |
| 18:03:58 | 61,652 | [] |
| 18:02:56 | 61,533 | [] |
| 18:01:45 | 61,822 | [] |
| 18:00:40 | 62,107 | [] |

### glm5_2_nv 失败明细 (3 zombie_empty_completion)
NVCF server-side content-filter, not config-fixable.

## 分析

5 dsv4p_nv ATE **全部无救援路径**:
- `NVU_PEER_FB_SKIP_MODELS: "dsv4p_nv"` → peer-fallback disabled
- `NVU_MS_GW_FALLBACK_MODELMAP` excludes dsv4p_nv (R1609: ms_gw relay broken)
- 5 ATE → 100% failure rate, no rescue path

## 方案

Clear `NVU_PEER_FB_SKIP_MODELS` to enable dsv4p_nv peer-fallback to HM2.

**Budget safety**: HM1 PEER_FALLBACK_TIMEOUT=72 ≥ HM2 BUDGET=70+2=72 ✓
Total: 78 (local) + 72 (peer-fb) = 150 < 205 (BUDGET) ✓

HM2's per-key SOCKS5 gives independent IPs for rescue — dsv4p_nv ATE gets HM2's independent key pool.

## 修改

**HM1** `/opt/cc-infra/docker-compose.yml` line 501:
```
- NVU_PEER_FB_SKIP_MODELS: "dsv4p_nv"
+ NVU_PEER_FB_SKIP_MODELS: ""  # R1646
```

## 验证

- `docker compose up -d nv_gw` → container restarted
- `docker exec nv_gw env | grep NVU_PEER_FB_SKIP_MODELS` → `NVU_PEER_FB_SKIP_MODELS=` (empty) ✓
- `/health` → `{"status": "ok"}` ✓
- Core params: BUDGET=78, PEER_FALLBACK_TIMEOUT=72, UPSTREAM=66, KEY=TIER=60 all intact ✓

## 评判

预期: dsv4p_nv ATE now has peer-fallback rescue path → less total failures, faster recovery.

铁律: 只改HM1不改HM2 ✓ 单参数 ✓
## ⏳ 轮到HM1优化HM2
