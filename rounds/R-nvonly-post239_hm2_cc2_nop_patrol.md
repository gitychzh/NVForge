# R-nvonly-post239 hm2_cc2 NOP 巡检轮 (2026-08-02 13:00 CST)

## 本轮改了什么
0 改动, 0 重启. NOP 巡检轮.

## 依据 (轮前链路分析 12:59:32 CST)
- cc2 (cc4101-primary) 30min: **0 req** — session 轮前无流量产生, 无数据可判 SR.
  链路健康无故障, 0 tier error, 0 buffer/wait 日志.
- hermes→dsv4p_nv 30min: 12req, 9×200/3×429, SR=75%.
  - all_tiers_exhausted×3 (avg_dur 1712ms) — NVCF 配额限流, 非 cc2 链路.
  - per-key: key2 扛 9×200 (单 key 健康, avg_dur 9480ms), 3×429 来自空 key 映射.
  - per-egress: 203.10.96.139 扛 9×200 (100% SR), 3×429 来自空 IP.
  - finish_reason: tool_calls×6, stop×3 (无 zombie).
  - 按分钟趋势: 04:30-04:40 间 3×429 (限流), 04:45-04:55 9×200 (恢复).
  - **与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).
- glm5_2_nv 连续 post100-post237 (134 轮) 无 dsv4p 故障扩散到 cc2 链路.
- 配置: NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007.
- 30min nv_tier_attempts: 0 rows (无 tier 错误记录).

## 验证 (13:00 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101 Up 11h, ms_gw/logs_db Up 3d, nv_gw_stable Up 11h ✓ |
| cc2 (cc4101-primary) 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| 30min tier error (全 caller) | 0 rows ✓ |
| 30min 全 caller | hermes 12req dsv4p_nv (9×200/3×429 限流), cc2 0 req ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## 参数快照 (无变化, 同 post235/post237)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, BUFFER_TOTAL_DEADLINE=450s, TIER_TIMEOUT_BUDGET=180s, TIER_COOLDOWN_S=180s, UPSTREAM_TIMEOUT=90s, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, MIN_OUTBOUND_INTERVAL_S=10, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, NVU_FORCE_STREAM_UPGRADE=0, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150, CC4101_PRIMARY_SKIP_S=30, CC4101_PRIMARY_FAIL_THRESHOLD=3, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, PRIMARY_UPSTREAM_MODEL=glm5_2_nv, FALLBACK_UPSTREAM_MODEL=glm5_2_ms

## 下一步
继续 NOP 巡检. 等 cc2 流量产生后再判 SR. 若 dsv4p_nv 配额限流持续扩散到 glm5_2_nv 再介入.
