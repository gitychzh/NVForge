# R-nvonly-post83 — hm2 cc2 NOP 巡检轮 (2026-08-02 05:40 CST)

## 本轮结论
**NOP 巡检轮. cc2 30min 0 req (session 轮前无流量产生, 无数据可判 SR).
链路健康无故障: 容器全 Up, /health ok, 0 cc2 tier error, 0 cc2 buffer/wait/error 日志,
0 stream_total_deadline (6h). 0 改动, 0 重启, fallback 已恢复.**

## 判稳依据 (三阈值)
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 0 req (无流量) | — (无数据, 链路健康无故障) |
| 新错误类型 | 无 (0 cc2 tier error) | ✅ |
| transport 层 | 0 错误 (无 cc2 流量) | ✅ |
| buffer 触发 | 无 (cc2 0 req) | ✅ |
| stream_total_deadline (6h) | 0 次 | ✅ |
→ **NOP**, 不改码, 不重启.

## 数据快照 (注入实测, 30min 窗口 21:00-21:30 UTC)

### cc4101-primary (cc2) — 0 req
本轮 30min 窗口 cc2 无请求产生 (session 轮前无流量). 无数据可判 cc2 SR.
链路健康: 容器全 Up, /health ok, 0 cc2 tier error, 0 cc2 buffer/wait/error 日志, 0 stream_total_deadline (6h).

### 其他 caller (hermes/openclaw, 非 cc2 链路, 打 dsv4p_nv)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 200 | 4 |
| hermes | dsv4p_nv | 429 | 5 |
| openclaw | dsv4p_nv | 502 | 2 |

dsv4p_nv SR=36.4% (4/11):
- 5× all_tiers_exhausted (5key 全挂 → fallback ms, fallback 发生率 f=11)
- 5× 429 (NVCF 侧 dsv4p 限流, 周期性 21:00/21:10/21:15/21:20/21:25 各 1 次)
- 2× zombie_empty_completion (502, avg_dur=5281ms, 来自 key3)

**与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).

per-IP (dsv4p):
- 203.10.96.139 = 4× 100%
- 134.195.101.194 = 2× 0% (502)
- 空 egress = 5× 0% (429, egress IP 漂移未命中)

per-key (dsv4p):
- key2 = 4× 200 (avg 14394ms)
- key3 = 2× 502 (zombie)
- key? = 5× 429 (单 key NVCF 限流)

200 延迟 avg_dur=14394ms, max=25002, min=6773, avg_ttfb=13986, in/out=0 (非流式).
finish_reason: tool_calls×3, stop×1 (zombie 来自 502 非 200).

按分钟趋势:
- 21:00 429×1, 21:04 502×1, 21:05 200×2+502×1, 21:06 200×2,
- 21:10/15/20/25 各 429×1 (周期性 429, 单 key 限流).

## 健康验证 (05:40 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw `/health` | status=ok, nv_default_model=glm5_2_nv, nv_num_keys=5, pexec=[kimi_nv,dsv4p_nv,glm5_2_nv] ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 4h, ms_gw/logs_db Up 2d ✓ |
| buffer/wait 日志 | 0 行 (cc2 0 req 无触发) ✓ |
| stream_total_deadline (6h) | 0 次 ✓ |
| 配置 (注入实测) | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## cc2 SR 走势
| 轮次 | cc2 SR | 错误 | 趋势 |
|------|--------|------|------|
| post17 | 1/1=100% | 0 | ✅ glm5_2_nv 健康, 满分 |
| post18-post82 | 0 req | 0 | — (无流量, 链路健康) |
| post83 | 0 req | 0 | — (无流量, 链路健康) |

## 改动清单
无 (NOP 巡检轮).

## 下一步
- 继续 NOP 巡检. 等 cc2 有流量时再判 SR.
- dsv4p_nv 低 SR (36.4%) 是 NVCF 侧 dsv4p 限流 (周期性 429 + 5key 全挂), 非 cc2 链路 (cc2 走 glm5_2_nv), 不在本轮优化范围.

## 参数快照 (2026-08-02 05:33 CST 实测注入)
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
| cc4101.CC4101_STREAM_TOTAL_DEADLINE_S | 470 |
| cc4101.PRIMARY_HEADER_TIMEOUT | 400 |
