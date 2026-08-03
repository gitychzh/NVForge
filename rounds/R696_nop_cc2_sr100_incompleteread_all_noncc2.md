# R696: NOP 巡检轮 — cc2 16req 全 200 SR100% fb6.25% + NVStream_IncompleteRead×5 全非 cc2(openclaw/hermes) + R661 post-restart ~41h+ 仍无 NVAnthCollect_IncompleteRead

**Date**: 2026-08-03 18:45 CST (10:45 UTC)
**Host**: HM2 (100.109.57.26)
**Agent**: cc2 (cc4101→nv_gw:40006)
**Iron rule**: 改前必有数据 / 改后必有验证 / 聚焦 nv_gw / 所有修改写入仓库

## 改动: 不改码 (NOP)

## 依据 (30min 窗口实测 18:13-18:43 CST = 10:13-10:43 UTC)

### cc2 (cc_requests) — 目标达成 ✅
- **16req 全 200, SR 100%**, fallback 1/16 = **6.25%** (< 10% 目标 ✅)
- 1×fallback 走 dsv4p_nv (36360ms, 200)
- 15×primary glm5_2_nv 全 200 (avg 42431ms)
- 注: cc_requests.ts 有 ~5h 漂移 (容器写 CST 时间但标 UTC tag), 但 16req 数字与 R695 一致, 数据可信

### nv_gw 全量 (nv_requests, ts 正常) — 64req
- dsv4p_nv: 49×200 + 2×502 = 96.1% (49/51)
- glm5_2_nv: 8×200 + 5×502 = 61.5% (8/13) — 但**全部 5×502 非 cc2 管辖**
- agent_type 全是 `_nv` (非 cc4101-primary)

### NVStream_IncompleteRead ×5 — 全部非 cc2
- 18:23:43 (144110ms, 1614 bytes) → **openclaw** k4 integrate_us_rr
- 18:23:49 (32818ms, 1551 bytes) → **openclaw** k4 (retry)
- 18:27:44 (67218ms, 7394 bytes) → **hermes** k3
- 18:29:44 (116731ms, 0 bytes) → **hermes** k1
- 18:32:41 (124069ms, 614 bytes) → **hermes** k3

**关键特征**: 全部 content_flushed=0c, reasoning_flushed=0c, ttfb_recorded=False —
NVCF 在 TTFB 前断连, 非配置问题, 不可控

### caller 路径分析
- **CALLER_BIND**: 11×hermes(bind k3), 3×openclaw(bind k4) — 这些走固定 key
- **cc4101-primary**: 走 buffer rotation (NVU_BUFFER_CALLERS 匹配), 无 CALLER_BIND 日志
- cc2 请求在 nv_gw 走 5key 轮转 buffer, 无 IncompleteRead

### tier attempts (nv_tier_attempts)
- k0: 2×IntegrateRemoteDisconnected
- k1: 1×IntegrateRemoteDisconnected
- k2: 8×pexec_conn_RemoteDisconnected, 4×429_nv_rate_limit, 2×pexec_success
- k3: 3×integrate_success, 1×integrate_conn_RemoteDisconnected
- k4: 1×IntegrateRemoteDisconnected

### KeyManager — 快速惩罚生效
- k3/k4 RemoteDisconnected penalty=5s (no conn_count) ×7 — 快速恢复

### 其他
- 无 BUFFER-/WAIT- 日志
- R661 post-restart ~41h+ 无 NVAnthCollect_IncompleteRead 再现
- 1×stream_absolute_cap (10:30 桶, 新错误类型但单次偶发)

## 验证: NOP 无需 restart
- `curl /health`: nv_gw ok(5keys) + cc4101 ok + dsv4p_nv40066 ok(5keys)
- `docker ps`: nv_gw Up 3h, cc4101 Up 3h, dsv4p_nv40066 Up 3h, nv_gw_stable Up 41h, logs_db Up 4d — 全 Up
- 配置实测无漂移:
  - NVU_DISABLE_MS_FALLBACK=1, buffer 5×90s=450s, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180
  - NV_GLM52_KEY_FID_BIND=0:0;2:1;4:2, NV_GLM52_KEY_MODE_BIND=0:pexec_us_rr;1:integrate_us_rr;2:pexec_us_rr;3:integrate_us_rr;4:pexec_us_rr
  - cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=dsv4p_nv→dsv4p_nv40066:40066, STREAM_TOTAL=470, HEADER=400

## 下一步
- 持续监控 cc2 流量 SR + fallback 触发率 (目标 SR99%+ fb<10%)
- glm5_2_nv 全量 SR 61.5% — 但 5×502 全非 cc2, 关注是否蔓延到 cc4101-primary
- NVStream_IncompleteRead 是 NVCF 上游间歇断连, 非 nv_gw 可控
- 等 NVAnthCollect_IncompleteRead 是否再现 (R661 修复窗口 ~41h+ clean)

## 参数快照 (无变化, 沿用 R661)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, buffer 5×90s=450s, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180
  - per-key FID bind: NV_GLM52_KEY_FID_BIND=0:0;2:1;4:2 (k0/k2/k4 pexec fid1/2/3)
  - per-key mode bind: NV_GLM52_KEY_MODE_BIND=0:pexec_us_rr;1:integrate_us_rr;2:pexec_us_rr;3:integrate_us_rr;4:pexec_us_rr
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=dsv4p_nv→dsv4p_nv40066:40066, STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle
