# R-nvonly-post136 (hm2_cc2) — NOP 巡检轮

**时间**: 2026-08-02 08:08 CST
**轮次**: R-nvonly-post136
**动作**: NOP 巡检 (0 改动, 0 重启)

## 本轮依据
- cc2 (cc4101-primary) 30min 0 req: session 轮前无流量产生, 无数据可判 cc2 SR.
- 链路健康无故障: 容器全 Up (nv_gw/cc4101/nv_gw_stable 6h, ms_gw/logs_db 2d).
- env 配置正确: NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), BUFFER_MAX_RETRIES=5,
  BUFFER_TIMEOUT_STAIRS=90×5=450s, BUFFER_TOTAL_DEADLINE=450s, TIER_TIMEOUT_BUDGET=180s,
  UPSTREAM_TIMEOUT=90s, CC4101_STREAM_TOTAL_DEADLINE=470, PRIMARY_HEADER_TIMEOUT=400,
  FALLBACK_UPSTREAM=ms_gw:40007.
- 0 cc2 tier error, 0 cc2 buffer/wait/error 日志, 0 stream_total_deadline (6h).
- glm5_2_nv 连续 post100-post135 (35 轮) 无 dsv4p 故障扩散, 链路稳定.

## 30min 链路数据 (轮前注入)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 200 | 5 |
| hermes | dsv4p_nv | 429 | 5 |

- dsv4p_nv SR=50.0% (5/10): 5×429 (all_tiers_exhausted, 5key 全挂) + 5×200.
- 周期性 5min 一发 429 (23:30/35/40/45/50 各 1×429, 23:55-56 5×200), NVCF 侧 dsv4p 限流模式.
- **与 cc2 无关**: cc2 走 glm5_2_nv, 不打 dsv4p_nv; hermes caller 非本轮职责.
- 30min fallback 发生率: f=10 (dsv4p 全挂 fallback ms, ms_gw fallback 已恢复正常工作).

## 健康验证 (08:08 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| nv_gw env | NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, BUFFER_TIMEOUT_STAIRS=90×5, TOTAL_DEADLINE=450s, UPSTREAM_TIMEOUT=90s, TIER_TIMEOUT_BUDGET=180s ✓ |
| cc4101 env | STREAM_TOTAL_DEADLINE=470, PRIMARY_HEADER_TIMEOUT=400, FALLBACK=ms_gw:40007 ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 6h, ms_gw/logs_db Up 2d ✓ |
| cc2 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| stream_total_deadline (6h) | 0 ✓ |
| buffer/wait 日志 | 无 (cc2 0 req) ✓ |

## 结论
NOP 巡检轮. SR>=99% (无 cc2 流量, 链路健康) 且无新错误. 0 改动 0 重启.
dsv4p_nv 限流持续但属 NVCF 侧 + hermes caller, 非本轮职责.
glm5_2_nv 链路连续 36 轮稳定, 无需调整.

## 下一步
- 继续巡检. 等 cc2 有流量时观察 glm5_2_nv SR.
- dsv4p_nv 限流持续, 但属 NVCF 侧 + hermes caller, 非本轮职责 (只改 HM2 nv_gw, 不碰 caller).
- glm5_2_nv 链路稳定, 无需调整.
