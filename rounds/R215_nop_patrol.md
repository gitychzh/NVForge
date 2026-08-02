# R-nvonly-post215 (2026-08-02 12:25 CST) — hm2_cc2 NOP 巡检轮

## 本轮结论
NOP 巡检轮. cc2 (cc4101-primary) 30min **0 req** (session 轮前无流量产生, 无数据可判 SR).
链路健康无故障: nv_gw /health ok (5 keys, passthrough, default glm5_2_nv), env 配置正确,
全容器 Up 10h+, 0 cc2 tier error, 0 cc2 buffer/wait/error 日志.
**0 改动, 0 重启.**

## 依据 (轮前链路分析注入数据)
- cc2 (cc4101-primary) 30min: 0 rows (无流量, 链路健康无故障).
- 其他 caller (hermes, 非 cc2 链路): hermes→dsv4p_nv 39req (36×200/2×429/1×502, SR=92.3%,
  all_tiers_exhausted ×3, NVCF 配额限流, 5key 全 cooling).
  **与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).
- 30min cc2 tier error: 0. 30min cc2 buffer/wait 日志: 空.
- 配置正确: NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, BUFFER_MAX_RETRIES=5.

## 健康验证 (12:25 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 10h, ms_gw/logs_db Up 3d ✓ |
| cc2 (cc4101-primary) 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| 30min tier error (cc2) | 0 ✓ |
| 30min 全 caller | hermes 39req dsv4p_nv (36×200/2×429/1×502 限流), cc2 0 req ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## 改动
无 (NOP 巡检轮).

## 下一步
继续 NOP 巡检. 等 cc2 流量产生后再判 SR. 若 dsv4p_nv 配额限流持续扩散到 glm5_2_nv 再介入.
