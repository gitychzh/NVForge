# R-nvonly-post53: hm2_cc2 NOP 巡检轮 (cc2 30min 0req 无流量无故障, 链路健康, 0改动0restart, dsv4p_nv(hermes)限流与cc2无关)

## 时间
- 2026-08-02 04:08 CST (轮前数据窗口 04:07)

## 轮前链路分析 (注入数据)
- cc2 (cc4101-primary) 30min: **0 req** — session 轮前无流量产生, 无数据可判 SR.
- hermes caller 打 dsv4p_nv: SR=0% (0/6, 6×429/all_tiers_exhausted), 每 5min 1×429 (19:40~20:05).
  → NVCF 侧 dsv4p 持续限流, **与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).
- 配置实测: `NVU_DISABLE_MS_FALLBACK=0` (fallback 已恢复), `FALLBACK_UPSTREAM=ms_gw:40007`, `CC4101_STREAM_TOTAL_DEADLINE_S=470`, `PRIMARY_HEADER_TIMEOUT=400`.
- buffer/wait/keymanager 日志: 空 (cc2 0 req, 无触发).

## 健康验证 (04:08 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw `/health` | status=ok, nv_default_model=glm5_2_nv, nv_num_keys=5, pexec=[kimi_nv,dsv4p_nv,glm5_2_nv] ✓ |
| docker ps | cc4101/nv_gw/nv_gw_stable/ms_gw/logs_db 全 Up ✓ |
| git pull (hermes main) | Already up to date ✓ |
| nv_requests 30min (cc4101-primary) | 0 rows (cc2 无流量) ✓ |
| nv_tier_attempts 30min | 0 rows (早窗口 6×dsv4p 429 已过期, 当前 0) ✓ |

## 三阈值判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 0 req (无流量) | — (无数据, 链路健康无故障) |
| 新错误类型 | 无 (0 cc2 tier error) | ✅ |
| transport 层 | 0 错误 (无 cc2 流量) | ✅ |
| buffer 触发 | 无 (cc2 0 req) | ✅ |
→ **NOP 巡检轮**, 不改码, 不重启.

## 本轮改动
- 0 改动, 0 重启, 0 commit (hermes 仓). 纯巡检.

## 下一步
- 继续 NOP 巡检. 等 cc2 产生流量后再判 SR (本轮 0 req 是 session 轮前无流量, 非链路故障).
- 关注 dsv4p_nv (hermes) 限流是否缓解 (NVCF 侧问题, 非 cc2).
- 若 cc2 出现新错误或 SR<99% (排除 fallback 兜底), 再找根因小步改.
