# R-nvonly-post166 — hm2 cc2 NOP 巡检轮

**时间**: 2026-08-02 09:35 CST
**上轮**: R-nvonly-post165 (48a41df, 已 push)
**本轮类型**: NOP 巡检轮 (无流量, 无故障, 0 改动, 0 重启)

## 轮前链路分析 (30min 窗口)

### cc2 (cc4101-primary) 30min — 0 req
本轮 30min 窗口 cc2 无请求产生. 无数据可判 cc2 SR. 链路健康无故障.

### 其他 caller (hermes/openclaw, 非 cc2 链路)
| caller | model | status | count | avg_dur |
|--------|-------|--------|-------|---------|
| hermes | dsv4p_nv | 429 | 6 | 1478s |
| openclaw | dsv4p_nv | 200 | 2 | 6091ms |

dsv4p_nv (hermes): 6×429 (all_tiers_exhausted, 5key 全挂, NVCF 侧 dsv4p 配额限流, 5min 周期).
dsv4p_nv (openclaw): 2×200 (avg_dur 6091ms, 链路本身可用, 佐证 429 是 NVCF 配额限流非链路挂).
**与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).

### 30min 错误分类
| error_type | sub | count | avg_dur |
|------------|-----|-------|---------|
| all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 6 | 1478 |

全部 6× 是 hermes→dsv4p_nv 的 NVCF 配额限流, 非 cc2 链路.

### tier error / buffer / wait — 0 / 空 (cc2)

## 健康验证 (09:35 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 8h, ms_gw/logs_db Up 3d ✓ |
| cc2 (cc4101-primary) 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| 30min tier error | 0 ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## 判稳结论
SR 无法判定 (cc2 30min 0 req). 链路健康无故障, 无新错误. → NOP 巡检轮.
dsv4p_nv 429 是 NVCF 侧配额限流 (hermes caller), 未扩散到 glm5_2_nv, 非 cc2 链路问题.

## 改动
无 (NOP 巡检轮).

## 参数快照 (2026-08-02 09:35 CST)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, BUFFER_TOTAL_DEADLINE=450s, TIER_TIMEOUT_BUDGET=180s, UPSTREAM_TIMEOUT=90s, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, PRIMARY_UPSTREAM_MODEL=glm5_2_nv

## 下一步
继续 NOP 巡检. 等 cc2 流量产生后再判 SR. 若 dsv4p_nv 配额限流持续扩散到 glm5_2_nv 再介入.
