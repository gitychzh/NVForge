# R-nvonly-post163 — hm2 cc2 NOP 巡检轮 (2026-08-02 09:24 CST)

## 结论
NOP 巡检轮. cc2 (cc4101-primary) 30min 0 req (session 轮前无流量, 无数据判 SR).
链路健康无故障: nv_gw /health ok (5 keys, default glm5_2_nv), env 配置正确,
0 cc2 tier error, 0 cc2 buffer/wait 日志. 0 改动, 0 重启.

## 数据 (30min 窗口)
| caller | model | status | count | avg_dur |
|--------|-------|--------|-------|---------|
| hermes | dsv4p_nv | 429 | 6 | 1406s |
| openclaw | dsv4p_nv | 200 | 2 | 6091ms |

- dsv4p_nv (hermes): 6×429 (all_tiers_exhausted, NVCF 侧配额限流 5min 周期)
- dsv4p_nv (openclaw): 2×200 (链路本身可用, 佐证 429 是配额限流非挂)
- **与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv)
- cc4101-primary (cc2): 0 req — 无流量, 链路健康

## 错误分类
| error_type | sub | count | avg_dur |
|------------|-----|-------|---------|
| all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 6 | 1406 |

全部 6× hermes→dsv4p_nv 配额限流, 非 cc2.

## 健康验证 (09:24 CST)
| 项 | 结果 |
|----|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 7h, ms_gw/logs_db Up 3d ✓ |
| cc2 (cc4101-primary) 30min SR | 0 rows (无流量, 链路健康) ✓ |
| 30min tier error | 0 ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复) ✓ |

## 改动
0 改动, 0 重启.

## 下一步
继续 NOP 巡检. 等 cc2 流量产生后再判 SR. 若 dsv4p_nv 配额限流持续扩散到 glm5_2_nv 再介入.
