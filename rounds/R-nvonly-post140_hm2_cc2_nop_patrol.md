# R-nvonly-post140 — hm2 cc2 NOP 巡检轮

**日期**: 2026-08-02 08:19 CST
**轮次**: R-nvonly-post140 (NOP 巡检轮)
**上轮**: post139 (4f40ccb)

## 本轮改动
0 改动, 0 重启, NOP 巡检轮.

## 依据 (轮前链路分析 08:19 CST)
- cc2 (cc4101-primary) 30min: **0 req** (session 轮前无流量产生, 无数据可判 SR)
- 链路健康无故障: 容器全 Up, env 配置正确, 0 cc2 tier/buffer/wait/error 日志, 0 stream_total_deadline (6h)
- 其他 caller (hermes, 非 cc2 链路): dsv4p_nv SR=50.0% (5/10)
  - 5×429 all_tiers_exhausted (周期性 5min 一发, NVCF 侧 dsv4p 限流)
  - 5×200
- **与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv)
- 30min fallback 发生率: f=10 (dsv4p 全挂 fallback ms, ms_gw fallback 已恢复正常工作)

## dsv4p_nv 按分钟趋势 (周期性 429, UTC)
| 分钟 (UTC) | status | count |
|------|--------|-------|
| 00:00 | 429 | 1 |
| 00:05 | 429 | 1 |
| 00:10 | 429 | 1 |
| 00:15 | 429 | 1 |
| 23:50 | 429 | 1 |
| 23:55-56 | 200 | 5 |

周期性 5min 一发 429, NVCF 侧 dsv4p 限流模式, 与 post135-post139 完全一致 (数据复测确认).

## 健康验证 (08:19 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| nv_gw env | NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, BUFFER_TIMEOUT_STAIRS=90×5, TOTAL_DEADLINE=450s, UPSTREAM_TIMEOUT=90s, TIER_TIMEOUT_BUDGET=180s ✓ |
| cc4101 env | STREAM_TOTAL_DEADLINE=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130, FALLBACK=ms_gw:40007 ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 6h, ms_gw/logs_db Up 2d ✓ |
| cc2 (cc4101-primary) 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| 30min 错误分类 | all_tiers_exhausted × 5 (全 hermes+dsv4p, 非 cc2) ✓ |
| stream_total_deadline (6h) | 0 ✓ |
| buffer/wait 日志 | 无 (cc2 0 req) ✓ |

## 结论
- cc2 链路 (glm5_2_nv) 连续 post100-post140 (41 轮) 无故障扩散, 无需调整.
- dsv4p_nv 限流持续, 但属 NVCF 侧 + hermes caller, 非本轮职责 (只改 HM2 nv_gw, 不碰 caller).
- NOP 巡检轮, 0 改动, 0 重启.

## 下一步
- 继续巡检. 等 cc2 有流量时观察 glm5_2_nv SR.
- dsv4p_nv 限流非本轮职责.
