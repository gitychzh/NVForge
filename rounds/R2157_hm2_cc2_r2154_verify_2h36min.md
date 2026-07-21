# R2157 (hm2_cc2): R2154 cc4101 动态 header timeout 持续验证轮 (2h36min 窗口)

> 巡检轮, 0 改动 0 restart. 接 R2156 (commit 6e4930a) 继续盯 R2154 6 档表 6h 全窗口验证.
> 轮号基线: git log 最新 = 6e4930a R2156. 本轮 = R2157.
> 本轮接全新 session, STATE.md 被手动清成无害标题(无上一轮上下文), 从 git log + 轮文件重建基线.

## 改前数据 (2026-07-21 ~16:05 CST = 08:05Z)

### nv_gw 30min 窗口 (全模型 SR)
| status | count |
|--------|-------|
| 200 | 61 |
| 502 | 7 |

全模型 SR = 61/68 = **89.7%** (502 全是 dsv4p_nv, 见下).

### 30min by mapped_model
| mapped_model | 200 | 502 | SR |
|--------------|-----|-----|-----|
| glm5_2_nv | 61 | 1 | **98.4%** (61/62) |
| dsv4p_nv | 0 | 6 | 0% (NVCF function 全挂, 非本域) |

### 非成功 error_type (30min, 全模型)
| error_type | count | 模型 |
|-------------|-------|------|
| all_tiers_exhausted | 6 | dsv4p_nv (NVCF function 74f02205 全挂) |
| NVAnth_IncompleteRead | 1 | glm5_2_nv (NVCF 上游中断, 良性已知类) |

**glm5_2_nv 路径 0 个 nv_gw 可修错误** (1 个 IncompleteRead 是 NVCF 上游中断).

### 6h glm5_2_nv SR
| status | count | SR |
|--------|-------|-----|
| 200 | 775 | **98.6%** (775/786) |
| 502 | 11 | |

6h 全模型 200/502/429 = 780/183/5 (502 主体是 dsv4p_nv NVCF function 全挂).

### 6h fallback 趋势 (by hour, glm5_2_nv)
| hour (UTC) | total | fb | fb_pct | ok |
|------------|-------|----|--------|-----|
| 02:00 | 131 | 11 | 8.4% | 131 |
| 03:00 | 128 | 24 | 18.8% | 125 |
| 04:00 | 137 | 17 | 12.4% | 136 |
| 05:00 | 107 | 13 | 12.1% | 105 |
| 06:00 | 143 | 11 | 7.7% | 143 |
| 07:00 | 132 | 15 | 11.4% | 127 |
| 08:00 | 14 | 0 | 0% | 14 |

**关键: 每小时 ok≈total**, 即所有 fallback 最终都成功 (被 ms_gw 兜住), **0 真中断**.
fallback 8-19% 区间抖动 = NVCF ttfb 慢的自然抖动, 非 nv_gw 退化.
R2156 记 "fallback=2" 是 30min 小样本; 6h 大窗看 ~10% 是稳态.

### fallback 明细 (30min, 6 条全 glm5_2_nv→glm5_2_ms)
| created_at | ttfb_ms | duration_ms |
|------------|---------|-------------|
| 07:35:10 | 128017 | 189449 |
| 07:38:39 | 123946 | 157283 |
| 07:41:48 | 160317 | 168049 |
| 07:42:29 | 135417 | 176592 |
| 07:45:07 | 128676 | 129148 |
| 07:58:38 | 139565 | 170398 |

全 ttfb 124-160s 档, NVCF 侧 header/ttfb 慢 (s 档), 被 ms_gw 兜住 0 真中断 — 符合热备设计.

### nv_tier_attempts 30min
| error_type | count |
|-------------|-------|
| pexec_success | 60 |
| pexec_conn_RemoteDisconnected | 17 |
| pexec_SSLEOFError | 7 |
| pexec_429 | 2 |
| pexec_empty_200 | 1 |

全 NVCF 侧上游抖动 (conn/SSLEOF/429), 非 nv_gw 旋钮可修.

### cc4101 30min (R2154 后窗口)
- FALLBACK 日志 = **0** (30min 内 cc4101 层无切档, 因 fallback 在 nv_gw 内部完成)
- PRIMARY-FAIL = **0**
- 75s timeout = **0** (R2154 6 档表持续归零 ✅)
- BREAKER = **0**
- 1 条 STREAM-STALL-FAIL (15:50:29, passthrough stall 656605ms): 480s 总 deadline 超时, nv 本身慢 656s 导致的真超时, **非 75s 误杀**

### R2154 后纯窗口 (05:28:51Z 起, 现 08:05Z = **2h36min**, 距 6h 全窗口还差 ~3h24min)
- **75s_timeout = 0** (旧误杀类持续归零 ✅, R2154 6 档表持续生效)
- fallback = 6/64 ≈ 9.4% (全 NVCF ttfb 慢, 被 ms_gw 兜住, **0 真中断**)
- cc4101 StartedAt = `2026-07-21T05:28:51Z` (R2154 restart 实例, RestartCount=0) ✅
- nv_gw StartedAt = `2026-07-21T01:44:55Z`, RestartCount=0, env 无漂移 ✅

## 决策: 巡检轮, 0 改动 0 restart

依据:
1. glm5_2_nv 30min SR 98.4% / 6h 98.6% — 稳态带内, 远超 CLAUDE.md "SR>95%" 巡检线.
2. fallback 全是 NVCF ttfb 慢的良性兜底, 0 真中断 (每小时 ok≈total), 符合 40007 热备设计.
3. 75s_timeout 持续归零, R2154 6 档表持续生效, 6h 验证进行中 (2h36min/6h), 未到终点不改.
4. dsv4p_nv 6×502 是 NVCF function 74f02205 全挂的非本域问题, 非 nv_gw 旋钮能修, 不影响 glm5_2_nv 路径.
5. 唯一 1 个 glm5_2_nv 错 (NVAnth_IncompleteRead) 是 NVCF 上游中断, 良性已知类.

CLAUDE.md 铁律: 数据证明 nv_gw 已稳 (SR>95% 且 fallback 全良性 0 真中断) → 巡检轮, 不改代码.

## 验证 (0 改动无需 restart)
- nv_gw /health: ok, passthrough, 5 keys, RestartCount=0 ✅
- 容器 uptime: nv_gw 6h / cc4101 3h / ms_gw 19h, 无漂移 ✅
- env 无漂移 (UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, KEY_COOLDOWN_S=60, TIER_COOLDOWN_S=180) ✅

## 下一轮
1. R2154 6h 验证窗 (05:28:51Z 起): 现 2h36min, 距 6h 全窗口还差 ~3h24min. 下轮 (~08:35Z+ 拉数据) 应已过 3h, 继续盯 75s_timeout 是否持续 0, fallback 是否仍全 NVCF 慢非误杀.
2. 若 6h 窗口内 75s_timeout 持续 0 且无新误杀类 → R2154 验证收口, 可考虑下轮做点别的 (但优先保持稳态, 不为改而改).
3. dsv4p_nv NVCF function 全挂�� NVCF 侧问题, 等 NVCF 修复, 不本域动手.
4. STATE.md 被手动清空过, 本轮已覆写恢复交接棒.

HM2 only.
