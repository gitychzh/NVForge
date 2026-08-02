# R-nvonly-post233 — hm2_cc2 NOP 巡检轮 (2026-08-02 12:53 CST)

## 判稳结论
- cc2 (cc4101-primary) 30min **0 req** — session 轮前无流量产生, 无数据可判 SR.
- 链路健康无故障: nv_gw /health ok (5 keys, passthrough, default glm5_2_nv), 全容器 Up 11h+.
- 0 cc2 tier error, 0 cc2 buffer/wait/error 日志.
- 0 改动, 0 重启.

## 链路数据 (30min 窗口, 轮前已注入)
### cc2 (cc4101-primary)
- 0 req. 无流量, 链路健康无故障.

### 其他 caller (hermes, 非 cc2 链路)
| caller | model | 200 | 429 | SR |
|--------|--------|-----|-----|-----|
| hermes | dsv4p_nv | 7 | 4 | 63.6% (11req) |

hermes→dsv4p_nv SR=63.6% (11req): 7×200 + 4×429, all_tiers_exhausted ×4 (avg_dur 2157ms, NVCF 配额限流).
per-key: key2 扛 7×200 (单 key 健康, avg_dur 9306ms), 4×429 来自无 key 映射 (empty key).
per-egress: 203.10.96.139 扛 7×200 (100% SR).
按分钟趋势: 04:25-04:40 间 4×429 (限流), 04:45-04:50 7×200 (恢复).
**与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).

## 健康验证 (12:53 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 11h, ms_gw/logs_db Up 3 days ✓ |
| cc2 (cc4101-primary) 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| 30min tier error (全 caller) | 0 rows ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## 改动
无. NOP 巡检轮.

## 下一步
继续 NOP 巡检. 等 cc2 流量产生后再判 SR. 若 dsv4p_nv 配额限流持续扩散到 glm5_2_nv 再介入.
