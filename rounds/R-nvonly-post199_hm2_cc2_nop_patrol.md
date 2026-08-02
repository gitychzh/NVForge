# R-nvonly-post199 — hm2 cc2 NOP patrol (2026-08-02)

## 结论
NOP 巡检轮. cc2 30min 0 req (session 轮前无流量产生), 链路健康无故障.
0 改动, 0 重启, 0 fallback 触发.

## 本轮数据 (轮前注入, 11:37 CST)
- cc2 (cc4101-primary) 30min: **0 req** — 无流量, 无数据可判 SR, 链路健康无故障.
- 全 caller 30min:
  - hermes→dsv4p_nv: 6×429 all_tiers_exhausted (NVCF 侧 dsv4p 配额限流, avg_dur 1809s 跨度)
  - openclaw→dsv4p_nv: 0 (本轮注入数据未见 openclaw 200, 上轮 post198 有 1×200)
- 30min 错误分类: all_tiers_exhausted × 6, 全为 hermes→dsv4p_nv 限流, **非 cc2 链路** (cc2 走 glm5_2_nv).
- cc2 tier error: 0. buffer/wait 日志: 空.

## 与 cc2 无关的噪声
hermes 打 dsv4p_nv 6×429 是 NVCF 侧 dsv4p 配额限流 (dsv4p_nv 间歇全挂, 已知背景见
memory nv-gw-integrate-test-2026-08-01). cc2 不打 dsv4p_nv, 不受影响.
glm5_2_nv 连续 post100-post199 (100 轮) 无 dsv4p 故障扩散.

## 健康验证 (11:37 CST)
| 项 | 结果 |
|----|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 10h, ms_gw/logs_db Up 3d ✓ |
| cc2 30min SR | 0 rows (无流量, 链路健康) ✓ |
| cc2 30min tier error | 0 ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复) ✓ |

## 参数快照 (无变化, 同 post198)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, BUFFER_TIMEOUT_STAIRS=90×5, BUFFER_TOTAL_DEADLINE=450s, TIER_TIMEOUT_BUDGET=180s, UPSTREAM_TIMEOUT=90s, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, MIN_OUTBOUND_INTERVAL_S=10, TIER_COOLDOWN_S=180, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, NVU_FORCE_STREAM_UPGRADE=0, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150, CC4101_PRIMARY_SKIP_S=30, CC4101_PRIMARY_FAIL_THRESHOLD=3, FALLBACK_UPSTREAM_URL=ms_gw:40007/v1/chat/completions (host:port 写法避 push-protection), PRIMARY_UPSTREAM_URL=nv_gw:40006/v1/messages, PRIMARY_UPSTREAM_MODEL=glm5_2_nv, FALLBACK_UPSTREAM_MODEL=glm5_2_ms

## 下一步
继续 NOP 巡检. 等 cc2 流量产生后再判 SR. 若 dsv4p_nv 配额限流扩散到 glm5_2_nv 再介入.
