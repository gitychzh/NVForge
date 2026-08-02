# R-nvonly-post195 hm2_cc2 NOP patrol (2026-08-02 11:25 CST)

## 本轮判定: NOP 巡检轮 (0 改动, 0 重启)

### 依据
- cc2 (cc4101-primary) 30min 窗口: **0 req** — 轮前无流量产生, 无数据可判 SR.
- 链路健康无故障: nv_gw /health ok (5 keys, passthrough, default glm5_2_nv),
  全容器 Up 9h+.
- 30min 错误: hermes→dsv4p_nv 6×429 all_tiers_exhausted (NVCF 侧 dsv4p 配额限流),
  openclaw→dsv4p_nv 1×200. **均非 cc2 链路** (cc2 走 glm5_2_nv).
- cc2 tier/buffer/wait 日志: 0.

### 健康验证 (11:25 CST)
| 项 | 结果 |
|----|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 9h, ms_gw/logs_db Up 3d ✓ |
| cc2 30min SR | 0 rows (无流量, 无故障) ✓ |
| cc2 30min tier error | 0 ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## 结论
链路健康, 0 改动 0 重启. 等 cc2 流量产生后再判 SR.
dsv4p_nv 配额限流未扩散到 glm5_2_nv, 无需介入.

## 下一步
继续 NOP 巡检. 若 dsv4p_nv 限流扩散到 glm5_2_nv 再介入.
