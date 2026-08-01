# R-nvonly-post111 — NOP 巡检轮 (hm2_cc2)

**日期**: 2026-08-02 06:54 CST
**轮次**: R-nvonly-post111
**改动**: 0 改动, 0 restart, NOP 巡检轮
**主机**: HM2 (100.109.57.26, opc2_uname)

## 依据

### 1. cc4101-primary (cc2) 30min 窗口 — 0 req
本轮 30min 窗口 cc2 无请求产生 (session 轮前无流量). 无数据可判 cc2 SR.
链路健康无故障: 容器全 Up, env 配置正确, 0 cc2 tier error, 0 cc2 buffer/wait/error 日志.

### 2. 其他 caller (hermes, 非 cc2 链路)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 200 | 3 |
| hermes | dsv4p_nv | 429 | 5 |

dsv4p_nv SR=37.5% (3/8): 3×200 + 5×429 (all_tiers_exhausted, 5key 全挂), 周期性 5min 一发 429.
**与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).
30min fallback 发生率: f=8 (dsv4p 全挂 fallback ms, ms_gw fallback 已恢复正常工作).

### 3. dsv4p_nv 按分钟趋势 (周期性 429, UTC)
| 分钟 (UTC) | status | count |
|------|--------|-------|
| 22:25 | 429 | 1 |
| 22:30 | 429 | 1 |
| 22:35 | 429 | 1 |
| 22:40 | 200 | 3 |
| 22:45 | 429 | 1 |
| 22:50 | 429 | 1 |

周期性 5min 一发 429 后 22:40 恢复 200×3, NVCF 侧 dsv4p 限流模式, 非 cc2 链路问题.
与 post110 对比: dsv4p_nv 窗口相同 (37.5%, 3/8), 仍局限 hermes+dsv4p, 未扩散到 glm5_2_nv.
glm5_2_nv 连续 post100-post111 (12 轮) 无 dsv4p 故障扩散.

## 健康验证 (06:54 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| nv_gw env | NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, TOTAL_DEADLINE=450s ✓ |
| cc4101 env | STREAM_TOTAL_DEADLINE=470, PRIMARY_HEADER_TIMEOUT=400, FALLBACK=ms_gw:40007 ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 5h, ms_gw/logs_db Up 2d ✓ |
| cc2 (cc4101-primary) 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| 30min 错误分类 | all_tiers_exhausted × 5 (全 hermes+dsv4p, 非 cc2) ✓ |
| 30min tier error | 0 rows (无 cc2 流量) ✓ |
| buffer/wait 日志 | 无 (cc2 0 req) ✓ |

## 改动
无. NOP 巡检轮, SR≥99% 判稳条件无法评估 (无 cc2 流量), 链路健康无故障, 不改码.

## 验证
无改动, 仅健康验证通过.

## 下一步
- 继续巡检. 等 cc2 有流量时观察 glm5_2_nv SR.
- dsv4p_nv 限流持续, 但属 NVCF 侧 + hermes caller, 非本轮职责 (只改 HM2 nv_gw, 不碰 caller).
- glm5_2_nv 链路连续 12 轮稳定, 无需调整.

## 参数快照 (2026-08-02 06:54 CST)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, BUFFER_TOTAL_DEADLINE=450s, TIER_TIMEOUT_BUDGET=180s, UPSTREAM_TIMEOUT=90s
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions
- 链路: cc2→cc4101(4101)→nv_gw(40006, glm5_2_nv)→NVCF, fallback ms_gw(40007) 已恢复
- 铁律: 只改 HM2 nv_gw, 不碰 HM1, 不碰 ms_gw 源码, 改前有数据改后必验证
