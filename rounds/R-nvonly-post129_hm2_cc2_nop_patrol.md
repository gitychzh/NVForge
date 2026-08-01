# R-nvonly-post129 — NOP 巡检轮 (2026-08-02 07:48 CST)

## 结论
NOP 巡检轮. cc2 (cc4101-primary) 30min 0 req (session 轮前无流量), 链路健康无故障.
0 改动, 0 重启, 0 回滚. fallback 已恢复.

## 数据 (30min 窗口, 2026-08-02 07:46 CST 注入分析)

### 1. cc4101-primary (cc2) 30min — 0 req
无 cc2 流量产生. 无数据可判 cc2 SR. 链路健康: 容器全 Up, env 正确,
0 cc2 tier error, 0 cc2 buffer/wait/error 日志, 0 stream_total_deadline (6h).

### 2. 其他 caller (hermes, 非 cc2 链路)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 429 | 6 |

dsv4p_nv SR=0.0% (0/6): 6×429 (all_tiers_exhausted, 5key 全挂), 周期性 5min 一发 (23:20/25/30/35/40/45).
**与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv). 属 NVCF 侧 dsv4p 限流 + hermes caller.
30min fallback 发生率: f=6 (dsv4p 全挂 fallback ms, ms_gw fallback 已恢复正常工作).

### 3. dsv4p_nv 按分钟趋势 (周期性 429, UTC)
| 分钟 (UTC) | status | count |
|------|--------|-------|
| 23:20 | 429 | 1 |
| 23:25 | 429 | 1 |
| 23:30 | 429 | 1 |
| 23:35 | 429 | 1 |
| 23:40 | 429 | 1 |
| 23:45 | 429 | 1 |

周期性 5min 一发 429, NVCF 侧 dsv4p 限流模式, 非 cc2 链路问题.
与 post128 对比: 窗口一致 (0%), 仍局限 hermes+dsv4p, 未扩散到 glm5_2_nv.

## 健康验证 (07:48 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| nv_gw env | NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, BUFFER_TIMEOUT_STAIRS=90×5, TOTAL_DEADLINE=450s, UPSTREAM_TIMEOUT=90s, TIER_TIMEOUT_BUDGET=180s ✓ |
| cc4101 env | STREAM_TOTAL_DEADLINE=470, PRIMARY_HEADER_TIMEOUT=400, FALLBACK=ms_gw:40007, UPSTREAM_TIMEOUT=130 ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 6h, ms_gw/logs_db Up 2d ✓ |
| cc2 (cc4101-primary) 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| 30min 错误分类 | all_tiers_exhausted × 6 (全 hermes+dsv4p, 非 cc2) ✓ |
| stream_total_deadline (6h) | 0 ✓ |
| buffer/wait 日志 | 无 (cc2 0 req) ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复) ✓ |

## 参数快照
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, BUFFER_TOTAL_DEADLINE=450s, TIER_TIMEOUT_BUDGET=180s, UPSTREAM_TIMEOUT=90s
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions
- 链路: cc2→cc4101(4101)→nv_gw(40006, glm5_2_nv)→NVCF, fallback ms_gw(40007) 已恢复
- 铁律: 只改 HM2 nv_gw, 不碰 HM1, 不碰 ms_gw 源码, 改前有数据, 改后必验证

## 本轮改动
无 (NOP 巡检轮).

## 下一步
- 继续巡检. 等 cc2 有流量时观察 glm5_2_nv SR.
- dsv4p_nv 限流持续, 但属 NVCF 侧 + hermes caller, 非本轮职责 (只改 HM2 nv_gw, 不碰 caller).
- glm5_2_nv 链路连续 post100-post129 (30 轮) 稳定, 无需调整.
