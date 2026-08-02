# R-nvonly-post189 — hm2 cc2 NOP 巡检轮

**日期**: 2026-08-02 ~11:05 CST
**轮次**: R-nvonly-post189 (NOP 巡检)
**主仓 HEAD**: 382cd14 (post188 已 push)

## 决策

NOP 巡检轮. cc2 (cc4101-primary) 30min **0 req**, 无流量可判 SR.
链路健康无故障, 0 改动, 0 重启.

## 依据

### 1. cc2 (cc4101-primary) 30min — 0 req
session 轮前无 cc2 流量产生, 无数据可判 SR. 链路健康无故障.

### 2. 其他 caller — hermes→dsv4p_nv 6×429 (非 cc2 链路)
| caller | status | count |
|--------|--------|-------|
| hermes | 429 | 6 |

全部为 hermes→dsv4p_nv 的 NVCF 配额限流 (5min 周期 02:35-03:00),
all_tiers_exhausted, **与 cc2 无关** (cc2 走 glm5_2_nv).

### 3. 30min 错误分类
| error_type | sub | count | avg_dur |
|------------|-----|-------|---------|
| all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 6 | 1706 |

全部 6× 是 hermes→dsv4p_nv 限流, 非 cc2.

### 4. tier 错误 — 0 (cc2, nv_tier_attempts 无 cc4101-primary rows)
### 5. buffer/wait 日志 — 空 (cc2 无 buffer 触发)

## KeyManager 行为 (dsv4p_nv, 正常退避)
dsv4p_nv per-key 全 429, 5key 轮转后 all_tiers_exhausted (符合设计: 5key×配额限流→全挂→429).
KeyManager 429 指数退避工作正常, 符合设计. 与 cc2 无关 (cc2 不打 dsv4p_nv).

## 健康验证 (11:05 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 9h, ms_gw/logs_db Up 3d ✓ |
| cc2 (cc4101-primary) 30min SR | 0 rows (无流量, 无故障) ✓ |
| 30min tier error | 0 ✓ |
| 30min 全 caller | hermes 6req dsv4p_nv (6×429 限流), cc2 0 req ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## 改动
无. 0 改动, 0 重启.

## 下一步
继续 NOP 巡检. 等 cc2 流量产生后再判 SR.
若 dsv4p_nv 配额限流持续扩散到 glm5_2_nv 再介入.
glm5_2_nv 连续 post100-post189 (90 轮) 无 dsv4p 故障扩散.
