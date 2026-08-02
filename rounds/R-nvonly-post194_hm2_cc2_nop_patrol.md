# R-nvonly-post194 — hm2 cc2 NOP patrol

- 日期: 2026-08-02 11:22 CST
- 轮次: R-nvonly-post194 (NOP 巡检轮)
- 主仓 HEAD: d65a52f (post193 已 push)
- 改动: 0  | 重启: 0  | 回滚: 0

## 判稳依据

### cc2 (cc4101-primary) 30min 窗口
- 0 req (session 轮前无 cc2 流量产生, 无数据可判 SR)
- tier error: 0 rows
- buffer/wait 日志: 空
- 链路健康无故障

### 全 caller 30min (非 cc2)
| caller | status | count |
|--------|--------|-------|
| hermes | 429 | 6 |
| openclaw | 200 | 1 |

hermes 6×429 = dsv4p_nv 配额限流 (NVCF 侧, all_tiers_exhausted), 与 cc2 无关 (cc2 走 glm5_2_nv).
openclaw 1×200 正常.

### tier 错误 (cc2): 0

## 健康验证
- nv_gw /health: ok, passthrough, 5 keys, default glm5_2_nv ✓
- docker ps: nv_gw/cc4101/nv_gw_stable Up 9h, ms_gw/logs_db Up 3d ✓
- 配置: NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓

## 参数快照 (无变化, 同 post193)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, BUFFER_TIMEOUT_STAIRS=90×5, BUFFER_TOTAL_DEADLINE=450s, UPSTREAM_TIMEOUT=90s, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, MIN_OUTBOUND_INTERVAL_S=10, TIER_COOLDOWN_S=180, TIER_TIMEOUT_BUDGET=180s, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, NVU_FORCE_STREAM_UPGRADE=0, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150, CC4101_PRIMARY_SKIP_S=30, CC4101_PRIMARY_FAIL_THRESHOLD=3, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, PRIMARY_UPSTREAM_MODEL=glm5_2_nv, FALLBACK_UPSTREAM_MODEL=glm5_2_ms

## 下一步
继续 NOP 巡检. 等 cc2 流量产生后再判 SR. 若 dsv4p_nv 配额限流扩散到 glm5_2_nv 再介入.
