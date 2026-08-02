# R-nvonly-post154 — hm2 cc2 NOP 巡检轮 (2026-08-02 08:56 CST)

## 轮前数据 (注入)
- cc2 (cc4101-primary) 30min: 0 req (session 轮前无流量)
- 链路健康无故障: 容器全 Up, env 正确, 0 cc2 tier/buffer/wait/error, 0 stream_total_deadline (6h)
- hermes/dsv4p_nv: 6×429 all_tiers_exhausted (周期性 5min 一发, NVCF 侧限流, 非 cc2 链路)

## 决策
SR 无数据 (0 req) + 链路健康无新错误 → **NOP 巡检轮**, 0 改动 0 重启.

## 验证
- nv_gw /health: ok, passthrough, 5 keys, default glm5_2_nv
- docker ps: nv_gw/cc4101/nv_gw_stable Up 7h, ms_gw/logs_db Up 2d
- cc2 30min: 0 req (无流量)
- stream_total_deadline (6h): 0

## 结论
glm5_2_nv (cc2 链路) 连续 post100-post154 (55 轮) 无 dsv4p 故障扩散.
dsv4p_nv 429 是 NVCF 侧限流, fallback ms 正常工作 (f=6).
0 改动, 0 重启.

## 下一步
继续 NOP 巡检. 等 cc2 有真实流量时复测 glm5_2_nv SR.
