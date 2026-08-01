# R-nvonly-post81 — hm2 cc2 NOP 巡检轮 (2026-08-02 05:35 CST)

## 轮前链路分析 (注入数据)
- 上轮: R-nvonly-post80 | 容器 nv_gw/cc4101/nv_gw_stable Up 3h, ms_gw/logs_db Up 2d
- nv_gw /health: status=ok, nv_default_model=glm5_2_nv, nv_num_keys=5, pexec=[kimi_nv,dsv4p_nv,glm5_2_nv]

## 本轮数据 (30min 窗口, 05:26 CST 拉取)

### 1. cc2 (cc4101-primary) 30min — 0 req
| status | count |
|--------|-------|
| (无) | 0 |

cc2 session 轮前无流量产生. 无数据可判 SR.
- 6h `stream_total_deadline`: 0 次 ✅
- 6h cc2 req 趋势: 仅 17:00(1) + 18:00(2) UTC = 3 req, 近 30min 0 req.
- buffer/wait/error 日志: 0 行 ✅

### 2. 其他 caller (hermes/openclaw, 非 cc2 链路)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 200 | 4 |
| hermes | dsv4p_nv | 429 | 5 |
| openclaw | dsv4p_nv | 502 | 2 |

dsv4p_nv SR=36.4% (4/11): 5×all_tiers_exhausted (5key 全挂) + 5×429 (NVCF 侧 dsv4p 限流) + 2×zombie_empty_completion (502, avg_dur 5281ms).
**与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).
per-key: key2=4×200, key3=2×502, key?=5×429 (单 key NVCF 限流).
per-IP: 203.10.96.139=4×100%, 其余 IP=0%.
200 延迟 avg_dur=14394ms, finish_reason: tool_calls×3, stop×1.
30min fallback 发生率: f=11 (dsv4p 全挂 fallback ms).
按分钟: 21:00/21:10/21:15/21:20/21:25 周期性 429, 21:05-21:06 恢复 4×200.

### 3. tier 错误 (dsv4p_nv, 非 cc2)
| error_type | count | avg_dur |
|------------|-------|---------|
| all_tiers_exhausted | 5 | 1065s |
| zombie_empty_completion | 2 | 5281s |

## 三阈值判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 0 req (无流量) | — (无数据, 链路健康无故障) |
| 新错误类型 (cc2) | 无 | ✅ |
| transport 层 (cc2) | 0 错误 (无 cc2 流量) | ✅ |
| buffer 触发 (cc2) | 无 (cc2 0 req) | ✅ |
| stream_total_deadline (6h) | 0 次 | ✅ |
→ **NOP 巡检轮**, 不改码, 不重启, 0 改动.

## 本轮改动
无. 0 改动, 0 重启.

## 验证
- nv_gw /health: ok, glm5_2_nv, 5 keys ✅
- docker ps: nv_gw/cc4101/nv_gw_stable Up 3h, ms_gw/logs_db Up 2d ✅
- 0 cc2 tier error, 0 buffer/wait 日志, 0 stream_total_deadline (6h) ✅

## 下一步
- 继续 NOP 巡检. 等 cc2 有流量时再判 SR.
- dsv4p_nv 低 SR (36.4%) 是 NVCF 侧 dsv4p 限流 (周期性 429 + 5key 全挂), 非 cc2 链路 (cc2 走 glm5_2_nv), 不在本轮优化范围.
- ms_gw fallback 已恢复 (NVU_DISABLE_MS_FALLBACK=0, FALLBACK_UPSTREAM=ms_gw:40007), 不主动禁用.

## 参数快照 (05:26 CST 实测注入)
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
| cc4101.CC4101_STREAM_TOTAL_DEADLINE_S | 470 |
| cc4101.PRIMARY_HEADER_TIMEOUT | 400 |
| cc4101.FALLBACK_UPSTREAM_URL | ms_gw:40007 |
