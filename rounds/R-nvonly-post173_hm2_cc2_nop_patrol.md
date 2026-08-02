# R-nvonly-post173 — hm2 cc2 NOP 巡检轮 (2026-08-02 10:05 CST)

## 轮前链路分析
- 上轮: post172 (NOP). 容器 nv_gw/cc4101 Up 8h.
- 配置无变化同 post172: NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复),
  BUFFER_MAX_RETRIES=5, BUFFER_TIMEOUT_STAIRS=90×5, BUFFER_TOTAL_DEADLINE=450s,
  cc4101 STREAM_TOTAL_DEADLINE=470, PRIMARY_HEADER_TIMEOUT=400.

## 本轮数据 (30min 窗口, 10:00:32 CST 采样)

### 1. cc4101-primary (cc2) — 0 req
本轮 30min cc2 无请求产生. 无数据可判 SR. 链路健康无故障.

### 2. 其他 caller (非 cc2 链路)
| caller | model | status | count | avg_dur |
|--------|-------|--------|-------|---------|
| hermes | dsv4p_nv | 200 | 1 | 5783 |
| hermes | dsv4p_nv | 429 | 5 | 1686 |

hermes→dsv4p_nv SR=16.7% (1/6), all_tiers_exhausted ×5 (5key 全挂, NVCF 侧 dsv4p 配额限流).
**与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).

### 3. 30min 错误分类
| error_type | sub | count | avg_dur |
|------------|-----|-------|---------|
| all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 5 | 1686 |

全部 5× 是 hermes→dsv4p_nv 的 NVCF 配额限流, 非 cc2 链路.

### 4. tier 错误 (cc2) — 0
### 5. buffer/wait 日志 — 空 (无 buffer/wait/keymanager 日志)

## 健康验证 (10:05 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 8h, ms_gw/logs_db Up 3d ✓ |
| cc2 (cc4101-primary) 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| 30min tier error | 0 ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## 本轮改动
**0 改动, 0 重启** — NOP 巡检轮. SR 无数据可判 (cc2 无流量), 链路健康无故障.
hermes→dsv4p_nv 限流与 cc2 无关, 不介入.

## 下一步
继续 NOP 巡检. 等 cc2 流量产生后再判 SR. 若 dsv4p_nv 配额限流持续扩散到 glm5_2_nv 再介入.
