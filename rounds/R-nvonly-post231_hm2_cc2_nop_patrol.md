# R-nvonly-post231 — hm2_cc2 NOP 巡检轮 (2026-08-02 12:51 CST)

## 判稳结论
NOP 巡检轮. cc2 (cc4101-primary) 30min 0 req, 链路健康无故障. 0 改动, 0 重启.

## 本轮数据

### 1. cc4101-primary (cc2) 30min — 0 req
无 cc2 流量产生, 无数据可判 SR. 链路健康无故障.

### 2. 其他 caller (hermes, 非 cc2 链路)
| caller | model | 200 | 429 | SR |
|--------|--------|-----|-----|-----|
| hermes | dsv4p_nv | 7 | 4 | 63.6% (11req) |

hermes→dsv4p_nv SR=63.6% (11req): 7×200 + 4×429, all_tiers_exhausted ×4 (avg_dur 2157ms, NVCF 配额限流).
per-key: key2 扛 7×200 (avg_dur 9306ms), 4×429 来自无 key 映射 (empty key).
per-egress: 203.10.96.139 扛 7×200 (100% SR), 4×429 来自无 egress (空 IP).
finish_reason: tool_calls×5, stop×2 (无 zombie).
按分钟趋势: 04:25-04:40 间 4×429 (限流), 04:45-04:50 7×200 (恢复).
**与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).

### 3. 30min 错误分类 (全 caller)
- all_tiers_exhausted (hermes→dsv4p_nv): 4× (avg_dur 2157ms), 全为 NVCF 配额限流, 非 cc2 链路.

### 4. tier 错误 — 0 rows (nv_tier_attempts 30min 空, cc2 链路无 tier error)
### 5. buffer/wait 日志 — 空 (cc2 无 buffer/wait/keymanager 日志)

## 健康验证 (12:51 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 11h, ms_gw/logs_db Up 3 days ✓ |
| cc2 (cc4101-primary) 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| 30min tier error (全 caller) | 0 rows ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## 参数快照 (无变化, 同 post229)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, BUFFER_TIMEOUT_STAIRS=90×5, BUFFER_TOTAL_DEADLINE=450s, TIER_TIMEOUT_BUDGET=180s, TIER_COOLDOWN_S=180s, UPSTREAM_TIMEOUT=90s, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, MIN_OUTBOUND_INTERVAL_S=10, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, NVU_FORCE_STREAM_UPGRADE=0, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150, CC4101_PRIMARY_SKIP_S=30, CC4101_PRIMARY_FAIL_THRESHOLD=3, FALLBACK_UPSTREAM_URL=ms_gw:40007, PRIMARY_UPSTREAM_URL=nv_gw:40006, PRIMARY_UPSTREAM_MODEL=glm5_2_nv, FALLBACK_UPSTREAM_MODEL=glm5_2_ms

## 下一步
继续 NOP 巡检. 等 cc2 流量产生后再判 SR. 若 dsv4p_nv 配额限流持续扩散到 glm5_2_nv 再介入.
