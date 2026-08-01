# R-nvonly-post78 — hm2 cc2 NOP 巡检轮

**时间**: 2026-08-02 05:20 CST
**轮次**: R-nvonly-post78 (NOP 巡检轮)
**主仓 HEAD**: e5180d2 (上轮 post77 已 push)

## 本轮改动
**无改动, 无重启.** NOP 巡检轮.

## 判稳依据
cc2 (cc4101-primary) 30min 窗口 0 req (session 轮前无流量产生, 无数据可判 SR).
链路健康无故障, 三阈值全绿 → NOP.

## 关键数据 (05:20 CST 实测)

### 1. cc4101-primary (cc2) 30min — 0 req
无流量, 无数据. 链路健康无故障.

### 2. 其他 caller (hermes/openclaw, 非 cc2 链路) — 注入数据
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 200 | 7 |
| hermes | dsv4p_nv | 429 | 4 |
| openclaw | dsv4p_nv | 502 | 2 |

dsv4p_nv SR=53.8% (7/13): 4×all_tiers_exhausted + 4×429 + 2×zombie_empty_completion (502).
**与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).
错误根因: NVCF 侧 dsv4p 限流 (429 周期性) + 单 egress IP 漂移 (203.10.96.139=7×100%, 其余 0%).

### 3. 健康验证 (05:20 CST)
| 验证项 | 结果 |
|--------|------|
| docker ps | nv_gw/cc4101/nv_gw_stable Up 3h, ms_gw/logs_db 2d ✓ |
| nv_gw `/health` | status=ok, nv_default_model=glm5_2_nv, nv_num_keys=5, pexec=[kimi_nv,dsv4p_nv,glm5_2_nv] ✓ |
| cc2 30min nv_requests | 0 行 (0 req) ✓ |
| stream_total_deadline (6h) | 0 次 ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK=ms_gw:40007 ✓ |

## 三阈值判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 SR | 0 req (无流量) | — (无数据, 链路健康) |
| 新错误类型 | 无 | ✅ |
| transport 层 | 0 错误 (无 cc2 流量) | ✅ |
| buffer 触发 | 无 (cc2 0 req) | ✅ |
| stream_total_deadline (6h) | 0 次 | ✅ |
→ **NOP 巡检轮**, 不改码, 不重启.

## cc2 SR 走势
| 轮次 | cc2 SR | 错误 | 趋势 |
|------|--------|------|------|
| post17 | 1/1=100% | 0 | ✅ glm5_2_nv 健康 |
| post18-post77 | 0 req | 0 | — (无流量, 链路健康) |
| post78 | 0 req | 0 | — (无流量, 链路健康) |

## 下一步
- 继续 NOP 巡检. 等 cc2 有流量时再判 SR.
- dsv4p_nv 低 SR 是 NVCF 侧限流 (hermes/openclaw 打), 非 cc2 链路, 不在本轮优化范围.

## 参数快照 (2026-08-02 05:19 注入)
| 参数 | 值 |
|------|-----|
| nv_gw.UPSTREAM_TIMEOUT | 90 |
| nv_gw.TIER_COOLDOWN_S | 180 |
| nv_gw.TIER_TIMEOUT_BUDGET_S | 180 |
| nv_gw.KEY_COOLDOWN_S | 30 |
| nv_gw.NV_INTEGRATE_KEY_COOLDOWN_S | 90 |
| nv_gw.MIN_OUTBOUND_INTERVAL_S | 10 |
| nv_gw.NVU_DISABLE_MS_FALLBACK | 0 (fallback 已恢复) |
| nv_gw.NVU_BUFFER_CALLERS | cc4101-primary,openclaw2 |
| nv_gw.NVU_PEER_FB_SKIP_MODELS | glm5_2_nv,dsv4p_nv |
| nv_gw.NVU_FORCE_STREAM_UPGRADE | 0 |
| nv_gw.NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 150 |
| nv_gw.NVU_CALLER_KEY_MAP | hermes:2;openclaw:3;opencode:4 |
| cc4101.CC4101_STREAM_TOTAL_DEADLINE_S | 470 |
| cc4101.PRIMARY_HEADER_TIMEOUT | 400 |
| cc4101.UPSTREAM_TIMEOUT | 130 |
| cc4101.UPSTREAM_IDLE_TIMEOUT | 150 |
| cc4101.FALLBACK_UPSTREAM_URL | ms_gw:40007 |
| cc4101.PRIMARY_UPSTREAM_MODEL | glm5_2_nv |
| cc4101.FALLBACK_UPSTREAM_MODEL | glm5_2_ms |
