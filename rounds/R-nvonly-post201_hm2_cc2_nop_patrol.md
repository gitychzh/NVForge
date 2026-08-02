# R-nvonly-post201 — hm2 cc2 NOP patrol (2026-08-02 11:44 CST)

## 本轮结论
NOP 巡检轮. cc2 30min 0 req (session 轮前无流量产生, 无数据可判 SR).
链路健康无故障: nv_gw /health ok (5 keys, passthrough, default glm5_2_nv),
全容器 Up 10h+, 0 cc2 tier error, 0 cc2 buffer/wait/error 日志.
0 改动, 0 重启.

## 数据依据 (轮前注入, 11:44:32 CST)
### 30min cc2 (cc4101-primary) — 0 req
本轮 30min cc2 无请求产生. 无数据可判 cc2 SR. 链路健康无故障.

### 30min 其他 caller (非 cc2 链路)
- hermes → dsv4p_nv: 6×429 all_tiers_exhausted (NVCF 侧 dsv4p 配额限流, avg_dur ~2160s).
  按分钟趋势 03:15/03:20/03:25/03:30/03:35/03:40 每 5min 1×429.
  **与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).

### 30min 错误分类 (全 caller)
- all_tiers_exhausted (hermes→dsv4p_nv): 6×, 全为 NVCF 配额限流, 非 cc2 链路.

### tier/buffer/wait (cc2) — 0, 空.

## 健康验证 (11:44 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 10h, ms_gw/logs_db Up 3d ✓ |
| cc2 (cc4101-primary) 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| 30min tier error (cc2) | 0 ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## 改动
无. 0 改动, 0 重启.

## 下一步
继续 NOP 巡检. 等 cc2 流量产生后再判 SR.
若 dsv4p_nv 配额限流持续扩散到 glm5_2_nv 再介入.
glm5_2_nv 连续 post100-post200 (101 轮) 无 dsv4p 故障扩散.
