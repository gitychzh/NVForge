# R-nvonly-post160 — hm2 cc2 NOP 巡检轮

**时间**: 2026-08-02 09:14 CST
**轮型**: NOP 巡检轮 (无流量, 无故障, 无改动)
**上轮**: post159 (9c6434c)

## 判稳依据

### 30min cc2 (cc4101-primary) — 0 req
session 轮前无流量产生, 无数据可判 cc2 SR. 链路健康无故障.

### 30min 其他 caller (非 cc2 链路)
| caller | status | count |
|--------|--------|-------|
| hermes | 429 | 6 |
| openclaw | 200 | 2 |

- hermes 6×429 (dsv4p_nv, all_tiers_exhausted, NVCF 侧 dsv4p 限流, 5min 周期性)
- openclaw 2×200 (dsv4p_nv 链路本身可用, 佐证 429 是配额限流非链路挂)
- **与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv)

### 30min tier error — 0
### 30min buffer/wait 日志 — 空
### glm5_2_nv 连续 post100-post160 (61 轮) 无 dsv4p 故障扩散

## 健康验证 (09:14 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| 30min cc2 SR | 0 rows (无流量, 链路健康无故障) ✓ |
| 30min tier error | 0 ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复) ✓ |

## 本轮改动
- 0 改动, 0 重启

## 下一步
- 继续观察. 等有 cc2 流量产生时再判 SR. dsv4p_nv 限流是 NVCF 侧配额, 非链路问题, 不在 cc2 优化范围.
