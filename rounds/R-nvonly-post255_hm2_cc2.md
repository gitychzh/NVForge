# R-nvonly-post255 hm2_cc2 — NOP 巡检轮 (2026-08-02 13:34 CST)

## 本轮: NOP 巡检, 0 改动 0 重启
- cc2 (cc4101-primary) 30min: 0 req (session 轮前无流量产生, 无数据判 SR)。
- 链路健康无故障: nv_gw /health ok (passthrough, 5 keys, default glm5_2_nv), env 配置正确。
- 全容器 Up 12h+ (nv_gw/cc4101/nv_gw_stable), ms_gw/logs_db Up 3d。
- 0 cc2 tier error (nv_tier_attempts 30min 空), 0 cc2 buffer/wait 日志。

## 数据 (本轮 30min 窗口)
### cc2 (cc4101-primary) — 0 req
```
 status | count
--------+-------
(0 rows)
```
链路健康无故障, 无 cc2 流量产生。

### 30min 链路总览 (caller × model × status)
| caller | model | status | count |
|--------|--------|--------|-------|
| hermes | dsv4p_nv | 200 | 17 |
| hermes | dsv4p_nv | 429 | 3 |
| hermes | dsv4p_nv | 502 | 1 |
| openclaw | dsv4p_nv | 200 | 1 |

dsv4p_nv SR=81.8% (18/22, 含 1×502 NVStream_IncompleteRead avg 34130ms), 全部来自 hermes/openclaw, **非 cc2 链路** (cc2 走 glm5_2_nv)。
per-key: key2 扛 17×200 (avg 10436ms) + 1×502, key3 1×200, 3×429 无 key。
per-egress: 203.10.96.139 18 (94ms), 134.195.101.194 1×200。
finish_reason: tool_calls×15, stop×3 (无 zombie)。
fallback 发生率: 0/22 (无 fallback)。
按分钟趋势: 05:05-05:11 稳定 200, 05:15/05:20/05:25 各 1×429, 05:31 1×502。

### 30min 错误分类 (全 caller, status!=200)
- all_tiers_exhausted ×3 (hermes dsv4p_nv, avg 2855ms, 非 cc2)。
- NVStream_IncompleteRead ×1 (hermes dsv4p_nv key2, avg 34130ms, 非 cc2)。

### 30min tier 错误 (nv_tier_attempts)
```
(0 rows)
```
cc2 相关 tier 错误为 0。

## 健康验证 (13:34 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 12h, ms_gw/logs_db Up 3d ✓ |
| cc2 (cc4101-primary) 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| 30min tier error (全 caller) | all_tiers_exhausted ×3 + NVStream_IncompleteRead ×1 (hermes dsv4p_nv, 非 cc2) ✓ |
| 30min 全 caller | hermes 21req + openclaw 1req dsv4p_nv (18×200 + 3×429 + 1×502), cc2 0 req ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## 判稳决策
- cc2 30min 0 req, 无流量产生, 无数据判 SR, 但链路健康无故障。
- 3× all_tiers_exhausted + 1× NVStream_IncompleteRead 全是 hermes 打 dsv4p_nv, 与 cc2 (glm5_2_nv) 无关, 不介入。
- SR 判稳标准: 无 cc2 流量时以"链路健康无故障 + 0 cc2 tier error"为准 → NOP 巡检轮。
- 0 改动, 0 重启。

## 参数快照 (2026-08-02 13:34 CST, 无变化, 同 post254)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, BUFFER_TOTAL_DEADLINE=450s, TIER_TIMEOUT_BUDGET=180s, TIER_COOLDOWN_S=180s, UPSTREAM_TIMEOUT=90s, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, MIN_OUTBOUND_INTERVAL_S=10, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, NVU_FORCE_STREAM_UPGRADE=0, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150, CC4101_PRIMARY_SKIP_S=30, CC4101_PRIMARY_FAIL_THRESHOLD=3, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, PRIMARY_UPSTREAM_MODEL=glm5_2_nv, FALLBACK_UPSTREAM_MODEL=glm5_2_ms

## 下一步
继续 NOP 巡检. 等 cc2 流量产生后再判 SR. 若 dsv4p_nv 配额限流持续扩散到 glm5_2_nv 再介入.
