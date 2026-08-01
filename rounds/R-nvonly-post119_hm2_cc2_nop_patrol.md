# R-nvonly-post119 — hm2_cc2 NOP 巡检轮 (2026-08-02 07:19 CST)

## 轮前链路分析 (注入数据)
- cc2 (cc4101-primary) 30min: **0 req** (session 轮前无流量, 无 SR 数据)
- dsv4p_nv SR=44.4% (4/9): 4×200 + 5×429(all_tiers_exhausted), 周期性 5min 一发 429
  - 全 hermes/openclaw caller 打的, **非 cc2 链路** (cc2 走 glm5_2_nv)
  - 30min fallback f=9 (dsv4p 全挂 fallback ms_gw, fallback 已恢复工作)
- 30min 错误分类: all_tiers_exhausted × 5 (avg_dur 1266s), 全 dsv4p
- 0 stream_total_deadline (6h)

## 判稳
- cc2 30min 0 req → 无数据 → 按铁律「改前必有数据」NOP 巡检轮, 不改码.
- glm5_2_nv 连续 post100-post119 (20 轮) 无 dsv4p 故障扩散.
- dsv4p_nv 限流持续, 属 NVCF 侧 + hermes/openclaw caller, 非本轮职责.

## 健康验证 (07:19 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 5h, ms_gw/logs_db Up 2d ✓ |
| cc2 (cc4101-primary) 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| stream_total_deadline (6h) | 0 ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), buffer 5×90s=450s, cc4101 deadline 470s ✓ |

## 改动
- 0 改动, 0 重启.

## 下一步
- 继续巡检. 等 cc2 有流量时观察 glm5_2_nv SR.
- glm5_2_nv 链路连续 20 轮稳定, 无需调整.
