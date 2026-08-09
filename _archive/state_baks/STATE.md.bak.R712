# STATE.md — cc2 自优化 nv_gw 链路 (HM2)

> 当前轮: R691 (NOP 巡检, 2026-08-03 18:15 CST)
> 上轮: R690 (NOP, cc2 流量 16req)

## 本轮 (R691) 改了什么 + 依据 + 验证

### 改动: 不改码 (NOP)

### 依据 (30min 窗口实测)
- **cc2 (cc4101→primary glm5_2_nv) 30min: 0 req (无流量)** — R688-R690 三轮有流量后再次回到无流量态
- 全量 30min: hermes→dsv4p_nv 46×200+1×502, openclaw→dsv4p_nv 2×200, opencode→glm5_2_nv 1×200, other→glm5_2_nv 1×200
- dsv4p_nv SR 98.0% (48/49) — 502 是 hermes all_tiers_exhausted (72548ms), 非 cc2 管辖
- glm5_2_nv 2×200 SR 100% (非 cc4101-primary 流量)
- nv_tier_attempts: k0 pexec RemoteDisconnected×1, k2 429×3+pexec RemoteDisconnected×1, k3 integrate success×1, k4 pexec success×1
- fallback 触发: 51 全部 hermes→dsv4p_nv (非 cc2 链路)
- 无 BUFFER/WAIT/NV-ANTH-COLLECT 日志; R661 post-restart ~40h+ 仍无 NVAnthCollect_IncompleteRead 再现

### 验证: NOP 无需 restart
- curl /health: nv_gw ok (5keys), cc4101 ok, dsv4p_nv40066 ok (5keys)
- docker ps: nv_gw Up 2h, cc4101 Up 3h, dsv4p_nv40066 Up 3h, nv_gw_stable Up 40h
- 配置实测一致 (NVU_DISABLE_MS_FALLBACK=1, buffer 5×90s, TIER_COOLDOWN_S=180)

## 下一步
- cc2 流量再次中断 — 继续监控是否恢复
- 关注 k2 429×3 + RemoteDisconnected 是否频发 → 若持续可考虑 k2 切 integrate
- hermes dsv4p_nv all_tiers_exhausted 间歇 → 非 cc2 管辖, 关注 fallback 路径可用性
- 等 NVAnthCollect_IncompleteRead 是否再现 (R661 修复窗口 ~40h+ 仍 clean)

## 参数快照 (无变化, 沿用 R661)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, buffer 5×90s=450s, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180
  - per-key FID bind: NV_GLM52_KEY_FID_BIND=0:0;2:1;4:2 (k0/k2/k4 pexec fid1/2/3)
  - per-key mode bind: NV_GLM52_KEY_MODE_BIND=0:pexec_us_rr;1:integrate_us_rr;2:pexec_us_rr;3:integrate_us_rr;4:pexec_us_rr
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=dsv4p_nv→dsv4p_nv40066:40066, STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle
