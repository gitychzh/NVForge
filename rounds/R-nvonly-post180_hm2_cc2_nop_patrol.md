# R-nvonly-post180 — cc2 NOP 巡检轮 (2026-08-02 10:28 CST)

## 结论: NOP (0 改动, 0 重启)
cc2 (cc4101-primary) 30min 窗口 0 req, 无流量产生, 链路健康无故障, 无数据可判 SR.
仅 hermes→dsv4p_nv 4×429 (NVCF 侧配额限流, 与 cc2 走 glm5_2_nv 无关, 未扩散).

## 依据 (轮前链路分析)
- cc2 (cc4101-primary) 30min: **0 req** — 无流量无数据.
- 全 caller 30min: hermes|dsv4p_nv 11req (7×200, 4×429 all_tiers_exhausted).
- dsv4p_nv SR=63.6% (11req) — 全部 hermes 流量, 非 cc2 链路.
- 30min 错误: all_tiers_exhausted ×4 (hermes→dsv4p NVCF 配额限流).
- tier 错误 (cc2): 0 rows.
- buffer/wait 日志: 空.
- glm5_2_nv (cc2 模型) 连续 post100-post180 (81 轮) 无 dsv4p 故障扩散.

## 健康验证 (10:28 CST)
| 项 | 结果 |
|----|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 8h, ms_gw/logs_db Up 3d ✓ |
| cc2 30min SR | 0 rows (无流量, 链路健康) ✓ |
| 30min tier error | 0 ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复) ✓ |

## 参数快照 (无变化, 同 post179)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, BUFFER_TIMEOUT_STAIRS=90×5, BUFFER_TOTAL_DEADLINE=450s, TIER_TIMEOUT_BUDGET=180s, UPSTREAM_TIMEOUT=90s, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, MIN_OUTBOUND_INTERVAL_S=10, TIER_COOLDOWN_S=180, NVU_FORCE_STREAM_UPGRADE=0, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150, CC4101_PRIMARY_SKIP_S=30, CC4101_PRIMARY_FAIL_THRESHOLD=3, FALLBACK_UPSTREAM_URL=ms_gw:40007, PRIMARY_UPSTREAM_URL=nv_gw:40006, PRIMARY_UPSTREAM_MODEL=glm5_2_nv, FALLBACK_UPSTREAM_MODEL=glm5_2_ms

## 下一步
继续 NOP 巡检. 等 cc2 流量产生后再判 SR. 若 dsv4p_nv 配额限流持续扩散到 glm5_2_nv 再介入.
