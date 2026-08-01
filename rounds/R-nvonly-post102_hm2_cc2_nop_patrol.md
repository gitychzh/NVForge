# R-nvonly-post102 — hm2_cc2 NOP 巡检轮 (2026-08-02)

## 时间
- 2026-08-02 06:25 CST (轮前链路分析注入时间)
- 接棒: post101 (STATE 已读, 仓库已 pull, HEAD=d46760a up to date)

## 轮前链路分析 (注入数据, 30min 窗口)

### cc2 (cc4101-primary) — 0 req
本轮 30min 窗口 cc2 无请求产生 (session 轮前无流量). 无数据判 SR.
链路健康无故障: 容器全 Up, /health ok, 0 cc2 tier error, 0 buffer/wait 日志,
0 stream_total_deadline (6h).

### 其他 caller (hermes, 非 cc2 链路)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 429 | 6 |

- dsv4p_nv SR=0.0% (0/6): 6×429 (all_tiers_exhausted, 5key 全挂)
- 周期性 5min/发 429 (22:00→22:05→...→22:25), NVCF 侧 dsv4p 限流模式
- 与 cc2 无关 (cc2 走 glm5_2_nv, 不打 dsv4p_nv)
- fallback f=6 (dsv4p 全挂 fallback ms, ms_gw fallback 正常)

### 自动分析要点
- ❌ dsv4p_nv SR=0.0% (6req) — NVCF 侧 dsv4p 限流, 非 cc2 链路
- 📌 top error: all_tiers_exhausted × 6 → 5key 全挂, NVCF 侧配额/限流

## 健康验证 (06:25 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw `/health` | status=ok, nv_default_model=glm5_2_nv, nv_num_keys=5, pexec=[kimi_nv,dsv4p_nv,glm5_2_nv] ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 4h, ms_gw/logs_db Up 2d ✓ |
| cc2 (cc4101-primary) 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| stream_total_deadline (6h) | 0 ✓ |
| buffer/wait 日志 | 无 (cc2 0 req) ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## 三阈值判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 0 req (无流量) | — (无数据, 链路健康) |
| 新错误类型 | 0 cc2 tier error | ✅ |
| transport 层 | 0 (无 cc2 流量) | ✅ |
| buffer 触发 | 无 (cc2 0 req) | ✅ |
→ **NOP 巡检轮**, 不改码, 不重启.

## 改动
0 ��动, 0 重启. (NOP 巡检)

## 下一步
- 继续 NOP 巡检. 等 cc2 有流量时再判 SR.
- dsv4p_nv 低 SR (0.0%) 是 NVCF 侧 dsv4p 限流 (周期性 429 + 5key 全挂), 非 cc2 链路,
  不在本轮优化范围. 关注是否扩散到 glm5_2_nv (目前未扩散).

## 参数快照 (2026-08-02 06:25 CST, 未变化)
- nv_gw: UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180, KEY_COOLDOWN_S=30,
  NV_INTEGRATE_KEY_COOLDOWN_S=90, TIER_TIMEOUT_BUDGET_S=180, MIN_OUTBOUND_INTERVAL_S=10,
  NVU_DISABLE_MS_FALLBACK=0, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, NVU_FORCE_STREAM_UPGRADE=0
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400,
  UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150, CC4101_PRIMARY_SKIP_S=30,
  CC4101_PRIMARY_FAIL_THRESHOLD=3, FALLBACK_UPSTREAM=ms_gw:40007, PRIMARY_MODEL=glm5_2_nv
