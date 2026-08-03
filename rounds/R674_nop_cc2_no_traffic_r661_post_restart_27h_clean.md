# R674 — NOP 巡检轮 — cc2 链路无流量 30min 0req + cc4101真实SR100%(16/16 fb1成功) + R661修复窗口post-restart~27h仍无NVAnthCollect_IncompleteRead再现 + 30min非200全hermes/openclaw配额型(all_tiers_exhausted×4 dsv4p_nv 5key全429)非cc2链路 + nv_tier_attempts 0行 + 无BUFFER/WAIT/NV-ANTH-COLLECT日志 + /health ok 5keys 配置无漂移 容器都Up + 不改码

> 时间: 2026-08-03 17:10 CST (09:10 UTC)
> 上轮: R673 (NOP, R661 修复窗口 ~27h 无再现)
> 容器: nv_gw Up ~1h, cc4101 Up ~2h, dsv4p_nv40066 Up ~2h

## 判稳结论: NOP (不改码)

R661 (handlers.py:1853 NV-ANTH-COLLECT-BUFRETRY) restart @08:02 UTC 后 ~27h 窗口:
- cc2 (cc4101-primary/glm5_2_nv) 30min: 0 请求 (cc2 自身无流量)
- cc4101 真实 SR 30min = 100% (16/16, fb=1) — 1 次 dsv4p_nv fallback 成功覆盖
- 30min 非 200: all_tiers_exhausted×4 (hermes×3 + openclaw×1, 全 dsv4p_nv 5key 全 429, NVCF 侧配额型, 非 cc2 链路)
- nv_tier_attempts 30min: 0 行 (无 tier 级错误)
- 无 BUFFER/WAIT/NV-ANTH-COLLECT/NV-BREAKER 日志 (post-restart window clean)
- NVAnthCollect_IncompleteRead 仍无再现 → R661 修复窗口 post-restart ~27h 干净
- /health ok 5keys, 配置无漂移, 容器都 Up → NOP

## 基线 (R674 实测)
- cc2 (cc4101-primary/glm5_2_nv) nv_gw 30min: 0 req (无流量)
- cc4101 真实 SR 30min = 100% (16/16, fb=1) — 1 次 dsv4p_nv fallback 成功
- 30min 非 200: all_tiers_exhausted×4 (hermes×3/openclaw×1 dsv4p_nv 429, NVCF 配额型)
  - hermes/dsv4p_nv: 200×30 + 502×3 (SR 90.9%)
  - openclaw/dsv4p_nv: 200×4 + 502×1 (SR 80%)
- nv_tier_attempts 30min: 0 行
- NVAnthCollect_IncompleteRead: 无再现 (R661 post-restart ~27h clean)
- /health ok 5keys, 配置无漂移, 无启动错误, 容器都 Up

## 下一步
- 等下一波 cc4101-primary 流量 → 查 NV-ANTH-COLLECT-BUFRETRY 日志判断 R661 是否生效
- 若 IncompleteRead 再现仍落 502 → 深查 handlers.py:1853 触发条件是否命中
- hermes/openclaw dsv4p_nv all_tiers_exhausted 配额型持续 → 关注 dsv4p_nv40066 fallback 路径可用性 (本轮 1 次 fb 成功说明 fallback 健康)

## 参数快照 (无变化, 沿用 R661)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, buffer 5×90s=450s, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180
  - per-key FID bind: NV_GLM52_KEY_FID_BIND=0:0;2:1;4:2 (k0/k2/k4 pexec fid1/2/3)
  - per-key mode bind: NV_GLM52_KEY_MODE_BIND=0:pexec_us_rr;1:integrate_us_rr;2:pexec_us_rr;3:integrate_us_rr;4:pexec_us_rr
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=dsv4p_nv→dsv4p_nv40066:40066, STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle
