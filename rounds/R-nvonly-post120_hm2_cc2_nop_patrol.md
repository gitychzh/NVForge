# R-nvonly-post120 — NOP 巡检轮 (hm2_cc2)

**日期**: 2026-08-02 07:23 CST
**方向**: R-nvonly (nv_gw 5key+5IP 自恢复, fallback 已恢复不主动禁用)
**改动**: 0 | **重启**: 0 | **回滚**: 无

## 轮前链路分析 (30min 窗口, 07:22 CST 注入)

### cc2 (cc4101-primary) 专属 — 0 req
本轮 30min 窗口 cc2 无请求产生 (session 轮前无流量). 无数据可判 cc2 SR.
链路健康无故障: 0 tier error, 0 buffer/wait/error 日志, 0 stream_total_deadline (6h).
与 post114-119 一致的 NOP 模式 (cc2 轮前静默, 工具调用本身经 cc4101→nv_gw 链路).

### 其他 caller (hermes/openclaw, 非 cc2 链路)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 200 | 3 |
| hermes | dsv4p_nv | 429 | 5 |
| openclaw | dsv4p_nv | 200 | 1 |

dsv4p_nv SR=44.4% (4/9): 4×200 + 5×429 (all_tiers_exhausted, 5key 全挂, avg_dur 1258s).
**与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv). NVCF 侧 dsv4p 限流, 周期性 5min 一发.
30min fallback 发生率: f=9 (dsv4p 全挂 fallback ms, ms_gw fallback 已恢复).

### dsv4p_nv 按分钟趋势 (UTC)
| 分钟 | status | count |
|------|--------|-------|
| 22:55 | 429 | 1 |
| 23:00 | 429 | 1 |
| 23:04 | 200 | 1 |
| 23:05 | 429 | 1 |
| 23:10 | 429 | 1 |
| 23:15 | 200 | 2 |
| 23:16 | 200 | 1 |
| 23:20 | 429 | 1 |

周期性 5min 一发 429, 间夹 200, NVCF 侧 dsv4p 限流模式.
与 post119 对比: 持平 (44.4% vs 44.4%), 仍局限 hermes+dsv4p, 未扩散到 glm5_2_nv.

## 判稳 + 行动
- cc2 0 req, 链路健康无故障, glm5_2_nv 连续 20 轮稳定 → **NOP 巡检轮**.
- dsv4p_nv 限流属 NVCF 侧 + hermes/openclaw caller, 非本轮职责 (只改 HM2 nv_gw, 不碰 caller).
- 0 改动, 0 重启. 无需验证 (未改码).

## 健康验证 (07:22 CST 注入数据)
| 验证项 | 结果 |
|--------|------|
| 容器状态 | nv_gw/cc4101/nv_gw_stable Up 5h, ms_gw/logs_db Up 2d ✓ |
| env 配置 | NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, deadline 470s ✓ |
| cc2 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| 30min 错误分类 | all_tiers_exhausted × 5 (全 hermes+dsv4p, 非 cc2) ✓ |
| 30min tier error | 0 rows (无 cc2 流量) ✓ |
| stream_total_deadline (6h) | 0 ✓ |
| buffer/wait 日志 | 无 (cc2 0 req) ✓ |
| fallback | f=9 (dsv4p 全挂 fallback ms, 已恢复) ✓ |

## 下一步
- 继续巡检. 等 cc2 有流量时观察 glm5_2_nv SR.
- dsv4p_nv 限流持续, 但属 NVCF 侧 + 非 cc2 caller, 不在本轮职责内.
- glm5_2_nv 链路连续 21 轮稳定, 无需调整.
