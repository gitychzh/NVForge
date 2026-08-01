# R-nvonly-post54 — hm2_cc2 NOP 巡检轮 (2026-08-02 04:12 CST)

## 结论
NOP 巡检轮. cc2 30min 0 req (session 轮前无流量产生, 无数据可判 SR).
链路健康无故障, 0 改动, 0 重启.

## 依据 (轮前注入数据 + 实测)
- cc2 (cc4101-primary) 30min: 0 req (无流量, 非链路故障)
- 其他 caller: hermes|dsv4p_nv|429 ×6 (NVCF 侧 dsv4p 限流, 与 cc2 无关, cc2 走 glm5_2_nv)
- tier 30min: 0 rows (当前窗口无 cc2 tier error)
- top error: all_tiers_exhausted ×6 (全来自 hermes→dsv4p_nv, 非 cc2)
- /health: ok, glm5_2_nv, 5 keys, pexec=[kimi_nv,dsv4p_nv,glm5_2_nv] ✓
- docker ps: cc4101/nv_gw/nv_gw_stable/ms_gw/logs_db 全 Up (2h/2d) ✓
- 配置: NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓

## 三阈值判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 SR | 0 req (无流量) | — (链路健康无故障) |
| 新错误类型 | 无 (0 cc2 tier error) | ✅ |
| transport 层 | 0 错误 (无 cc2 流量) | ✅ |
| buffer 触发 | 无 (cc2 0 req) | ✅ |
→ NOP 巡检轮, 不改码, 不重启.

## 改动
0 改动, 0 重启 (NOP).

## 下一步
- 继续 NOP 巡检. 等 cc2 产生流量后再判 SR.
- 关注 dsv4p_nv (hermes) 限流是否缓解 (NVCF 侧问题, 非 cc2).
- 若 cc2 出现新错误或 SR<99% (排除 fallback 兜底), 再找根因小步改.
