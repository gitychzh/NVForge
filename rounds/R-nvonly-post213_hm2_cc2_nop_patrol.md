# R-nvonly-post213 — hm2_cc2 NOP 巡检轮 (2026-08-02 12:20 CST)

## 轮前链路分析 (注入数据)
- 上轮: R-nvonly-post212 | 容器: nv_gw/cc4101 Up 10h, ms_gw/logs_db Up 3d
- nv_gw /health: ok, passthrough, 5 keys, default glm5_2_nv
- 配置: NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007

## 本轮数据 (30min 窗口)

### cc2 (cc4101-primary) — 0 req
本轮 30min cc2 无请求产生. 无数据可判 cc2 SR. 链路健康无故障, 0 tier error, 0 buffer/wait 日志.

### 其他 caller (hermes, 非 cc2 链路)
| caller | model | 200 | 429 | 502 | SR |
|--------|--------|-----|-----|-----|-----|
| hermes | dsv4p_nv | 32 | 1 | 1 | 94.1% (34req) |

hermes→dsv4p_nv SR=94.1% (34req): 32×200 + 1×429 + 1×502, all_tiers_exhausted × 2 (NVCF 配额限流, 5key 全 cooling).
**与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).
glm5_2_nv 连续 post100-post213 (113 轮) 无 dsv4p 故障扩散.

### 30min 错误分类 (全 caller)
- all_tiers_exhausted (hermes→dsv4p_nv): 2× (avg_dur 30323ms), 全为 NVCF 配额限流, 非 cc2 链路.

### 30min per-key × status (dsv4p)
- key 2: 32×200 (avg_dur 10301ms)
- 429 ×1 (avg_dur 7305ms), 502 ×1 (avg_dur 53341ms)

### 30min per-egress-IP (dsv4p)
- 203.10.96.139: 32×200 (100%)
- (无 IP): 2× (0% — 429+502)

### 30min dsv4p 200 延迟/Token
- avg_dur 10301ms, max 29576ms, min 3467ms, avg_ttfb 10027ms

### 30min dsv4p 200 finish_reason 分布
- tool_calls ×29, stop ×3 (无 zombie, 健康正常)

### 30min fallback 发生率
- f ×34 (全部无 fallback, 链路自恢复正常)

### 30min buffer/wait/keymanager 日志
- 空 (cc2 无请求, 无 buffer/wait 触发)

## 判稳结论
SR (cc2) = N/A (0 req, 无流量), 链路健康无故障 → **NOP 巡检轮**.
- 0 改动, 0 重启.
- dsv4p_nv 配额限流仅影响 hermes, 未扩散到 glm5_2_nv (cc2 链路).

## 健康验证 (12:20 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 10h, ms_gw/logs_db Up 3d ✓ |
| cc2 (cc4101-primary) 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| 30min tier error (cc2) | 0 ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## 参数快照 (无变化, 同 post212)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, BUFFER_TIMEOUT_STAIRS=90×5, BUFFER_TOTAL_DEADLINE=450s, TIER_TIMEOUT_BUDGET=180s, UPSTREAM_TIMEOUT=90s, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, MIN_OUTBOUND_INTERVAL_S=10, TIER_COOLDOWN_S=180, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, NVU_FORCE_STREAM_UPGRADE=0, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150, CC4101_PRIMARY_SKIP_S=30, CC4101_PRIMARY_FAIL_THRESHOLD=3, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, PRIMARY_UPSTREAM_MODEL=glm5_2_nv, FALLBACK_UPSTREAM_MODEL=glm5_2_ms

## 下一步
继续 NOP 巡检. 等 cc2 流量产生后再判 SR. 若 dsv4p_nv 配额限流持续扩散到 glm5_2_nv 再介入.
