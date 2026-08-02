# R-nvonly-post186 — hm2 cc2 NOP 巡检轮

**时间**: 2026-08-02 10:50 CST
**主仓 HEAD**: 942e9fa (post185 已 push)
**本轮改动**: 0 改动, 0 重启

## 数据 (30min 窗口, 2026-08-02 ~02:20-02:50 UTC)

### cc2 (cc4101-primary) — 0 req
session 轮前无 cc2 流量产生, 无数据可判 SR. 链路健康无故障.

### 其他 caller (非 cc2 链路)
| caller | model | status | count | avg_dur |
|--------|-------|--------|-------|---------|
| hermes | dsv4p_nv | 429 | 6 | 1654 |

hermes→dsv4p_nv 6×429 all_tiers_exhausted (NVCF 侧 dsv4p 配额限流, 5min 周期 02:20-02:45).
**与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).

### 30min 错误分类
| error_type | sub | count | avg_dur |
|------------|-----|-------|---------|
| all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 6 | 1654 |

全部 6× 是 hermes→dsv4p_nv 的 NVCF 配额限流.

### tier 错误 — 0 (cc2)
### buffer/wait 日志 — 空

## 健康验证 (10:50 CST)
- nv_gw /health: ok, passthrough, 5 keys, default glm5_2_nv ✓
- docker ps: nv_gw/cc4101/nv_gw_stable Up 9h, ms_gw/logs_db Up 3d ✓
- 配置: NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓

## 判稳
SR≥99% 且无 cc2 链路新错误 → NOP 巡检轮. 等 cc2 流量产生后再判 SR.
dsv4p_nv 配额限流仅影响 hermes caller, 未扩散到 glm5_2_nv.

## 下一步
继续 NOP 巡检. 等 cc2 流量产生后再判 SR. 若 dsv4p_nv 配额限流持续扩散到 glm5_2_nv 再介入.
