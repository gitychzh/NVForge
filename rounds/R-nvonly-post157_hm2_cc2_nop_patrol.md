# R-nvonly-post157 — hm2 cc2 NOP 巡检轮 (2026-08-02 09:05 CST)

## 轮前数据 (注入 + DB 复查)
- cc2 (cc4101-primary) 30min: 0 req (session 轮前无流量, DB 直查 0 rows 确认)
- 链路健康无故障: 容器全 Up (nv_gw/cc4101/nv_gw_stable Up 7h, ms_gw/logs_db Up 2d), env 正确,
  0 cc2 tier/buffer/wait/error, 0 stream_total_deadline (6h, DB 直查 0 rows)
- hermes/dsv4p_nv: 6×429 all_tiers_exhausted (周期性 5min 一发, NVCF 侧 dsv4p 限流, 非 cc2 链路)
- openclaw/dsv4p_nv: 1×200 (链路本身可用, 佐证 429 是 NVCF 配额限流非链路挂)

## 决策
SR 无数据 (0 req) + 链路健康无新错误 → **NOP 巡检轮**, 0 改动 0 重启.

## 验证 (09:05 CST)
- nv_gw /health: ok, passthrough, 5 keys, default glm5_2_nv ✓
- docker ps: nv_gw/cc4101/nv_gw_stable Up 7h, ms_gw/logs_db Up 2d ✓
- cc2 30min SR: 0 rows (无流量, 链路健康无故障) ✓
- stream_total_deadline (6h): 0 ✓
- 30min 全 caller: hermes 6×429 (dsv4p_nv 限流), openclaw 1×200 (dsv4p_nv 成功), cc2 0 req
- 配置: NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓

## 结论
glm5_2_nv (cc2 链路) 连续 post100-post157 (58 轮) 无 dsv4p 故障扩散.
dsv4p_nv 429 是 NVCF 侧 dsv4p 限流 (周期性 5min 一发), 非 cc2 链路问题 (cc2 走 glm5_2_nv).
openclaw 同期 dsv4p_nv 1×200 佐证: 429 是配额限流非链路级故障.
ms_gw fallback 正常工作 (hermes dsv4p 全挂时 fallback ms, f=6).
0 改动, 0 重启.
