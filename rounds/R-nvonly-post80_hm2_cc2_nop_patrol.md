# R-nvonly-post80 — hm2 cc2 NOP 巡检轮

## 时间
2026-08-02 05:30 CST

## 本轮数据 (30min 窗口, 链路分析注入)

### cc4101-primary (cc2) — 0 req
session 轮前无 cc2 流量产生, 无数据可判 cc2 SR. 链路健康无故障.

### 其他 caller (非 cc2 链路, cc2 走 glm5_2_nv)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 200 | 7 |
| hermes | dsv4p_nv | 429 | 4 |
| openclaw | dsv4p_nv | 502 | 2 |

dsv4p_nv SR=53.8% (7/13): 4×all_tiers_exhausted + 4×429 + 2×zombie_empty_completion(502).
NVCF 侧 dsv4p 限流, 与 cc2 无关 (cc2 走 glm5_2_nv).
per-IP: 203.10.96.139=7×100%, 其余 0% (egress IP 漂移单 IP 限流).
200 延迟 avg_dur=12873ms (正常水位).

## 健康验证
| 项 | 结果 |
|----|------|
| nv_gw /health | ok, glm5_2_nv, 5 keys, pexec=[kimi_nv,dsv4p_nv,glm5_2_nv] ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 3h, ms_gw/logs_db 2d ✓ |
| buffer/wait 日志 | 0 行 (cc2 0 req 无触发) |
| stream_total_deadline (6h) | 0 次 |

## 判稳
三阈值全 ✅ (cc2 0 req 无数据但链路健康无故障, 0 新错误, 0 transport 错误, 0 buffer 触发, 0 deadline).
→ **NOP 巡检轮**, 0 改动, 0 重启.

## 行动
无. 继续等 cc2 有流量时再判 SR. dsv4p_nv 低 SR 是 NVCF 侧限流, 不在本轮优化范围.

## 参数快照
- nv_gw: NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180, KEY_COOLDOWN_S=30, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, FALLBACK_UPSTREAM_URL=ms_gw:40007, PRIMARY_UPSTREAM_MODEL=glm5_2_nv
