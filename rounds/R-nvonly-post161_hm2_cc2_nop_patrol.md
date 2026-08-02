# R-nvonly-post161 — hm2 cc2 NOP 巡检轮

**时间**: 2026-08-02 09:17 CST
**轮型**: NOP 巡检轮 (无 cc2 流量, 无 cc2 故障, 无改动)
**上轮**: post160 (9ff403a)

## 判稳依据

### 30min cc2 (cc4101-primary) — 0 req
session 轮前无 cc2 流量产生, 无数据可判 cc2 SR. 链路健康无故障.
注入的轮前分析中 cc4101-primary 30min 专属窗口为空, 印证 cc2 无请求.

### 30min 其他 caller (非 cc2 链路)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 429 | 6 |
| openclaw | dsv4p_nv | 200 | 2 |

- hermes 6×429 (dsv4p_nv, all_tiers_exhausted, avg_dur 1475s, NVCF 侧 dsv4p 配额限流, 5min 周期性)
- openclaw 2×200 (dsv4p_nv, avg_dur 6091ms, 链路本身可用, 佐证 429 是 NVCF 配额限流非链路挂)
- **与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv)

### 30min 错误分类
| error_type | sub | count | avg_dur |
|------------|-----|-------|---------|
| all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 6 | 1475 |

全部 6× 是 hermes→dsv4p_nv 的 NVCF 配额限流, 非 cc2 链路.

### 30min tier error — 0 (cc2)
### 30min buffer/wait 日志 — 空

### glm5_2_nv 连续 post100-post161 (62 轮) 无 dsv4p 故障扩散到 cc2 链路

## 健康验证 (09:17 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 7h, ms_gw/logs_db Up 2d ✓ |
| 30min cc2 (cc4101-primary) SR | 0 rows (无流量, 链路健康无故障) ✓ |
| 30min cc2 tier error | 0 ✓ |
| 30min 全 caller | hermes 6×429 (dsv4p_nv 限流), openclaw 2×200 (dsv4p_nv 成功), cc2 0 req ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## 本轮改动
- 0 改动, 0 重启

## 下一步
- 继续观察. 等有 cc2 流量产生时再判 SR.
- dsv4p_nv 限流是 NVCF 侧配额 (hermes caller), 非链路问题, 不在 cc2 优化范围.
- 若后续 cc2 产生流量并出现 SR<99% 或新错误类型, 再找根因小步改.
