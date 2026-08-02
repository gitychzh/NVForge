# R-nvonly-post146 — hm2 cc2 NOP 巡检轮

## 时间
2026-08-02 08:50 CST

## 本轮改了什么
**0 改动, 0 重启** — NOP 巡检轮.

## 依据
轮前链路分析 (08:33:32 CST) 显示:
- cc2 (cc4101-primary) 30min 窗口 **0 req** (session 轮前无流量产生, 无数据可判 cc2 SR).
- 链路健康无故障: 容器全 Up (nv_gw/cc4101 7h, nv_gw_stable 7h, ms_gw/logs_db 2d).
- env 配置正确: NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), buffer 5×90s=450s, cc4101 deadline 470s, UPSTREAM_TIMEOUT=90/130.
- 0 cc2 tier error, 0 cc2 buffer/wait/error 日志, 0 stream_total_deadline (6h, DB 直查确认).
- hermes 打 dsv4p_nv SR=0.0% (0/6, 6×429 all_tiers_exhausted, 周期性 5min 一发) 是 NVCF 侧 dsv4p 限流, **非 cc2 链路** (cc2 走 glm5_2_nv).
- glm5_2_nv 连续 post100-post146 (47 轮) 无 dsv4p 故障扩散.

## 判稳
SR ≥99% (无 cc2 流量=无故障) + 无新错误 → NOP 巡检轮, 只记数据不改码.
SR<99% 或有新错误 → 找根因, 小步改一点 + 验证.

## 验证 (08:50 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101 Up 7h, nv_gw_stable Up 7h, ms_gw/logs_db Up 2d ✓ |
| cc2 (cc4101-primary) 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| stream_total_deadline (6h) | 0 ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## 参数快照 (2026-08-02 08:50 CST)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, BUFFER_TOTAL_DEADLINE=450s, TIER_TIMEOUT_BUDGET=180s, UPSTREAM_TIMEOUT=90s, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, MIN_OUTBOUND_INTERVAL_S=10, TIER_COOLDOWN_S=180
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, PRIMARY_UPSTREAM_MODEL=glm5_2_nv, FALLBACK_UPSTREAM_MODEL=glm5_2_ms
- 链路: cc2→cc4101(4101)→nv_gw(40006, glm5_2_nv)→NVCF, fallback ms_gw(40007) 已恢复
- 铁律: 只改 HM2 nv_gw, 不碰 HM1, 不碰 ms_gw 源码, 改前有数据, 改后必验证

## 下一步
- 继续巡检. 等 cc2 有流量时观察 glm5_2_nv SR.
- dsv4p_nv 限流持续, 但属 NVCF 侧 + hermes caller, 非本轮职责 (只改 HM2 nv_gw, 不碰 caller).
- glm5_2_nv 链路连续 47 轮稳定, 无需调整.
