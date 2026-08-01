# R-nvonly-post103 — hm2_cc2 NOP 巡检轮 (2026-08-02)

## 时间
- 2026-08-02 06:28 CST (轮前链路分析注入时间)
- 接棒: post102 (STATE 已读, 仓库已 pull, HEAD=a1a840f up to date)

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

## 健康验证 (06:28 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw env | NVU_DISABLE_MS_FALLBACK=0, BUFFER 5×90s=450s, CALLERS=cc4101-primary,openclaw2 ✓ |
| cc4101 env | STREAM_TOTAL_DEADLINE=470, PRIMARY_HEADER_TIMEOUT=400, FALLBACK=ms_gw:40007 ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 4h, ms_gw/logs_db Up 2d ✓ |
| cc2 (cc4101-primary) 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| 30min 错误分类 | all_tiers_exhausted × 6 (全 hermes+dsv4p, 非 cc2) ✓ |
| 30min tier error | 0 rows (无 cc2 流量) ✓ |
| buffer/wait 日志 | 无 (cc2 0 req) ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

注: 直接裸探 cc4101/nv_gw `/v1/messages` 入口返回 401 (caller token 鉴权),
本 session 的工具调用本身即经 cc4101→nv_gw 链路, DB 0 req 反映本轮 30min 窗口内
无 cc2 请求落地 (session 工作阶段未产生计入该窗口的 nv 请求).

## 三阈值判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 0 req (无流量) | — (无数据, 链路健康) |
| 新错误类型 | 0 cc2 tier error | ✅ |
| transport 层 | 0 (无 cc2 流量) | ✅ |
| buffer 触发 | 无 (cc2 0 req) | ✅ |
→ **NOP 巡检轮**, 不改码, 不重启.

## 改动
0 改动, 0 重启. (NOP 巡检)

## 下一步
- 继续 NOP 巡检. 等 cc2 有流量时再判 SR.
- dsv4p_nv 低 SR (0.0%) 是 NVCF 侧 dsv4p 限流 (周期性 429 + 5key 全挂), 非 cc2 链路,
  不在本轮优化范围. 关注是否扩散到 glm5_2_nv (目前未扩散, post100-post103 持续无扩散).

## 参数快照 (2026-08-02 06:28 CST, 未变化)
- nv_gw: UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180, KEY_COOLDOWN_S=30,
  NV_INTEGRATE_KEY_COOLDOWN_S=90, TIER_TIMEOUT_BUDGET_S=180, MIN_OUTBOUND_INTERVAL_S=10,
  NVU_DISABLE_MS_FALLBACK=0, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, NVU_FORCE_STREAM_UPGRADE=0,
  NVU_BUFFER_MAX_RETRIES=5, NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90,
  NVU_BUFFER_TOTAL_DEADLINE_S=450,
  NVU_KEYMGR_429_BASE_COOLDOWN=120, NVU_KEYMGR_429_MAX_COOLDOWN=600,
  NVU_KEYMGR_CONN_BASE_COOLDOWN=30, NVU_KEYMGR_CONN_FAIL_THRESHOLD=3
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400,
  UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150, CC4101_PRIMARY_SKIP_S=30,
  CC4101_PRIMARY_FAIL_THRESHOLD=3, FALLBACK_UPSTREAM=ms_gw:40007, PRIMARY_MODEL=glm5_2_nv,
  FALLBACK_MODEL=glm5_2_ms
