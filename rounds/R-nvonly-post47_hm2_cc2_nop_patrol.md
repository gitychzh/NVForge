# R-nvonly-post47 — hm2_cc2 NOP 巡检轮 (2026-08-02 03:50 CST)

## 数据 (30min 窗口, 轮前链路分析注入)
- cc2 (cc4101-primary): 0 req (session 轮前无流量). 无数据判 SR, 链路健康无故障.
- hermes caller → dsv4p_nv: 6×429, all_tiers_exhausted (NVCF 侧 dsv4p 限流, 非 cc2 链路).
  按分钟趋势 19:20~19:45 每分钟 1×429, 稳定限流.
- cc2 tier error: 0 rows. buffer/wait/error 日志: 30min 无 cc2 相关.

## 健康验证
- nv_gw /health: status=ok, nv_num_keys=5, nv_default_model=glm5_2_nv ✓
- docker ps: cc4101/nv_gw/nv_gw_stable Up 2h, ms_gw/logs_db Up ✓
- 配置实测: NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓

## 三阈值判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 SR | 0 req (无流量) | — (无数据, 链路健康无故障) |
| 新错误类型 | 无 (0 cc2 tier error) | ✅ |
| transport 层 | 0 错误 | ✅ |
| buffer 触发 | 无 | ✅ |
→ **NOP 巡检轮**, 0 改动, 0 重启.

## 行动
- 0 改动, 0 重启. post17~post27 连续满分 11 连庄保持 (post28-post47 均 0 req 不计入连庄也不打断).

## 下一步
- 继续 NOP 巡检. 等 cc2 产生流量后再判 SR.
- 关注 dsv4p_nv (hermes) 限流是否缓解 (NVCF 侧问题, 非 cc2).
- 若 cc2 出现新错误或 SR<99%, 再找根因小步改.
