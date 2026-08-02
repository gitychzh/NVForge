# R-nvonly-post185 — hm2 cc2 NOP 巡检轮

**时间**: 2026-08-02 10:47 CST
**轮型**: NOP 巡检轮 (无流量, 无故障, 无改动)
**主仓 HEAD**: c6fa600 (post184 已 push)

## 数据 (30min 窗口, 10:47 CST)

### cc2 (cc4101-primary) — 0 req
session 轮前无流量产生, 无数据可判 cc2 SR。链路健康无故障。

### 其他 caller (非 cc2 链路)
| caller | model | status | count | avg_dur |
|--------|-------|--------|-------|---------|
| hermes | dsv4p_nv | 429 | 6 | 1625 |

hermes→dsv4p_nv 6×429 all_tiers_exhausted (NVCF 侧 dsv4p 配额限流, 5min 周期 02:20-02:45)。
**与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv)。

### 错误分类
| error_type | sub | count | avg_dur |
|------------|-----|-------|---------|
| all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 6 | 1625 |

全部 6× 是 hermes→dsv4p_nv 的 NVCF 配额限流, 非 cc2 链路。

### tier 错误 (cc2) — 0
### buffer/wait 日志 — 空

## 健康验证
| 项 | 结果 |
|----|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 9h, ms_gw/logs_db Up 3d ✓ |
| cc2 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| 30min tier error (cc2) | 0 ✓ |
| 30min 全 caller | hermes 6req dsv4p_nv (6×429 限流), cc2 0 req ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## 改动
0 改动, 0 重启 (NOP 巡检轮)。

## 判稳依据
- cc2 30min 0 req, 链路健康无故障, 无数据可判 SR → NOP。
- 唯一错误 (hermes→dsv4p_nv 6×429) 是 NVCF 侧 dsv4p 配额限流, 与 cc2 (glm5_2_nv) 无关。
- glm5_2_nv 连续 post100-post184 (85 轮) 无 dsv4p 故障扩散到 glm5_2_nv。
- 容器全 Up, 配置正确, fallback 已恢复。

## 下一步
继续 NOP 巡检。等 cc2 流量产生后再判 SR。若 dsv4p_nv 配额限流持续扩散到 glm5_2_nv 再介入。
