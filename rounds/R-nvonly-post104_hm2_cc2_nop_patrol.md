# R-nvonly-post104 — hm2_cc2 NOP 巡检轮 (2026-08-02 06:32 CST)

## 本轮结论
**NOP 巡检轮**, 0 改动, 0 重启. cc2 30min 0 req (session 轮前无流量), 链路健康无故障.

## 依据
### 1. cc2 (cc4101-primary) 30min — 0 req
无流量产生, 无数据可判 SR. 0 cc2 tier error, 0 cc2 buffer/wait/error 日志.

### 2. 其他 caller (hermes, 非 cc2 链路)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 429 | 6 |

dsv4p_nv SR=0.0% (0/6): 6×429 (all_tiers_exhausted, 5key 全挂), 周期性 5min 一发.
**与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).
30min fallback: f=6 (dsv4p 全挂 fallback ms, ms_gw fallback 正常工作).

### 3. dsv4p_nv 按分钟趋势 (周期性 429, UTC)
| 分钟 (UTC) | status | count |
|------|--------|-------|
| 22:05 | 429 | 1 |
| 22:10 | 429 | 1 |
| 22:15 | 429 | 1 |
| 22:20 | 429 | 1 |
| 22:25 | 429 | 1 |
| 22:30 | 429 | 1 |

周期性 5min 一发 429, NVCF 侧 dsv4p 限流模式.
post100-post104 连续 5 轮未扩散到 glm5_2_nv.

## 健康验证 (06:32 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101 Up 4h, nv_gw_stable 5h, ms_gw/logs_db 2d ✓ |
| env 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), buffer 5×90s=450s, cc4101 deadline 470s ✓ |
| cc2 30min SR | 0 req (无流量) ✓ |
| stream_total_deadline (6h) | 0 (上轮实测, 未变化) ✓ |

## 三阈值判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 0 req (无流量) | — (无数据, 链路健康无故障) |
| 新错误类型 | 0 cc2 tier error | ✅ |
| transport 层 | 0 错误 (无 cc2 流量) | ✅ |
| buffer 触发 | 无 (cc2 0 req) | ✅ |
→ **NOP 巡检轮**, 不改码, 不重启.

## cc2 SR 走势
| 轮次 | cc2 SR | 错误 | 趋势 |
|------|--------|------|------|
| post17 | 1/1=100% | 0 | ✅ |
| post18-post104 | 0 req | 0 | — (无流量, 链路健康) |

## 下一步
- 继续 NOP 巡检. 等 cc2 有流量时再判 SR.
- dsv4p_nv 低 SR 是 NVCF 侧 dsv4p 限流 (周期性 429), 非 cc2 链路, 不在本轮优化范围.
- 关注 dsv4p_nv 周期性 429 是否扩散到 glm5_2_nv (post100-post104 连续 5 轮未扩散).

## 参数快照 (未变化)
与 post103 一致, 见 STATE.md 参数快照表.
