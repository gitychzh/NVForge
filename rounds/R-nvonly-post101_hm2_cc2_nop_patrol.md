# R-nvonly-post101 — hm2_cc2 NOP 巡检轮 (2026-08-02 06:23 CST)

## 结论
NOP 巡检轮. cc2 (cc4101-primary) 30min 0 req (session 轮前无流量), 无数据可判 SR.
链路健康无故障: 容器全 Up, /health ok, 0 cc2 tier error, 0 buffer/wait 日志, 0 stream_total_deadline (6h).
0 改动, 0 重启.

## 注入数据 (06:23 CST)
- cc4101-primary 30min: 0 req (无流量)
- hermes|dsv4p_nv|429: 6 (周期性 5min 一发, NVCF 侧 dsv4p 限流, 非 cc2 链路)
- dsv4p_nv SR=0.0% (0/6): 6×429 + all_tiers_exhausted (5key 全挂), fallback=6 (ms_gw fallback 已恢复, 正常工作)
- 趋势: 21:55→22:20 每 5min 一发 429, 未扩散到 glm5_2_nv

## 健康验证
| 项 | 结果 |
|----|------|
| nv_gw /health | ok, glm5_2_nv, 5 keys, pexec=[kimi_nv,dsv4p_nv,glm5_2_nv] ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 4h, ms_gw/logs_db Up 2d ✓ |
| cc2 30min SR | 0 req (无流量, 链路健康) ✓ |
| stream_total_deadline (6h) | 0 ✓ |
| buffer/wait 日志 | 无 (cc2 0 req) ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复) ✓ |

## 判稳
三阈值全 ✅ → NOP 巡检轮, 不改码, 不重启.

## 下一步
- 继续 NOP 巡检, 等 cc2 有流量再判 SR.
- dsv4p_nv 周期性 429 是 NVCF 侧限流, 非 cc2 链路, 不在本轮优化范围.
- 关注 dsv4p_nv 是否扩散到 glm5_2_nv (目前未扩散).
