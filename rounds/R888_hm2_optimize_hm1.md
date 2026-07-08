# R888: HM2→HM1 — TIER_COOLDOWN_S 25→20 (-5s)

## 数据收集

### 6h 窗口 (2026-07-08 14:45 UTC → 20:45 UTC)
- **请求**: 38 req, 38 OK (100%), 0 ATE, 0 fail
- **延迟**: avg_ttfb=19,794ms, avg_dur=19,795ms, max_dur=144,743ms
- **上游路径**: 全部 nvcf_pexec (glm5_2_nv)
- **Fallback**: 1 次触发 (glm5_2_nv→dsv4p_nv), 救回成功

### 24h 窗口
- **请求**: 145 req, 103 OK (71.0%), 42 ATE (29.0%)
- **错误类型**: 全部 `all_tiers_exhausted` (server-side, 非 config 可修)

### Tier Attempts (6h)
- glm5_2_nv: 4×504_nv_gateway_timeout + 1×NVCFPexecTimeout (max=51,475ms, k3)

### TTFB 分布 (6h)
| Bucket | Count |
|--------|-------|
| 0-5s   | 13    |
| 5-10s  | 9     |
| 10-20s | 5     |
| 20-30s | 4     |
| 30-60s | 3     |
| 60-120s| 3     |
| 120s+  | 1     |

### 容器环境 (改前)
- UPSTREAM_TIMEOUT=66
- TIER_TIMEOUT_BUDGET_S=114
- FASTBREAK=1, EMPTY_200_FASTBREAK=1
- FORCE_STREAM_UPGRADE_TIMEOUT=66 (synced with UPSTREAM)
- FALLBACK_HEALTH_THRESHOLD=0.10
- KEY_COOLDOWN_S=25, TIER_COOLDOWN_S=25
- CONNECT_RESERVE_S=0, MIN_OUTBOUND_INTERVAL_S=0
- NV_INTEGRATE_KEY_COOLDOWN_S=0

### 日志 (最近100行 error/warn)
```
[18:04:51.2] [NV-CYCLE] tier=glm5_2_nv k2 → 504 (504_nv_gateway_timeout), cycling to next key
[18:05:42.7] [NV-TIMEOUT] tier=glm5_2_nv k3 NVCF pexec timeout: attempt=51475ms total=114056ms
[18:05:42.7] [NV-PEXEC-FASTBREAK] tier=glm5_2_nv 1 consecutive NVCFPexecTimeout -> fast-break (saved remaining keys)
[18:05:42.7] [NV-TIER-FAIL] tier=glm5_2_nv all 5 keys failed: 429=0, empty200=0, timeout=1, other=1, elapsed=114057ms
[18:05:42.7] [NV-FALLBACK] Tier glm5_2_nv all-failed → falling back to dsv4p_nv
[18:06:13.3] [NV-FALLBACK-SUCCESS] Success on fallback tier dsv4p_nv after primary glm5_2_nv failed
```

## 分析

1. **6h 零错误 regime**: 38/38 100% SR, 0 ATE, 1 rescued fallback — 系统健康
2. **NVCFPexecTimeout 非绑定**: max=51,475ms << UPSTREAM=66 (buffer=14.5s >> 3s minimum)
3. **504 gateway timeout**: 4次 NVCF 侧 gateway 超时, 非本地 config 可控
4. **KEY_COOLDOWN=25 ≥ TIER_COOLDOWN=25**: 改前 invariant 满足; 改后 KEY=25 ≥ TIER=20 仍满足
5. **key_cycle_429s=0**: 零 rate-limiting, 降低 cooldown 无 429 风险
6. **empty_200=0**: 无 NVCF empty 200 响应

## 优化决策

**参数**: TIER_COOLDOWN_S 25→20 (-5s)

**理由**:
- 6h 零错误 regime 持续, 0 ATE, 0 key_cycle_429s — 系统有充足安全余量
- 降低 tier cooldown 使 tier 失败后更快恢复可用, 提高 fallback 双向可用性
- KEY_COOLDOWN=25 ≥ TIER_COOLDOWN=20 invariant 保留 (KEY≥TIER 确保 key 不抢先于 tier)
- -5s 最多节省 5s 在 tier 失败后的等待, 对成功路径零影响
- NVCFPexecTimeout max=51.5s << UPSTREAM=66 (buffer 14.5s) — 非绑定, 不需要调整 UPSTREAM
- 单参数, 少改多轮

## 验证

- compose YAML 语法检查通过
- 容器重启成功 (Recreated)
- `docker exec nv_gw env | grep TIER_COOLDOWN_S` → 20 ✅
- KEY_COOLDOWN_S=25 ≥ TIER_COOLDOWN_S=20 ✅

## ⏳ 轮到HM1优化HM2