# R-nvonly-post127 — hm2 cc2 NOP 巡检轮 (2026-08-02 07:43 CST)

## 基线
- 主仓 HEAD: d66f158 (post126) → 本轮 post127
- 上轮: R-nvonly-post126 NOP 巡检轮

## 本轮数据 (30min 窗口, 07:41 CST 轮前注入)

### cc4101-primary (cc2) — 0 req
- cc2 30min 0 req (session 轮前无流量产生, 无数据可判 SR)
- 0 stream_total_deadline (6h)
- 0 cc2 tier error, 0 buffer/wait/error 日志
- 链路健康无故障

### hermes+dsv4p_nv (非 cc2 链路)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 200 | 3 |
| hermes | dsv4p_nv | 429 | 5 |

- dsv4p_nv SR=37.5% (3/8): 3×200 + 5×429(all_tiers_exhausted, 5key 全挂)
- 周期性 5min 一发 429 (23:20/23:25/23:30/23:35/23:40), 间夹 200 (23:15×2, 23:16×1)
- NVCF 侧 dsv4p 限流模式, 非 cc2 链路问题 (cc2 走 glm5_2_nv)
- 30min fallback f=8 (dsv4p 全挂 fallback ms, ms_gw fallback 已恢复)

## 健康验证 (07:43 CST)
| 项 | 结果 |
|----|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 6h, ms_gw/logs_db Up 2d ✓ |
| cc2 30min SR | 0 rows (无流量) ✓ |
| 30min errors | all_tiers_exhausted × 5 (全 hermes+dsv4p, 非 cc2) ✓ |
| stream_total_deadline 6h | 0 ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK=ms_gw:40007 ✓ |

## 本轮改动
- 0 改动, 0 重启 (NOP 巡检轮)

## 判稳结论
SR 无数据 (cc2 无流量), 无新错误, 链路健康 → NOP 巡检轮.
dsv4p_nv 限流持续但属 NVCF 侧 + hermes caller, 非本轮职责 (只改 HM2 nv_gw, 不碰 caller).
glm5_2_nv 链路连续 post100-post127 (28 轮) 稳定, 无需调整.

## 下一步
- 继续巡检. 等 cc2 有流量时观察 glm5_2_nv SR.
- dsv4p_nv 限流持续, 属 NVCF 侧 + hermes caller, 非本轮职责.
