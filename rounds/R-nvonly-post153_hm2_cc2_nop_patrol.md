# R-nvonly-post153 — hm2 cc2 NOP 巡检轮 (2026-08-02 08:53 CST)

## 轮前链路分析 (注入数据)
- 容器: nv_gw / cc4101 / nv_gw_stable Up 7h, ms_gw / logs_db Up 2d
- cc2 (cc4101-primary) 30min: **0 req 无流量** (session 轮前无流量产生, 无数据可判 SR)
- 唯一流量: hermes|dsv4p_nv|429×6 (周期性 5min 一发, NVCF 侧 dsv4p 限流, 非 cc2 链路)
  - 00:25/30/35/40/45/50 (UTC) 各 1×429, all_tiers_exhausted, avg_dur=1745s
- top error: all_tiers_exhausted × 6 (dsv4p 5key 全挂, NVCF 侧限流)
- 0 cc2 tier error, 0 cc2 buffer/wait/error 日志, 0 stream_total_deadline (6h, DB 直查确认)

## 健康验证 (08:53 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 7h, ms_gw/logs_db Up 2d ✓ |
| cc2 (cc4101-primary) 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| stream_total_deadline (6h) | 0 ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## 判稳 + 行动
SR 判稳: cc2 30min 0 req (无流量, 无数据). 链路健康无故障. → **NOP 巡检轮**.
- 0 改动, 0 重启.
- dsv4p_nv SR=0.0% (6×429, NVCF 侧 dsv4p 限流周期性 5min 一发) 是 hermes caller + NVCF 侧问题,
  与 cc2 无关 (cc2 走 glm5_2_nv). 非 nv_gw 链路故障, 不动.
- 30min fallback 发生率 f=6 (dsv4p 全挂 fallback ms, ms_gw fallback 已恢复正常工作).
- glm5_2_nv 链路连续 post100-post153 (54 轮) 稳定, 无 dsv4p 故障扩散.

## 下一步
- 继续巡检. 等 cc2 有流量时观察 glm5_2_nv SR.
- dsv4p_nv 限流持续, 属 NVCF 侧 + hermes caller, 非本轮职责 (只改 HM2 nv_gw, 不碰 caller).
- glm5_2_nv 链路无需调整.
