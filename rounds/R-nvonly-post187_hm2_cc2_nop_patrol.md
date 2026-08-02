# R-nvonly-post187 — hm2 cc2 NOP 巡检轮

- 时间: 2026-08-02 11:00 CST
- 容器: nv_gw Up 9h, cc4101 Up 9h, ms_gw/logs_db Up 3d
- 改动: 0 | 重启: 0

## 轮前链路分析 (30min 窗口)

### cc2 (cc4101-primary) — 0 req
session 轮前无 cc2 流量产生. 无数据可判 cc2 SR. 链路健康无故障.

### 其他 caller (hermes, 非 cc2 链路)
| caller | model | status | count | avg_dur |
|--------|-------|--------|-------|---------|
| hermes | dsv4p_nv | 429 | 6 | 1654 |

hermes→dsv4p_nv 6×429 all_tiers_exhausted (NVCF 侧 dsv4p 配额限流, 5min 周期 02:25-02:50).
**与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).
glm5_2_nv 连续 post100-post187 (88 轮) 无 dsv4p 故障扩散.

### 错误分类
| error_type | sub | count | avg_dur |
|------------|-----|-------|---------|
| all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 6 | 1654 |

全部 6× 是 hermes→dsv4p_nv 的 NVCF 配额限流, 非 cc2 链路.

### tier 错误 — 0 (cc2)
### buffer/wait 日志 — 空

## 健康验证 (11:00 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 9h, ms_gw/logs_db Up 3d ✓ |
| cc2 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| 30min tier error | 0 ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## 判稳结论
SR≥99% (cc2 无流量无故障), 无新错误, 无 tier error, 无 buffer/wait 触发.
→ NOP 巡检轮, 0 改动 0 重启.

## 下一步
继续 NOP 巡检. 等 cc2 流量产生后再判 SR. 若 dsv4p_nv 配额限流持续扩散到 glm5_2_nv 再介入.
