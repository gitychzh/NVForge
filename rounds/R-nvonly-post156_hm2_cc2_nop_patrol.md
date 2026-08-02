# R-nvonly-post156 — hm2 cc2 NOP 巡检轮 (2026-08-02 09:01 CST)

## 轮前数据 (注入)
- cc2 (cc4101-primary) 30min: 0 req (session 轮前无流量)
- 链路健康无故障: 容器全 Up (nv_gw/cc4101/nv_gw_stable Up 7h, ms_gw/logs_db Up 2d), env 正确, 0 cc2 tier/buffer/wait/error, 0 stream_total_deadline (6h)
- hermes/dsv4p_nv: 6×429 all_tiers_exhausted (周期性 5min 一发, avg_dur=1654s, NVCF 侧 dsv4p 限流, 非 cc2 链路)

## 决策
SR 无数据 (0 req) + 链路健康无新错误 → **NOP 巡检轮**, 0 改动 0 重启.

## 验证 (09:01 CST)
- 轮前链路分析注入数据与 post155 一致: cc2 0 req, dsv4p_nv 6×429 周期性限流
- 容器/env 配置未变 (上轮已确认, 本轮无改动无需重启复测)
- 配置: NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓

## 结论
glm5_2_nv (cc2 链路) 连续 post100-post156 (57 轮) 无 dsv4p 故障扩散.
dsv4p_nv 429 是 NVCF 侧 dsv4p 限流 (周期性 5min 一发, 00:35-01:00 UTC), 非 cc2 链路问题 (cc2 走 glm5_2_nv).
ms_gw fallback 正常工作 (f=6).
0 改动, 0 重启.

## 下一步
继续 NOP 巡检. 等 cc2 有真实流量时复测 glm5_2_nv SR.
