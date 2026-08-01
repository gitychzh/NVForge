# R-nvonly-post43 — hm2_cc2 NOP 巡检轮

**日期**: 2026-08-02 03:50 CST
**轮次**: R-nvonly-post43 (NOP 巡检, 0 改动, 0 重启)

## 轮前链路分析 (注入数据)
- 容器: nv_gw Up 2h, cc4101 Up 2h, nv_gw_stable Up 2h, ms_gw/logs_db Up 2d
- 30min cc2(cc4101-primary): **0 req** (session 轮前无流量)
- 30min 错误分类: all_tiers_exhausted ×6 (hermes caller 打 dsv4p_nv, 非 cc2 链路)
- 30min dsv4p_nv SR=0% (0/6) — NVCF 侧 dsv4p 限流, 与 cc2 无关 (cc2 走 glm5_2_nv)
- 30min tier_attempts: 0 rows (0 transport 错误)
- 30min buffer/wait 日志: 无

## 判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 0 req (无流量) | — (无数据, 链路健康无故障) |
| 新错误类型 | 无 (0 tier error) | ✅ |
| transport 层 | 0 错误 | ✅ |
| buffer 触发 | 无 (cc2 0 req) | ✅ |
→ **NOP 巡检轮**, 不改码, 不重启.

## 健康验证
- nv_gw `/health`: status=ok, nv_num_keys=5, nv_default_model=glm5_2_nv, pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv] ✓
- docker ps: 全 Up ✓
- 配置 (注入实测): NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓

## 结论
cc2 链路健康无故障. 0 改动, 0 重启. post17-post27 连续满分 11 连庄保持 (post28-post43 均 0 req 不计入连庄也不打断).
dsv4p_nv (hermes) 6×429 是 NVCF 侧限流, 非 cc2 链路 (cc2 走 glm5_2_nv).

## 下一步
- 继续 NOP 巡检. 等 cc2 产生流量后再判 SR.
- 关注 dsv4p_nv (hermes) 限流是否缓解.
