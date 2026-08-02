# R-nvonly-post147 — hm2 cc2 NOP 巡检轮 (2026-08-02 08:55 CST)

## 改动
无. 0 改动, 0 重启.

## 依据 (轮前链路分析注入)
- cc2 (cc4101-primary) 30min: 0 req (session 轮前无流量产生, 无数据可判 SR).
- hermes|dsv4p_nv|429 ×6: all_tiers_exhausted, avg_dur=1588s, 5min 一发 (00:10/15/20/25/30/35 UTC).
  → NVCF 侧 dsv4p 限流, 非 cc2 链路 (cc2 走 glm5_2_nv). 与 post135-post146 一致.
- 30min fallback: f=6 (dsv4p 全挂 fallback ms, ms_gw fallback 已恢复正常工作).
- 0 cc2 tier error, 0 cc2 buffer/wait 日志, 0 stream_total_deadline (6h DB 直查).

## 判稳
SR 无数据 (0 req), 但链路健康无故障 → NOP 巡检轮.
glm5_2_nv 链路连续 post100-post147 (48 轮) 无 dsv4p 故障扩散.

## 健康验证
| 项 | 结果 |
|----|------|
| nv_gw /health | ok, passthrough, 5 keys ✓ |
| docker ps | nv_gw/cc4101 Up 7h, nv_gw_stable Up 7h, ms_gw/logs_db Up 2d ✓ |
| env | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), deadline 链对齐 ✓ |

## 下一步
- 继续巡检. 等 cc2 有流量时观察 glm5_2_nv SR.
- dsv4p_nv 限流持续, 属 NVCF 侧 + hermes caller, 非本轮职责.
