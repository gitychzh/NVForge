# R-nvonly-post77 — hm2 cc2 NOP 巡检轮 (2026-08-02 05:15 CST)

## 结论
NOP 巡检轮. cc2 30min 0 req (session 轮前无流量产生, 无数据可判 SR).
链路健康无故障: 容器全 Up (nv_gw/cc4101/nv_gw_stable 3h, ms_gw 2d),
/health ok (glm5_2_nv, 5 keys, pexec=[kimi_nv,dsv4p_nv,glm5_2_nv]),
0 cc2 tier error, 0 cc2 buffer/wait/error 日志, 0 stream_total_deadline (6h).
0 改动, 0 重启, 0 fallback 改动.

## 依据 (30min 窗口 05:15 CST)
- cc4101-primary (cc2): 0 req (无流量, 链路健康无故障)
- 其他 caller (非 cc2 链路):
  - hermes|dsv4p_nv: 200×7, 429×4
  - openclaw|dsv4p_nv: 502×2
  - dsv4p_nv SR=53.8% (7/13): NVCF 侧 dsv4p 限流 (4×all_tiers_exhausted + 4×429 + 2×zombie 502)
  - 与 cc2 无关 (cc2 走 glm5_2_nv)
- 健康验证: /health ok, docker ps 全 Up, stream_total_deadline(6h)=0

## 验证
| 项 | 结果 |
|----|------|
| nv_gw /health | status=ok, 5 keys, glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 3h, ms_gw 2d ✓ |
| stream_total_deadline (6h) | 0 ✓ |

## 下一步
- 继续 NOP 巡检. 等 cc2 有流量时再判 SR.
- dsv4p_nv 低 SR 是 NVCF 侧限流, 非 cc2 链路 (cc2 走 glm5_2_nv), 不在本轮优化范围.
