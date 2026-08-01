# R-nvonly-post97 — hm2 cc2 NOP 巡检轮

**日期**: 2026-08-02 06:14 CST
**轮次**: R-nvonly-post97 (NOP 巡检轮)
**改动**: 0 (不改码, 不重启)

## 轮前链路分析 (注入数据, 06:12:32 CST)

### 30min caller × model × status
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 429 | 6 |

### 30min 按模型 SR
- dsv4p_nv: SR=0.0% (0/6) — hermes caller, 非 cc2 链路

### 30min cc2 (cc4101-primary) 专属
- 0 req (session 轮前无流量产生)

### 30min 错误分类
- all_tiers_exhausted|all_tiers_failed_in_mapped_tier|6|avg_dur 1354s

### 30min fallback 发生率
- f=6 (dsv4p 全挂 fallback ms, hermes caller)

### 30min dsv4p 按分钟趋势 (UTC)
| 分钟 | status | count |
|------|--------|-------|
| 21:45 | 429 | 1 |
| 21:50 | 429 | 1 |
| 21:55 | 429 | 1 |
| 22:00 | 429 | 1 |
| 22:05 | 429 | 1 |
| 22:10 | 429 | 1 |

周期性 5min 一发 429, NVCF 侧 dsv4p 限流, 非 cc2 链路.

## 健康验证 (06:14 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw `/health` | status=ok, nv_default_model=glm5_2_nv, nv_num_keys=5, pexec=[kimi_nv,dsv4p_nv,glm5_2_nv] ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 4h, ms_gw/logs_db Up 2d ✓ |
| cc2 (cc4101-primary) 30min | 0 req (无流量) |
| cc2 tier error 30min | 0 (DB 实测) |
| stream_total_deadline 6h | 0 (基线) |

## 三阈值判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 SR | 0 req (无流量) | — (无数据, 链路健康无故障) |
| 新错误类型 | 无 (0 cc2 tier error) | ✅ |
| transport 层 | 0 错误 (无 cc2 流量) | ✅ |
| buffer 触发 | 无 (cc2 0 req) | ✅ |
→ **NOP 巡检轮**, 不改码, 不重启.

## 分析
- cc2 (cc4101-primary) 30min 0 req: session 轮前无流量产生, 无数据可判 cc2 SR.
- 链路健康无故障: 容器全 Up, /health ok, 0 cc2 tier error, 0 stream_total_deadline.
- hermes|dsv4p_nv 6×429 (all_tiers_exhausted): NVCF 侧 dsv4p 限流, 周期性 5min 一发,
  5key 全挂触发 fallback ms (fallback 已恢复, 正常工作). **与 cc2 无关** (cc2 走 glm5_2_nv).
- 与 post96 对比: dsv4p_nv 从 SR=37.5%(3/8) 恶化到 0%(0/6), 但仍局限 hermes+dsv4p, 未扩散到 glm5_2_nv.

## 下一步
- 继续 NOP 巡检. 等 cc2 有流量时再判 SR.
- 关注 dsv4p_nv 周期性 429 是否扩散到 glm5_2_nv (目前未扩散).

## 参数快照 (06:09 CST 实测, 未变化)
| 参数 | 值 |
|------|-----|
| nv_gw.UPSTREAM_TIMEOUT | 90 |
| nv_gw.TIER_COOLDOWN_S | 180 |
| nv_gw.TIER_TIMEOUT_BUDGET_S | 180 |
| nv_gw.KEY_COOLDOWN_S | 30 |
| nv_gw.NVU_DISABLE_MS_FALLBACK | 0 (fallback 已恢复) |
| nv_gw.NVU_BUFFER_CALLERS | cc4101-primary,openclaw2 |
| cc4101.CC4101_STREAM_TOTAL_DEADLINE_S | 470 |
| cc4101.PRIMARY_HEADER_TIMEOUT | 400 |
| cc4101.FALLBACK_UPSTREAM_URL | ms_gw:40007 (fallback 已恢复) |
