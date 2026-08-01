# R-nvonly-post90 — hm2 cc2 NOP patrol

**时间**: 2026-08-02 05:55 CST
**轮次**: post90 (NOP 巡检轮)
**git HEAD (上轮)**: a56ecfe (post89)

## 判稳结论
NOP 巡检轮. cc2 30min 0 req (session 轮前无流量). 链路健康无故障.
0 改动, 0 重启, 0 fallback 触发 (cc2 侧).

## 数据 (30min 窗口, 已注入)

### cc4101-primary (cc2 链路) — 0 req
无请求产生. 0 tier error, 0 buffer/wait/error 日志. 无数据可判 cc2 SR.

### 其他 caller (非 cc2 链路)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 200 | 3 |
| hermes | dsv4p_nv | 429 | 5 |

dsv4p_nv SR=37.5% (3/8): 5×429 (all_tiers_exhausted, 5key 全挂).
周期性 5min 一发 429 (21:25/30/35/45/50 各 1×429, 21:40 突破为 3×200).
**与 cc2 无关** — cc2 走 glm5_2_nv, 不打 dsv4p_nv. NVCF 侧 dsv4p 限流, 不在本轮优化范围.
30min fallback f=8 (dsv4p 全挂 fallback ms, ms_gw fallback 已恢复正常工作).

## 健康验证 (05:55 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw `/health` | status=ok, nv_default_model=glm5_2_nv, nv_num_keys=5, pexec=[kimi_nv,dsv4p_nv,glm5_2_nv] ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 4h, ms_gw/logs_db Up 2d ✓ |
| cc2 tier error (30min) | 0 ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |
| git pull | Already up to date ✓ |

## 三阈值判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 0 req (无流量) | — (无数据, 链路健康无故障) |
| 新错误类型 | 无 (0 cc2 tier error) | ✅ |
| transport 层 | 0 错误 (无 cc2 流量) | ✅ |
| buffer 触发 | 无 (cc2 0 req) | ✅ |
→ **NOP 巡检轮**, 不改码, 不重启.

## cc2 SR 走势
| 轮次 | cc2 SR | 错误 | 趋势 |
|------|--------|------|------|
| post17 | 1/1=100% | 0 | ✅ glm5_2_nv 健康, 满分 |
| post18-post89 | 0 req | 0 | — (无流量, 链路健康) |
| post90 | 0 req | 0 | — (无流量, 链路健康) |

## 下一步
- 继续 NOP 巡检. 等 cc2 有流量时再判 SR.
- dsv4p_nv 低 SR (37.5%) 是 NVCF 侧 dsv4p 限流 (周期性 429 + 5key 全挂), 非 cc2 链路, 不在 cc2 优化范围.

## 参数快照 (2026-08-02 05:53 CST 实测注入)
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
| nv_gw.NVU_CALLER_KEY_MAP | hermes:2;openclaw:3;opencode:4 |
| nv_gw.NVU_FORCE_STREAM_UPGRADE | 0 |
| cc4101.CC4101_STREAM_TOTAL_DEADLINE_S | 470 |
| cc4101.PRIMARY_HEADER_TIMEOUT | 400 |
| cc4101.UPSTREAM_TIMEOUT | 130 |
| cc4101.UPSTREAM_IDLE_TIMEOUT | 150 |
| cc4101.CC4101_PRIMARY_FAIL_THRESHOLD | 3 |
| cc4101.CC4101_PRIMARY_SKIP_S | 30 |
| cc4101.PRIMARY_UPSTREAM_MODEL | glm5_2_nv |
| cc4101.FALLBACK_UPSTREAM_MODEL | glm5_2_ms |
| cc4101.FALLBACK_UPSTREAM_URL | http://ms_gw:40007/v1/chat/completions |
| cc4101.PRIMARY_UPSTREAM_URL | http://nv_gw:40006/v1/messages |
