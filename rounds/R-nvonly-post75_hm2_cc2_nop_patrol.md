# R-nvonly-post75 — hm2 cc2 NOP 巡检轮 (2026-08-02 05:11 CST)

## 结论: NOP 巡检轮, 0 改动 0 重启

cc2 (cc4101-primary) 30min 窗口 0 req (session 轮前无 cc2 流量产生). 无数据可判 cc2 SR.
链路健康无故障, 判稳 → 不改码不重启.

## 数据依据 (30min 窗口 05:09 注入)

### cc4101-primary (cc2) — 0 req
无 cc2 流量. 0 cc2 tier error, 0 buffer/wait/error 日志, 0 stream_total_deadline (6h).

### 其他 caller (非 cc2 链路, dsv4p_nv)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 200 | 7 |
| hermes | dsv4p_nv | 429 | 4 |
| openclaw | dsv4p_nv | 502 | 2 |

dsv4p_nv SR=53.8% (7/13): 4×all_tiers_exhausted (5key 全挂) + 4×429 + 2×zombie_empty_completion (502).
**与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).
per-key: key2=7×200, key3=2×502, key?=4×429 (单 key NVCF 限流).
per-IP: 203.10.96.139=7×100%, 其余 IP=0% (egress 漂移单 IP 限流).
按分钟: 20:40~21:00 周期 4×429, 20:55/21:05~21:06 恢复 7×200.
200 延迟 avg_dur=12873ms, finish_reason: tool_calls×5, stop×2.

## 健康验证 (05:11 CST)
- nv_gw /health: status=ok, nv_default_model=glm5_2_nv, nv_num_keys=5, pexec=[kimi_nv,dsv4p_nv,glm5_2_nv] ✓
- docker ps: nv_gw/cc4101/nv_gw_stable Up 3h ✓
- 配置: NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓

## 三阈值判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 0 req | — (无数据, 链路健康) |
| 新错误类型 | 无 | ✅ |
| transport 层 | 0 (无 cc2 流量) | ✅ |
| buffer 触发 | 无 (cc2 0 req) | ✅ |
| stream_total_deadline (6h) | 0 次 | ✅ |
→ NOP 巡检轮, 0 改动 0 重启.

## 下一步
继续巡检. cc2 走 glm5_2_nv, dsv4p_nv 限流是 hermes/openclaw caller 的 NVCF 侧问题, 非 cc2 链路.
