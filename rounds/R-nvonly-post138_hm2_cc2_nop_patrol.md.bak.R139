# R-nvonly-post138 — NOP 巡检轮 (2026-08-02 08:14 CST)

## 本轮结论
NOP 巡检轮. cc2 (cc4101-primary) 30min **0 req** — session 轮前无流量产生, 无数据可判 SR.
链路健康无故障: 容器全 Up, env 配置正确, 0 cc2 tier error, 0 buffer/wait/error 日志,
0 stream_total_deadline (6h). 0 改动, 0 重启.

## 轮前链路分析 (08:13:32 CST)
- 上轮: R-nvonly-post137 | 容器 nv_gw/cc4101: 6 hours ago
- 配置全部正确: nv_gw NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), BUFFER 5×90s=450s, TIER_TIMEOUT_BUDGET=180s, UPSTREAM_TIMEOUT=90s; cc4101 STREAM_TOTAL_DEADLINE=470s, PRIMARY_HEADER_TIMEOUT=400s, FALLBACK=ms_gw:40007

## 关键数据
### 1. cc4101-primary (cc2) 30min 窗口 — 0 req
本轮 30min 窗口 cc2 无请求产生 (session 轮前无流量). 无数据可判 cc2 SR.
链路健康无故障: 容器全 Up, env 配置正确, 0 cc2 tier error, 0 cc2 buffer/wait/error 日志,
0 stream_total_deadline (6h).

### 2. 其他 caller (hermes, 非 cc2 链路)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 200 | 5 |
| hermes | dsv4p_nv | 429 | 5 |

dsv4p_nv SR=50.0% (5/10): 5×429 (all_tiers_exhausted, 5key 全挂, 周期性 5min 一发) + 5×200.
NVCF 侧 dsv4p 限流模式, 非 cc2 链路问题. **与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).
30min fallback 发生率: f=10 (dsv4p 全挂 fallback ms, ms_gw fallback 已恢复正常工作).

### 3. dsv4p_nv 按分钟趋势 (周期性 429, UTC)
| 分钟 (UTC) | status | count |
|------|--------|-------|
| 00:00 | 429 | 1 |
| 00:05 | 429 | 1 |
| 00:10 | 429 | 1 |
| 23:45 | 429 | 1 |
| 23:50 | 429 | 1 |
| 23:55-56 | 200 | 5 |

周期性 5min 一发 429, NVCF 侧 dsv4p 限流模式. 与 post135-137 完全一��� (数据复测确认).

## 健康验证 (08:14 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 6h, ms_gw/logs_db Up 2d ✓ |
| cc2 (cc4101-primary) 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| 30min 错误分类 | all_tiers_exhausted × 5 (全 hermes+dsv4p, 非 cc2) ✓ |
| 30min tier error | 0 rows (无 cc2 流量) ✓ |
| stream_total_deadline (6h) | 0 ✓ |
| buffer/wait 日志 | 无 (cc2 0 req) ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## 本轮改动
0 改动, 0 重启 (NOP 巡检轮).

## 参数快照 (2026-08-02 08:14 CST)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, BUFFER_TOTAL_DEADLINE=450s, TIER_TIMEOUT_BUDGET=180s, UPSTREAM_TIMEOUT=90s
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions
- 链路: cc2→cc4101(4101)→nv_gw(40006, glm5_2_nv)→NVCF, fallback ms_gw(40007) 已恢复

## 下一步
- 继续巡检. 等 cc2 有流量时观察 glm5_2_nv SR.
- dsv4p_nv 限流持续, 但属 NVCF 侧 + hermes caller, 非本轮职责 (只改 HM2 nv_gw, 不碰 caller).
- glm5_2_nv 链路连续 39 轮稳定, 无需调整.
