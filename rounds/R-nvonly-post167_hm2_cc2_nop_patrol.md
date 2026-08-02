# R-nvonly-post167 — NOP 巡检轮 (hm2 cc2)

**日期**: 2026-08-02 09:36 CST
**上轮**: R-nvonly-post166 (commit 2d027a7)
**本轮改动**: 0 (NOP 巡检)
**本轮重启**: 0

## 判稳依据

### 1. cc4101-primary (cc2) 30min — 0 req
本轮 30min 窗口 cc2 无请求产生 (session 轮前无流量). 无数据可判 SR, 但链路健康无故障.

### 2. 其他 caller (非 cc2 链路)
| caller | model | status | count | avg_dur |
|--------|-------|--------|-------|---------|
| hermes | dsv4p_nv | 429 | 6 | 1529s |
| openclaw | dsv4p_nv | 200 | 2 | (佐证链路可用) |

dsv4p_nv (hermes): 6×429 all_tiers_exhausted (5key 全挂, NVCF 侧 dsv4p 配额限流, 5min 周期 01:10/01:15/.../01:35).
dsv4p_nv (openclaw): 2×200 佐证链路本身可用, 429 是 NVCF 配额限流非链路挂.
**与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).

### 3. 30min 错误分类
| error_type | sub | count | avg_dur |
|------------|-----|-------|---------|
| all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 6 | 1529 |

全部 6× 是 hermes→dsv4p_nv NVCF 配额限流.

### 4. tier 错误 (cc2) — 0
### 5. buffer/wait 日志 — 空

## 健康验证 (09:36 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 8h, ms_gw/logs_db Up 3d ✓ |
| cc2 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| 30min tier error (cc2) | 0 ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0, FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## 决策
SR 无数据可判 (0 req), 无新错误, 链路健康 → NOP 巡检轮.
- 0 改动, 0 重启
- dsv4p_nv 配额限流是 NVCF 侧问题, 非链路故障, 非 cc2 链路, 不介入
- glm5_2_nv 连续 post100-post167 (68 轮) 无 dsv4p 故障扩散

## 下一步
继续 NOP 巡检. 等 cc2 流量产生后再判 SR. 若 dsv4p_nv 配额限流持续扩散到 glm5_2_nv 再介入.

## 参数快照 (无变化, 同 post166)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, BUFFER_TOTAL_DEADLINE=450s, TIER_TIMEOUT_BUDGET=180s, UPSTREAM_TIMEOUT=90s, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, MIN_OUTBOUND_INTERVAL_S=10, TIER_COOLDOWN_S=180, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, NVU_FORCE_STREAM_UPGRADE=0, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150, CC4101_PRIMARY_SKIP_S=30, CC4101_PRIMARY_FAIL_THRESHOLD=3, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, PRIMARY_UPSTREAM_MODEL=glm5_2_nv, FALLBACK_UPSTREAM_MODEL=glm5_2_ms
