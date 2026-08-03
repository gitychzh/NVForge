# STATE.md — cc2 自优化 nv_gw 链路 (HM2)

> 当前轮: R712 (NOP 巡检, 2026-08-03 19:27 CST)
> 上轮: R711 (NOP, cc2 16req全200 SR100% fb6.3%)

## 本轮 (R712) 改了什么 + 依据 + 验证

### 改动: 不改码 (NOP)

### 依据 (30min 窗口 ~18:57-19:27 CST)
- **cc2 (cc4101-primary) 真实 SR**: 本窗口零流量 (cc4101-primary 行空) — 无数据不动手 (铁律1)
- **dsv4p_nv 全量 SR**: 93.3% (42/45) — 全 hermes/openclaw 非 cc2 流量
  - per-key: k0/k1/k3 各 8×200, k2 10×200, k4 8×200+1×502 — 均衡健康
  - per-IP: 5 US IPv4 全 89~100%
  - 200 延迟: avg 15.5s, max 65.2s, ttfb 15.0s
- **glm5_2_nv 全量 SR**: 0% (0/6) — 全 hermes 非 cc2, NVCF 上游持续退化 (10:20 起未恢复)
- **错误分类**: all_tiers_exhausted×5, NVStream_IncompleteRead×3, stream_absolute_cap×1 — 非 cc2 管辖
- **tier 错误**: NVCFPexecRemoteDisconnected×3, IntegrateRemoteDisconnected×4, pexec_conn_RemoteDisconnected×3, 429×1 — 全 NVCF 上游配额副作用
- **fallback**: f×51 (全 hermes/openclaw, glm5_2_nv 退化→dsv4p 兜底)
- **根因**: glm5_2_nv NVCF 上游持续退化 (10:20 起), 非 nv_gw 可控; cc2 无流量无素材

### 验证: NOP 无需 restart
- `curl /health`: nv_gw ok(5keys) + cc4101 ok + dsv4p_nv40066 ok(5keys)
- `docker ps`: nv_gw Up 3h, cc4101 Up 4h, dsv4p_nv40066 Up 4h, nv_gw_stable Up 41h, logs_db Up 4d — 全 Up
- 配置零漂移 (R661 baseline)

## 下一步
- 持续监控 cc2 SR + fallback 触发率 (目标 SR99%+ fb<10%)
- glm5_2_nv NVCF 上游持续退化中, 依赖 dsv4p 兜底, 非 nv_gw 可控
- cc2 有流量后再判稳
- R661 post-restart ~41h+ 仍无新错误类型, 配置稳定

## 参数快照 (无变化, 沿用 R661)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, buffer 5×90s=450s, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180
  - per-key FID bind: NV_GLM52_KEY_FID_BIND=0:0;2:1;4:2 (k0/k2/k4 pexec fid1/2/3)
  - per-key mode bind: NV_GLM52_KEY_MODE_BIND=0:pexec_us_rr;1:integrate_us_rr;2:pexec_us_rr;3:integrate_us_rr;4:pexec_us_rr
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=dsv4p_nv→dsv4p_nv40066:40066, STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150, PRIMARY_SKIP_S=30, FAIL_THRESHOLD=3
- dsv4p_nv40066: pexec-only, NV_INTEGRATE_MODELS=空, NVU_DISABLE_MS_FALLBACK=1, PEER_FALLBACK=0
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle
