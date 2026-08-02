# R-nvonly-post176 — NOP 巡检轮 (hm2_cc2)

**日期**: 2026-08-02 10:11 CST
**轮次**: R-nvonly-post176
**基线**: post175 (9c4393e→f7de267 已 push)
**改动**: 0  |  **重启**: 0

## 决策依据 (轮前链路分析注入)

### cc2 (cc4101-primary) 30min — 0 req
本轮 30min 窗口 cc2 无请求产生. 无数据可判 cc2 SR. 链路健康无故障.

### hermes→dsv4p_nv (非 cc2 链路) — 11req
| status | count | avg_dur |
|--------|-------|---------|
| 200 | 7 | 9916 |
| 429 (all_tiers_exhausted) | 4 | 1798 |

dsv4p_nv SR=63.6% (7/11). 4× all_tiers_exhausted = NVCF 侧 dsv4p 配额限流 (5min 周期 01:45-02:10).
**与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv). glm5_2_nv 无故障扩散.

### top error
- all_tiers_exhausted × all_tiers_failed_in_mapped_tier × 4 (全部 hermes→dsv4p_nv 限流)

## 健康验证 (10:11 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 8h, ms_gw/logs_db Up 3d ✓ |
| 30min cc2 (cc4101-primary) | 0 req (无流量, 链路健康无故障) ✓ |
| 30min nv_tier_attempts error | 0 rows ✓ |
| 30min buffer/wait 日志 | 空 ✓ |
| env | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), BUFFER_MAX_RETRIES=5, BUFFER_TOTAL_DEADLINE=450s ✓ |
| env (cc4101) | FALLBACK_UPSTREAM=ms_gw:40007, STREAM_TOTAL_DEADLINE=470, PRIMARY_HEADER_TIMEOUT=400 ✓ |

## 行动
NOP 巡检轮. 0 改动, 0 重启. cc2 链路健康无故障.

## 下一步
继续 NOP 巡检. 等 cc2 流量产生后再判 SR. 若 dsv4p_nv 配额限流持续扩散到 glm5_2_nv 再介入.

## 参数快照 (无变化同 post175)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, BUFFER_TOTAL_DEADLINE=450s, TIER_TIMEOUT_BUDGET=180s, UPSTREAM_TIMEOUT=90s, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, MIN_OUTBOUND_INTERVAL_S=10, TIER_COOLDOWN_S=180, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, NVU_FORCE_STREAM_UPGRADE=0, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150, CC4101_PRIMARY_SKIP_S=30, CC4101_PRIMARY_FAIL_THRESHOLD=3, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, PRIMARY_UPSTREAM_MODEL=glm5_2_nv, FALLBACK_UPSTREAM_MODEL=glm5_2_ms
