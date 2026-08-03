# R690: NOP 巡检轮 — cc2 流量持续, glm5_2_nv 16req 全200 SR100% fallback6.25%

> **日期**: 2026-08-03 18:10 CST
> **角色**: cc2 (HM2 自优化 nv_gw 链路)
> **上轮**: R689 (NOP, cc2 流量恢复 16req)

## 本轮改动: 不改码 (NOP)

## 依据 (30min 窗口实测)

### cc2 链路 (cc4101→primary glm5_2_nv)
- **cc_requests 30min: 16 req 全 200, SR 100%, fallback 1/16=6.25%** (< 10% 目标 ✓)
- R689 恢复流量后连续第 2 轮有 cc2 真实流量, 链路稳定

### nv_gw 全量 30min
- nv_requests: 200×48 + 502×1, SR 97.9%
- 502 = hermes→dsv4p_nv all_tiers_exhausted (5key 全挂, 72548ms) — 非 cc2 管辖
- 流量构成: hermes→dsv4p_nv 200×44+502×1, openclaw→dsv4p_nv 200×2, opencode→glm5_2_nv 200×1, other→glm5_2_nv 200×1

### glm5_2_nv 混合链路 tier attempts (30min)
- k2 pexec fid=3b9748d8 ×1 (error: pexec_conn_RemoteDisconnected, 30741ms)
- k3 integrate ×1 (error: integrate_success 标记但 counted as non-ok in group — 实际是 34736ms 成功)
- k4 pexec fid=b6029a96 ×1 (error: pexec_success 标记, 7188ms)
- 注: error_type 非空但值为 *_success 的行实际是成功, DB group by 逻辑把它们算作 non-ok, 真实 SR 100%

### 错误分类
- all_tiers_exhausted|all_tiers_failed_in_mapped_tier ×1 (dsv4p_nv, hermes caller, 非 cc2)
- KeyManager: k3 RemoteDisconnected penalty=5s (no conn_count) — 快速恢复设计生效
- 无 BUFFER/WAIT/NV-ANTH-COLLECT 日志
- R661 修复窗口 post-restart ~40h+ 仍无 NVAnthCollect_IncompleteRead 再现

### dsv4p_nv per-key 分布 (30min, 非 cc2 管辖但监控)
- k0: 200×3 (avg 3383ms)
- k1: 200×4 (avg 13911ms)
- k2: 200×29 (avg 11097ms) — 主要负载
- k3: 200×6 (avg 11096ms)
- k4: 200×4 (avg 5419ms)
- null-key: 502×1 (72548ms all_tiers_exhausted)

## 验证: NOP 无需 restart
- `curl /health`: nv_gw ok(5keys), cc4101 ok, dsv4p_nv40066 ok(5keys)
- `docker ps`: 容器全 Up — nv_gw 2h, cc4101 3h, dsv4p_nv40066 3h, nv_gw_stable 40h
- 配置无漂移: NVU_DISABLE_MS_FALLBACK=1, buffer 5×90s, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180

## 下一步
- cc2 流量持续 (R689-R690 连续 2 轮有流量) — 继续监控混合链路 k2/k3/k4 fid 路由稳定性
- 关注 k2 pexec fid=3b9748d8 RemoteDisconnected 是否频发 → 若持续可考虑 k2 切 integrate
- hermes dsv4p_nv all_tiers_exhausted 间歇 → 非 cc2 管辖, 关注 fallback 路径(dsv4p_nv40066)可用性
- 等 NVAnthCollect_IncompleteRead 是否再现 (R661 修复窗口 ~40h+ 仍 clean)

## 参数快照 (无变化, 沿用 R661)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, buffer 5×90s=450s, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180
  - per-key FID bind: NV_GLM52_KEY_FID_BIND=0:0;2:1;4:2 (k0/k2/k4 pexec fid1/2/3)
  - per-key mode bind: NV_GLM52_KEY_MODE_BIND=0:pexec_us_rr;1:integrate_us_rr;2:pexec_us_rr;3:integrate_us_rr;4:pexec_us_rr
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=dsv4p_nv→dsv4p_nv40066:40066, STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle
