# R-nvonly-post76 hm2_cc2 — NOP 巡检轮

**日期**: 2026-08-02 05:14 CST
**方向**: R-nvonly (HM2 nv_gw 40006, ms_gw fallback 已恢复保留)
**轮次**: post76 (post75 后连续 NOP)

## 本轮改动
**0 改动, 0 重启** — NOP 巡检轮.

## 依据 (30min 链路数据注入)
- cc2 (cc4101-primary) 30min: **0 req** (session 轮前无流量产生, 无数据可判 SR).
- 链路健康无故障:
  - 容器全 Up (nv_gw/cc4101/nv_gw_stable 3h, logs_db 2d)
  - /health ok (glm5_2_nv, 5 keys, pexec=[kimi_nv,dsv4p_nv,glm5_2_nv])
  - 0 cc2 tier error, 0 cc2 buffer/wait/error 日志
  - 0 stream_total_deadline (6h)
- 其他 caller (hermes/openclaw) 打 dsv4p_nv SR=53.8% (7/13):
  - 4×all_tiers_exhausted + 4×429 + 2×zombie_empty_completion(502)
  - **与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv)
  - 是 NVCF 侧 dsv4p 限流 + egress IP 漂移, 非 nv_gw 链路问题

## 三阈值判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 0 req | — (无流量, 链路健康) |
| 新错误类型 | 无 | ✅ |
| transport 层 | 0 错误 | ✅ |
| buffer 触发 | 无 | ✅ |
| stream_total_deadline (6h) | 0 次 | ✅ |
→ **NOP**, 不改码, 不重启.

## 验证 (05:14 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | status=ok, nv_num_keys=5, glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 3h ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复) ✓ |

## 下一步
- 继续观察 cc2 (cc4101-primary) 流量恢复后的 SR 走势.
- dsv4p_nv 低 SR 是 NVCF 侧限流, 非 cc2 链路, 不在本轮处理范围.
- 若 cc2 流量恢复且 SR<99% 或出现新错误, 再找根因小步改.

## 参数快照 (实测注入, 与 post75 一致, 0 变更)
| 参数 | 值 |
|------|-----|
| nv_gw.UPSTREAM_TIMEOUT | 90 |
| nv_gw.TIER_COOLDOWN_S | 180 |
| nv_gw.KEY_COOLDOWN_S | 30 |
| nv_gw.NV_INTEGRATE_KEY_COOLDOWN_S | 90 |
| nv_gw.NVU_DISABLE_MS_FALLBACK | 0 |
| nv_gw.NVU_BUFFER_CALLERS | cc4101-primary,openclaw2 |
| nv_gw.NVU_PEER_FB_SKIP_MODELS | glm5_2_nv,dsv4p_nv |
| nv_gw.NVU_FORCE_STREAM_UPGRADE | 0 |
| cc4101.CC4101_STREAM_TOTAL_DEADLINE_S | 470 |
| cc4101.PRIMARY_HEADER_TIMEOUT | 400 |
| cc4101.FALLBACK_UPSTREAM_URL | ms_gw:40007 |
