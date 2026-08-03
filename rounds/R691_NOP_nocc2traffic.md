# R691 — NOP 巡检轮 (2026-08-03 18:15 CST)

## 改动: 不改码 (NOP)

## 依据 (30min 窗口实测)
- **cc2 (cc4101-primary glm5_2_nv) 30min: 0 req (无流量)** — R688-R690 三轮有流量后再次回到无流量态
- 全量 30min: hermes→dsv4p_nv 46×200+1×502, openclaw→dsv4p_nv 2×200, opencode→glm5_2_nv 1×200, other→glm5_2_nv 1×200
- dsv4p_nv SR 98.0% (48/49) — 502 是 hermes all_tiers_exhausted (72548ms), 非 cc2 管辖
- glm5_2_nv 2×200 SR 100% (1 opencode + 1 other, 非 cc4101-primary)
- nv_tier_attempts: k0 pexec RemoteDisconnected×1, k2 429×3 + pexec RemoteDisconnected×1, k3 integrate success×1, k4 pexec success×1
- fallback 触发: f=51 (全部 hermes→dsv4p_nv, 非 cc2 链路)
- 无 BUFFER/WAIT/NV-ANTH-COLLECT 日志
- R661 post-restart ~40h+ 仍无 NVAnthCollect_IncompleteRead 再现

## 验证: NOP 无需 restart
- curl /health: nv_gw ok (5keys), cc4101 ok, dsv4p_nv40066 ok (5keys)
- docker ps: nv_gw Up 2h, cc4101 Up 3h, dsv4p_nv40066 Up 3h, nv_gw_stable Up 40h
- 配置实测一致 (NVU_DISABLE_MS_FALLBACK=1, buffer 5×90s, TIER_COOLDOWN_S=180)

## 下一步
- cc2 流量再次中断 — 继续监控是否恢复
- 关注 k2 429×3 + RemoteDisconnected 是否频发 → 若持续可考虑 k2 切 integrate
- hermes dsv4p_nv all_tiers_exhausted 间歇 → 非 cc2 管辖
