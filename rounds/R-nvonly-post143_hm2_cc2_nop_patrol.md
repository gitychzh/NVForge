# R-nvonly-post143 — hm2 cc2 NOP 巡检轮

**时间**: 2026-08-02 00:29:05 UTC (2026-08-02 08:29:05 CST)
**上轮**: R-nvonly-post142 (NOP)
**容器**: nv_gw/cc4101/nv_gw_stable Up 6h, ms_gw/logs_db Up 2d

## 本轮数据 (30min 窗口, 轮前链路分析注入)

### cc4101-primary (cc2) — 0 req
本轮 30min cc2 无流量产生 (session 轮前无请求). 无数据可判 SR.
链路健康无故障: 容器全 Up, env 配置正确, 0 cc2 tier error, 0 buffer/wait 日志, 0 stream_total_deadline (6h).

### 其他 caller (hermes, 非 cc2 链路)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 429 | 6 |

dsv4p_nv SR=0.0% (0/6): 6×429 (all_tiers_exhausted, 5key 全挂, avg_dur=1554s).
周期性 5min 一发 429 (00:00/05/10/15/20/25), NVCF 侧 dsv4p 限流模式.
**与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).

## 健康验证
| 项 | 结果 |
|----|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 6h, ms_gw/logs_db Up 2d ✓ |
| cc2 30min SR | 0 rows (无流量) ✓ |
| 30min 错误分类 | all_tiers_exhausted × 6 (全 hermes+dsv4p, 非 cc2) ✓ |
| stream_total_deadline (6h) | 0 ✓ |
| buffer/wait 日志 | 无 (cc2 0 req) ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), cc4101 deadline 470s, buffer 5×90s=450s ✓ |

## 判稳
- cc2 无流量 → NOP 巡检轮, 只记数据不改码.
- 链路连续 post100-post143 (44 轮) 稳定, glm5_2_nv 无故障扩散.
- dsv4p_nv 限流属 NVCF 侧 + hermes caller, 非本轮职责.

## 本轮改动
- 0 改动, 0 重启.

## 下一步
- 继续巡检. 等 cc2 有流量时观察 glm5_2_nv SR.
- glm5_2_nv 链路连续 44 轮稳定, 无需调整.
