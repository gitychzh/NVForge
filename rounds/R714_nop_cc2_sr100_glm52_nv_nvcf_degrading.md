# R714 — NOP 巡检轮 (cc2 SR100% fb6.3% glm5_2_nv NVCF上游持续退化)

**时间**: 2026-08-03 20:06 CST
**类型**: NOP 巡检 (不改码)
**触发**: 定期轮检, cc2 链路健康

## 数据 (30min 窗口 ~19:36-20:06 CST)

### cc2 (cc4101-primary) 真实 SR
- cc_requests: 16req 全 200, **SR 100%**, fallback 1/16 = **6.3%** (<10% 目标 ✅)
- primary 15 + fallback 1 (dsv4p 兜底)

### nv_gw 全量 30min (hermes/openclaw caller, 非 cc2)
| caller | model | status | count |
|---|---|---|---|
| hermes | dsv4p_nv | 200 | 24 |
| hermes | dsv4p_nv | 502 | 2 |
| hermes | glm5_2_nv | 502 | 2 |
| openclaw | dsv4p_nv | 200 | 5 |

- **dsv4p_nv**: 29×200 + 2×502 = SR **93.5%** (29/31) — 兜底链路健康
- **glm5_2_nv**: 2×502 = SR **0%** (0/2) — NVCF 上游持续退化 (10:20 起 ~10h), 非 nv_gw 可控

### 错误分类 (30min)
- all_tiers_exhausted × 4 — 5key 全挂, glm5_2_nv NVCF 上游配额副作用
- (无新错误类型)

### tier 错误 (30min)
- 空窗口 (无新 nv_tier_attempts 记录, glm5_2_nv 上游间歇无 tier attempt 到 DB)

### buffer/wait/keymanager 日志
- 无 (无 BUFFER-/WAIT-/KeyMgr 触发, 链路直接 fallback 到 dsv4p)

## 判稳 + 行动
- **cc2 SR=100% + fallback=6.3%(<10%) + 无新错误类型 → NOP 巡检轮, 不改码**
- glm5_2_nv NVCF 上游持续退化 (10:20 起 ~10h), cc4101 fallback → dsv4p 兜底正常
- 非 nv_gw 可控, 依赖 NVCF 上游恢复

## 验证 (NOP 无需 restart)
- `curl /health`:
  - nv_gw: ok, 5keys, passthrough, port 40006
  - cc4101: ok, primary=glm5_2_nv, port 4101
  - dsv4p_nv40066: ok, 5keys, passthrough, port 40066
- `docker ps`: nv_gw Up 4h, cc4101 Up 4h, dsv4p_nv40066 Up 4h, nv_gw_stable Up 42h, logs_db Up 4d — 全 Up
- 配置零漂移 (R661 baseline):
  - nv_gw: NVU_DISABLE_MS_FALLBACK=1, buffer 5×90s=450s, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180, TIER_TIMEOUT_BUDGET_S=180
  - NV_GLM52_KEY_FID_BIND=0:0;2:1;4:2, NV_GLM52_KEY_MODE_BIND=0:pexec_us_rr;1:integrate_us_rr;2:pexec_us_rr;3:integrate_us_rr;4:pexec_us_rr
  - cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=dsv4p_nv→dsv4p_nv40066:40066, STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150, PRIMARY_SKIP_S=30, FAIL_THRESHOLD=3
  - dsv4p_nv40066: pexec-only, NV_INTEGRATE_MODELS=空, NVU_DISABLE_MS_FALLBACK=1, PEER_FALLBACK=0

## 下一步
- 持续监控 cc2 SR + fallback 触发率 (目标 SR99%+ fb<10%)
- glm5_2_nv NVCF 上游持续退化中 (10:20 起 ~10h), 依赖 dsv4p 兜底, 非 nv_gw 可控
- 若 cc2 流量恢复后 fallback 率 >10% 再深入查 glm5_2_nv tier
- R661 post-restart ~42h+ 仍无新错误类型, 配置稳定

## 参数快照 (无变化, 沿用 R661)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, buffer 5×90s=450s, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180
  - per-key FID bind: NV_GLM52_KEY_FID_BIND=0:0;2:1;4:2 (k0/k2/k4 pexec fid1/2/3)
  - per-key mode bind: NV_GLM52_KEY_MODE_BIND=0:pexec_us_rr;1:integrate_us_rr;2:pexec_us_rr;3:integrate_us_rr;4:pexec_us_rr
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=dsv4p_nv→dsv4p_nv40066:40066, STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle
