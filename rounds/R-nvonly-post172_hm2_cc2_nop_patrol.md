# R-nvonly-post172 — NOP 巡检轮 (hm2_cc2)

## 元信息
- 轮号: post172 (R-nvonly 方向)
- 时间: 2026-08-02 10:02 CST
- 主仓 git HEAD: 1ced465 (post171, 上轮)
- 类型: NOP 巡检轮 (无流量无故障, 0 改动 0 重启)

## 本轮依据
- cc2 (cc4101-primary) 30min 窗口 0 req — session 轮前无流量产生, 无数据可判 SR.
- 链路健康: nv_gw /health ok (5 keys, passthrough, default glm5_2_nv), cc4101/nv_gw/ms_gw/logs_db 全 Up.
- 30min tier error: 0 (cc2). buffer/wait 日志: 空.
- hermes→dsv4p_nv 6×429 (all_tiers_exhausted, NVCF 侧 dsv4p 配额限流, 5min 周期 01:25-01:50) — 非 cc2 链路, cc2 走 glm5_2_nv 不打 dsv4p_nv.

## 本轮改动
0 改动, 0 重启.

## 健康验证 (10:02 CST)
| 项 | 结果 |
|----|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 8h, ms_gw/logs_db Up 3d ✓ |
| cc2 30min SR | 0 rows (无流量, 链路健康) ✓ |
| 30min tier error | 0 ✓ |
| 30min 全 caller | hermes 6×429 (dsv4p_nv 限流), cc2 0 req ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## 下一步
继续 NOP 巡检. 等 cc2 流量产生后再判 SR. 若 dsv4p_nv 配额限流扩散到 glm5_2_nv 再介入.
