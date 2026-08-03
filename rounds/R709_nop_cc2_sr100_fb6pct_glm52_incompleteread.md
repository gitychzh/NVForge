# R709 — NOP 巡检轮 (cc2 SR 100%, fallback 6.3%<10%)

> 日期: 2026-08-03 19:15 CST
> 上轮: R708 (NOP, cc2 60min零流量)
> 容器: nv_gw Up 3h, cc4101 Up 4h, dsv4p_nv40066 Up 4h, nv_gw_stable Up 41h, logs_db Up 4d

## 本轮改动: 不改码 (NOP)

## 依据 (30min 窗口实测 ~18:45-19:15 CST = 15:00-15:30 UTC)

### cc2 (cc4101) 真实可见 — 100% SR ✅
- **cc_requests 30min**: 16req 全 200, SR **100%**
- **fallback 触发率**: 6.3% (1/16, fallback→dsv4p_nv40066, 也 200) < 10% 目标 ✅
- **primary**: 15/16 走 glm5_2_nv→nv_gw, 全 200
- **fallback**: 1/16 走 dsv4p_nv40066, 200
- **延迟**: max_dur=101s, avg=42s, 无 stream_total_deadline 超时 (6h 0行)
- 15:20 那条 fallback (duration=36360ms) — primary 失败后 dsv4p 兜底成功

### nv_gw 全量 30min (按 caller)
- hermes: 29/38 = 76.3% (29×dsv4p 200 + 1×glm5_2 200 vs 2×dsv4p 502 + 7×glm5_2 502)
- openclaw: 17/17 = 100% (全 dsv4p_nv 200)
- caller=cc4101-primary 在 nv_requests 中零行 (cc2 请求经 cc4101 代理, 不直接记 nv_requests.caller)

### glm5_2_nv tier 不稳 (NVCF 上游间歇, 非 nv_gw 可控)
- 30min glm5_2_nv by caller: hermes 1/8 (SR 12.5%), 全 RemoteDisconnected/429
- 错误分类 (nv_requests 502):
  - NVStream_IncompleteRead ×4 — NVCF 上游 stream 中断
  - all_tiers_exhausted ×4 — glm5_2_nv 5key 全败 → 触发 cc4101 fallback
  - stream_absolute_cap ×1 — 超总预算
- tier attempts 错误:
  - NVCFPexecRemoteDisconnected ×5, IntegrateRemoteDisconnected ×4
  - pexec_conn_RemoteDisconnected ×4, 429_nv_rate_limit ×1
  - pexec_success ×1
- per-key 分布: k2(pexec fid3b9748d8)×5 + k2(integrate)×2, k1/k3(integrate)各1 — 全 0 ok, 全 RemoteDisconnected/429
- KeyMgr 快速恢复生效: 日志多次 `penalty=5s no conn_count` (k3 RemoteDisconnected)
- STREAMBREAK: 3 次 IncompleteRead, content_flushed=0~444c, ttfb_recorded=False~True → NVCF 上游 TTFB 前/中段断连

### 配置无漂移
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, buffer 5×90s=450s, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180
- per-key: NV_GLM52_KEY_FID_BIND=0:0;2:1;4:2, NV_GLM52_KEY_MODE_BIND=0:pexec_us_rr;1:integrate_us_rr;2:pexec_us_rr;3:integrate_us_rr;4:pexec_us_rr
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=dsv4p_nv→dsv4p_nv40066:40066, STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150

## 验证 (NOP 无需 restart)
- `curl /health`: nv_gw ok(5keys) + cc4101 ok + dsv4p_nv40066 ok(5keys) ✅
- `docker ps`: nv_gw Up 3h, cc4101 Up 4h, dsv4p_nv40066 Up 4h, nv_gw_stable Up 41h, logs_db Up 4d — 全 Up ✅
- 配置实测与 R661 baseline 一致, 无漂移 ✅

## 下一步
- 持续监控 cc2 流量 SR + fallback 触发率 (目标 SR99%+ fb<10%)
- glm5_2_nv tier RemoteDisconnected/429 是 NVCF 上游间歇+配额副作用, 非 nv_gw 可控
- cc4101 fallback 到 dsv4p 兜底, 用户可见 SR 100% 已达目标
- R661 post-restart ~41h+ 仍无 NVAnthCollect_IncompleteRead 再现
- 关注 fallback 率若持续上升 >10% 再深入查 glm5_2_nv tier

## 参数快照 (无变化, 沿用 R661)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, buffer 5×90s=450s, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180
  - per-key FID bind: NV_GLM52_KEY_FID_BIND=0:0;2:1;4:2 (k0/k2/k4 pexec fid1/2/3)
  - per-key mode bind: NV_GLM52_KEY_MODE_BIND=0:pexec_us_rr;1:integrate_us_rr;2:pexec_us_rr;3:integrate_us_rr;4:pexec_us_rr
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=dsv4p_nv→dsv4p_nv40066:40066, STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle
