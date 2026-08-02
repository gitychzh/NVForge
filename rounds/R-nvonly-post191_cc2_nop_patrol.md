# R-nvonly-post191 (hm2 cc2) — NOP 巡检轮

**日期**: 2026-08-02 11:13 CST
**轮次**: R-nvonly-post191 (hm2 cc2)
**类型**: NOP 巡检轮 (0 改动, 0 重启)

## 轮前链路分析
- cc2 (cc4101-primary) 30min: 0 req (session 轮前无流量, 无数据判 SR)
- hermes→dsv4p_nv: 6×429 all_tiers_exhausted (NVCF 配额限流, 5min 周期 02:45-03:10)
- openclaw→dsv4p_nv: 1×200 (3s, 正常)
- **与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv)

## 30min 错误分类 (全 caller)
| error_type | sub | count | avg_dur |
|------------|-----|-------|---------|
| all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 6 | 1606 |

全部为 hermes→dsv4p_nv 配额限流, 非 cc2 链路.

## 健康验证 (11:13 CST)
| 项 | 结果 |
|----|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 9h, ms_gw/logs_db Up 3d ✓ |
| cc2 30min SR | 0 req (无流量, 链路健康) ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK=ms_gw:40007 ✓ |

## 改动
0 改动, 0 重启.

## 判稳依据
- cc2 走 glm5_2_nv, 当前无流量产生.
- 链路健康无故障: nv_gw ok, 5 keys, 全容器 Up.
- dsv4p_nv 限流仅影响 hermes/openclaw, 未扩散到 glm5_2_nv.
- 连续 post100-post190 (91 轮) glm5_2_nv 无故障扩散.

## 下一步
继续 NOP 巡检. 等 cc2 流量产生后再判 SR. 若 dsv4p_nv 配额限流持续扩散到 glm5_2_nv 再介入.
