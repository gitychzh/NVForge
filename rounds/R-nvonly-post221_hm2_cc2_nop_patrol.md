# R-nvonly-post221: hm2_cc2 NOP 巡检轮

- 轮号: R-nvonly-post221
- 时间: 2026-08-02 12:36 CST
- 类型: NOP 巡检轮 (无流量无故障, 0 改动 0 重启)

## 链路数据 (30min 窗口, ~12:05–12:35 CST)

### cc2 (cc4101-primary) — 0 req
本轮 30min cc2 无请求产生. 无数据可判 cc2 SR. 链路健康无故障.

### 其他 caller (hermes, 非 cc2 链路)
| caller | model | 200 | 429 | SR |
|--------|--------|-----|-----|-----|
| hermes | dsv4p_nv | 23 | 4 | 85.2% (27req) |

hermes→dsv4p_nv SR=85.2% (27req): 23×200 + 4×429, all_tiers_exhausted ×4 (avg_dur 3663ms, NVCF 配额限流, 5key 全 cooling).
**与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).

### 30min 错误分类
- all_tiers_exhausted (hermes→dsv4p_nv): 4× (avg_dur 3663ms), 全为 NVCF 配额限流, 非 cc2 链路.

### tier / buffer / wait 日志 (cc2) — 空 (无 buffer/wait/keymanager 日志)

## 健康验证 (12:35 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101 Up 11h, nv_gw_stable Up 11h, ms_gw/logs_db Up 3d ✓ |
| cc2 (cc4101-primary) 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| 30min tier error (cc2) | 0 ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## 判稳
cc2 链路 0 req 无流量无故障 → NOP 巡检轮.
dsv4p_nv 限流属 hermes 链路 + NVCF 配额问题, 按"聚焦 cc2 glm5_2_nv"铁律不动 nv_gw (动它反而影响 cc2).
glm5_2_nv 连续 post100-post221 (120 轮) 无 dsv4p 故障扩散.

## 改动
0 改动, 0 重启.

## 下一步
继续 NOP 巡检. 等 cc2 流量产生后再判 SR. 若 dsv4p_nv 配额限流持续扩散到 glm5_2_nv 再介入.
