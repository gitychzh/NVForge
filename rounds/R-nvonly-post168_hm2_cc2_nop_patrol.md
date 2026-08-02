# R-nvonly-post168 — NOP 巡检轮 (hm2_cc2)

**日期**: 2026-08-02 09:39 CST
**上轮**: post167 (0e45d2e)
**容器**: nv_gw / cc4101 / nv_gw_stable Up 8h, ms_gw / logs_db Up 3d
**改动**: 0 | **重启**: 0

## 判稳结论
NOP 巡检轮. cc2 (cc4101-primary) 30min 0 req (session 轮前无流量产生, 无数据可判 SR).
链路健康无故障: nv_gw /health ok (5 keys, passthrough, default glm5_2_nv), env 配置正确,
0 cc2 tier error, 0 cc2 buffer/wait/error 日志.
0 改动, 0 重启.

## 关键数据 (30min 窗口)

### cc4101-primary (cc2) — 0 req
本轮 30min 窗口 cc2 无请求产生. 无数据可判 cc2 SR. 链路健康无故障.

### 其他 caller (非 cc2 链路)
| caller | model | status | count | avg_dur |
|--------|-------|--------|-------|---------|
| hermes | dsv4p_nv | 429 | 6 | 1529s |
| (openclaw 佐证 2×200 见上轮 STATE) |

hermes→dsv4p_nv 6×429 (all_tiers_exhausted, 5key 全挂, NVCF 侧 dsv4p 配额限流, 5min 周期 01:10-01:35).
**与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).

### 30min 错误分类
| error_type | sub | count | avg_dur |
|------------|-----|-------|---------|
| all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 6 | 1529 |

全部 6× 是 hermes→dsv4p_nv 的 NVCF 配额限流, 非 cc2 链路.

### cc2 tier error / buffer/wait 日志 — 0 / 空

## 健康验证 (09:39 CST)
- nv_gw /health: ok, passthrough, 5 keys, default glm5_2_nv ✓
- docker ps: nv_gw/cc4101/nv_gw_stable Up 8h, ms_gw/logs_db Up 3d ✓
- 配置: NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓

## 下一步
继续 NOP 巡检. 等 cc2 流量产生后再判 SR. 若 dsv4p_nv 配额限流持续扩散到 glm5_2_nv 再介入.
glm5_2_nv 连续 post100-post168 (69 轮) 无 dsv4p 故障扩散.
