# R-nvonly-post85 — hm2 cc2 NOP 巡检轮

**日期**: 2026-08-02 05:45 CST
**轮次**: R-nvonly-post85 (NOP 巡检)
**上轮**: R-nvonly-post84

## 判稳结论
NOP 巡检轮. cc2 (cc4101-primary) 30min 0 req (session 轮前无流量). 链路健康无故障, 0 改动, 0 重启.

## 本轮数据 (30min 窗口, 注入 + DB 实测复核)

### 1. cc4101-primary (cc2) — 0 req
```
nv_requests where caller='cc4101-primary' → (0 rows)
```
无 cc2 流量, 无数据可判 SR. 链路健康.

### 2. nv_tier_attempts (30min) — 0 行
```
nv_tier_attempts 30min → (0 rows)
```
0 cc2 tier error, 0 transport 错误.

### 3. stream_total_deadline (6h) — 0 次
```
cc_requests error_type='stream_total_deadline' 6h → (0 rows)
```
deadline 链对齐稳定.

### 4. 其他 caller (hermes, 非 cc2 链路)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 429 | 6 |

dsv4p_nv SR=0.0% (0/6): 6×429 (all_tiers_exhausted, 5key 全挂). 周期性 5min 一发 (21:10/15/20/25/30/35).
**与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv). NVCF 侧 dsv4p 限流, 非本轮优化范围.
30min fallback: f=6 (dsv4p 全挂 fallback ms, ms_gw fallback 已恢复正常工作).

## 健康验证 (05:45 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw `/health` | status=ok, nv_default_model=glm5_2_nv, nv_num_keys=5, pexec=[kimi_nv,dsv4p_nv,glm5_2_nv] ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 4h, ms_gw/logs_db Up 2d ✓ |
| cc2 tier error (30min) | 0 ✓ |
| stream_total_deadline (6h) | 0 ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## 三阈值判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 0 req (无流量) | — (无数据, 链路健康无故障) |
| 新错误类型 | 无 (0 cc2 tier error) | ✅ |
| transport 层 | 0 错误 (无 cc2 流量) | ✅ |
| buffer 触发 | 无 (cc2 0 req) | ✅ |
| stream_total_deadline (6h) | 0 次 | ✅ |
→ **NOP 巡检轮**, 不改码, 不重启.

## 改动
无 (NOP 巡检轮).

## 下一步
- 继续 NOP 巡检. 等 cc2 有流量时再判 SR.
- dsv4p_nv 低 SR (0%) 是 NVCF 侧 dsv4p 限流 (周期性 429 + 5key 全挂), 非 cc2 链路 (cc2 走 glm5_2_nv), 不在本轮优化范围.
