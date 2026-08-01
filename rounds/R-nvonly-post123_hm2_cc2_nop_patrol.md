# R-nvonly-post123 — cc2 NOP 巡检轮 (2026-08-02 07:35 CST)

## 改动
- 0 改动, 0 重启. NOP 巡检轮.

## 依据 (轮前链路分析注入数据)
- cc2 (cc4101-primary) 30min: **0 req** (session 轮前无流量)
- 链路健康无故障: 容器全 Up (nv_gw/cc4101 5h, nv_gw_stable 6h, ms_gw/logs_db 2d)
- env 配置正确: NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), buffer 5×90s=450s, cc4101 deadline 470s
- 0 cc2 tier error, 0 cc2 buffer/wait/error 日志, 0 stream_total_deadline (6h)
- nv_gw /health: ok, passthrough, 5 keys, default glm5_2_nv
- glm5_2_nv 连续 post100-post123 (24 轮) 无 dsv4p 故障扩散

## 其他 caller (非 cc2 链路, 非本轮职责)
- hermes/openclaw 打 dsv4p_nv SR=44.4% (4/9, 4×200 + 5×429/all_tiers_exhausted)
- 周期性 5min 一发 429, NVCF 侧 dsv4p 限流模式
- 30min fallback f=9 (dsv4p 全挂 fallback ms, ms_gw fallback 已恢复正常工作)
- 与 cc2 无关 (cc2 走 glm5_2_nv, 不打 dsv4p_nv)

## 验证
| 项 | 结果 |
|----|------|
| nv_gw /health | ok, 5 keys, default glm5_2_nv ✓ |
| docker ps | 全 Up ✓ |
| cc2 30min SR | 0 rows (无流量, 链路健康) ✓ |
| stream_total_deadline 6h | 0 ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0, FALLBACK=ms_gw:40007 ✓ |

## 下一步
- 继续巡检, 等 cc2 有流量时观察 glm5_2_nv SR
- dsv4p_nv 限流属 NVCF 侧 + hermes/openclaw caller, 非本轮职责
- glm5_2_nv 链路连续 24 轮稳定, 无需调整
