# HM2 Optimize HM1 — Round R1448

## 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = opc2_uname (HM2)
- R1447 已提交 (NOP, double-dispatch, 52nd chain of R1395)
- 本回合为 false trigger double-dispatch → R1448

## 数据收集 (改前必有数据)

### nv_gw 6h 窗口 (created_at >= now() - 6h)

| model | status | count | avg_ms | max_ms |
|---|---|---|---|---|
| dsv4p_nv | 200 | 1 | 20596 | 20596 |
| dsv4p_nv | 502 | 10 | 82725 | 124070 |
| glm5_2_nv | 200 | 15 | 11591 | 54010 |
| glm5_2_nv | 502 | 11 | 27596 | 187171 |

**Total**: 37 req, 16 OK (200), 21 fail (502) → 43.2% SR

### 错误类型

| error_type | count |
|---|---|
| zombie_empty_completion | 11 |
| all_tiers_exhausted | 10 |

### nv_gw 日志 (最近200行)

```
[19:03:20] glm5_2_nv integrate k1 SUCCESS (14312ms)
[19:03:34] glm5_2_nv integrate k2 SUCCESS (9173ms)
[19:03:40] glm5_2_nv zombie_empty_completion (content_chars=12 < 50, input_chars=216078)
[19:06:51] dsv4p_nv k2 → 504, all 5 keys failed, all_tiers_exhausted (63980ms)
[19:06:51] dsv4p_nv → ms_gw fallback → relay failed after 284097ms (TimeoutError)
```

### ms_gw 日志

- stream_cycle:stream_no_data_lines — 30 attempts per all-exhausted
- ModelScope upstream issue, not config-fixable

### 容器状态

- nv_gw: Up 26 min (healthy) — R1445 重启
- compose md5: `51079b89019ddfb1a08f65e79e847b51`

### 参数状态

nv_gw: UPSTREAM_TIMEOUT=66, BUDGET=66, MIN_OUTBOUND=0(floor), PEER_FALLBACK=66, CONNECT_RESERVE=0(floor), KEY_COOLDOWN=25, TIER_COOLDOWN=15, NVU_PEXEC_TIMEOUT_FASTBREAK=1, INTEGRATE_KEY_COOLDOWN=0(floor), FORCE_STREAM_UPGRADE=0, FORCE_STREAM_UPGRADE_TIMEOUT=66, EMPTY_200_FASTBREAK=3, SSLEOF_RETRY=1.0, FALLBACK_HEALTH_THRESHOLD=0.05, NVU_MS_GW_FALLBACK_TIMEOUT=280

ms_gw: EMPTY_200_FASTBREAK_THRESHOLD=3, KEY_COOLDOWN=60, VARIANT_COOLDOWN=30, MIN_OUTBOUND_INTERVAL=1.0, NUM_KEYS=7, NUM_VARIANTS=10, ALL_EXHAUSTED_COOLDOWN=30

## 分析

1. **dsv4p_nv ATE (all_tiers_exhausted)**: NVCF function 504 — upstream issue, not config-fixable. All 5 keys fail identically. BUDGET=66 already floor. FASTBREAK=1 already floor.
2. **glm5_2_nv zombie**: NVCF content-filter (content_chars < 50, input_chars > 5000) — code-level, not config-fixable.
3. **ms_gw stream_cycle**: ModelScope upstream no-data-lines — not config-fixable.
4. **ms_gw relay TimeoutError**: relay_started=True but ms_gw relay fails at code-level (streaming sync defect) — not config-fixable.
5. **All nv_gw params at floor/optimal**: no optimization headroom.

## 决定

**NOP** — 零参数变更，零 compose 变更，零容器重启。

真实触发: ds_v4p_nv NVCF 504 (upstream) + glm5_2_nv NVCF content-filter (code-level) + ms_gw ModelScope stream_cycle (upstream). 所有可调参数已至 floor。等待上游恢复。

铁律: 只改HM1不改HM2.

## ⏳ 轮到HM1优化HM2
