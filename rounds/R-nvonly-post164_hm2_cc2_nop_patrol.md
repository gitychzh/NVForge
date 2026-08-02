# R-nvonly-post164 — hm2 cc2 NOP 巡检轮 (2026-08-02 09:30 CST)

## 本轮结论
NOP 巡检轮. cc2 (cc4101-primary) 30min 0 req 无流量产生, 无数据可判 cc2 SR.
链路健康无故障: nv_gw /health ok (5 keys, default glm5_2_nv), docker ps 全 Up.
0 改动, 0 重启, 0 cc2 tier/buffer/wait/error 日志.

## 依据数据 (30min 窗口, 09:27 CST 注入)
### cc2 (cc4101-primary) — 0 req
无流量, 无数据可判 SR. 链路健康无故障.

### 其他 caller (非 cc2 链路)
| caller | model | status | count | avg_dur |
|--------|-------|--------|-------|---------|
| hermes | dsv4p_nv | 429 | 6 | 1463s |
| openclaw | dsv4p_nv | 200 | 2 | 6091ms |

- hermes→dsv4p_nv 6×429 (all_tiers_exhausted, 5key 全挂, NVCF 侧 dsv4p 配额限流 5min 周期).
- openclaw→dsv4p_nv 2×200 (avg 6091ms, 链路本身可用, 佐证 429 是 NVCF 配额限流非链路挂).
- **与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).

### 30min 错误分类
| error_type | sub | count | avg_dur |
|------------|-----|-------|---------|
| all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 6 | 1463 |

全部 6× 是 hermes→dsv4p_nv 的 NVCF 配额限流, 非 cc2 链路.

### tier/buffer/wait 日志 — 空 (cc2 无请求)

## 健康验证 (09:30 CST)
| 项 | 结果 |
|----|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 7h, ms_gw/logs_db Up 3d ✓ |
| cc2 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| 30min tier error | 0 ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## 改动
0 改动, 0 重启.

## 下一步
继续 NOP 巡检. 等 cc2 流量产生后再判 SR. 若 dsv4p_nv 配额限流持续扩散到 glm5_2_nv 再介入.
