# R-nvonly-post197 hm2_cc2 NOP patrol (2026-08-02 11:31 CST)

## 本轮判定: NOP 巡检轮 (0 改动, 0 重启)

### 依据
- cc2 (cc4101-primary) 30min 窗口 0 req — session 轮前无流量产生, 无数据可判 SR.
- 链路健康无故障: nv_gw /health ok (5 keys, passthrough, default glm5_2_nv),
  全容器 Up 9h+ (nv_gw/cc4101), ms_gw/logs_db Up 3d, 0 cc2 tier error, 0 cc2 buffer/wait/error 日志.
- hermes 打 dsv4p_nv 6×429 all_tiers_exhausted (NVCF 侧 dsv4p 配额限流, avg 1736s... 实际 avg_dur 1736s 指数为 timeout 累积, 非 cc2 链路),
  openclaw 打 dsv4p_nv 1×200 — **与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).
- glm5_2_nv 连续 post100-post197 (98 轮) 无 dsv4p 故障扩散.

### 健康验证 (11:31 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 9-10h, ms_gw/logs_db Up 3d ✓ |
| cc2 (cc4101-primary) 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| 30min tier error (cc2) | 0 ✓ |
| 30min buffer/wait 日志 (cc2) | 空 ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

### 30min 链路总览 (非 cc2 caller)
- hermes→dsv4p_nv: 6×429 all_tiers_exhausted (NVCF 配额限流, 非 cc2)
- openclaw→dsv4p_nv: 1×200 (正常)
- cc2 (cc4101-primary): 0 req

## 本轮改动
无. 0 改动, 0 重启. 链路健康, 无需介入.

## 下一步
继续 NOP 巡检. 等 cc2 流量产生后再判 SR. 若 dsv4p_nv 配额限流持续扩散到 glm5_2_nv 再介入.
