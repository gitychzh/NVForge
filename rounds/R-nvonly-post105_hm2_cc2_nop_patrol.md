# R-nvonly-post105 (hm2_cc2) — NOP 巡检轮

**时间**: 2026-08-02 06:37 CST
**主仓 HEAD**: 791bb68 (post104 已 push)
**本轮改动**: 0 (NOP)
**重启**: 0

## 判稳依据
cc2 (cc4101-primary) 30min 窗口 0 req (session 轮前无流量产生), 无数据可判 SR,
但链路健康无故障: 容器全 Up, env 配置正确, 0 cc2 tier error, 0 buffer/wait 日志.

唯一异常: hermes 打 dsv4p_nv 6×429 (all_tiers_exhausted, 5key 全挂, 周期性 5min 一发).
**与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv). dsv4p_nv 低 SR 是 NVCF 侧 dsv4p 限流,
不在本轮优化范围. post100-post105 连续 6 轮未扩散到 glm5_2_nv.

## 30min 关键数据
- cc2 (cc4101-primary) 30min: 0 req (无流量, 链路健康)
- hermes+dsv4p_nv: 6×429 (all_tiers_exhausted, 周期性 5min 一发, NVCF 侧限流)
- 30min fallback: f=6 (dsv4p 全挂 fallback ms, ms_gw fallback 已恢复)
- 0 cc2 tier error, 0 cc2 buffer/wait 日志

## 健康验证 (06:37 CST)
- nv_gw /health: ok, passthrough, 5 keys, default glm5_2_nv ✓
- docker ps: nv_gw/cc4101 Up 5h, nv_gw_stable Up 5h, ms_gw/logs_db Up 2d ✓
- env: NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), BUFFER 5×90s=450s, cc4101 deadline 470s ✓

## 三阈值判稳
| 阈值 | 实测 | 判定 |
|------|------|------|
| cc2 SR | 0 req (无流量) | — (无数据, 链路健康) |
| 新错误类型 | 0 cc2 tier error | ✅ |
| transport 层 | 0 (无 cc2 流量) | ✅ |
→ NOP, 不改码不重启.

## 下一步
- 继续 NOP 巡检, 等 cc2 有流量时再判 SR.
- 关注 dsv4p_nv 周期性 429 是否扩散到 glm5_2_nv (post100-post105 连续 6 轮未扩散).
