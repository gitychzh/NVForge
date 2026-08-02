# R-nvonly-post181 — hm2 cc2 NOP 巡检轮

**时间**: 2026-08-02 10:32 CST
**上轮**: R-nvonly-post180 (NOP 巡检轮)
**本轮**: NOP 巡检轮 (0 改动, 0 重启)

## 判稳依据
- cc2 (cc4101-primary) 30min: **0 req** (session 轮前无流量产生, 无数据可判 SR)
- 链路健康无故障: nv_gw /health ok (5 keys, passthrough, default glm5_2_nv)
- 0 cc2 tier error, 0 cc2 buffer/wait/error 日志
- 容器全 Up: nv_gw/cc4101 8h, nv_gw_stable 9h, ms_gw/logs_db 3d
- 配置正确: NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007

## 30min 链路数据
| caller | model | status | count | avg_dur |
|--------|-------|--------|-------|---------|
| hermes | dsv4p_nv | 200 | 4 | 9823 |
| hermes | dsv4p_nv | 429 | 5 | 1590 |

- hermes→dsv4p_nv SR=44.4% (4/9, all_tiers_exhausted ×5, NVCF 侧 dsv4p 配额限流, 5min 周期 02:05-02:30)
- **与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv)
- glm5_2_nv 连续 post100-post180 (81 轮) 无 dsv4p 故障扩散

## 健康验证 (10:32 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101 Up 8h, ms_gw/logs_db Up 3d ✓ |
| cc2 (cc4101-primary) 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| 30min tier error | 0 ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复) ✓ |

## 本轮改动
无 (NOP 巡检轮)

## 下一步
继续 NOP 巡检. 等 cc2 流量产生后再判 SR. 若 dsv4p_nv 配额限流持续扩散到 glm5_2_nv 再介入.
