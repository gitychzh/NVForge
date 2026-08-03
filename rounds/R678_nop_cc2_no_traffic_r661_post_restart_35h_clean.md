# R678 — NOP 巡检轮 (2026-08-03 17:20 CST)

## 改动: 不改码 (NOP)

## 依据 (30min 窗口实测 DB)

### cc2 链路 (cc4101-primary/glm5_2_nv) — 30min 0 请求
- 连续 7 轮 (R671-R677) cc2 自身无流量, 本轮同型态
- 3h 回溯: cc4101-primary/glm5_2_nv 15×200 + 1×502 = SR 93.75% (16 req, 全在 07:00 UTC ~10h前)
- cc4101-fallback/dsv4p_nv 1×200 (07:00 UTC)
- 最近 3h (08:00-09:00+ UTC = 16:00-17:00 CST) cc2 完全无流量

### 30min 全量 (非 cc2 链路, hermes/openclaw→dsv4p_nv)
- hermes/dsv4p_nv: 200×23 + 429×3 + 502×3 = SR 79.4% (29 req)
- openclaw/dsv4p_nv: 200×1 = SR 100% (1 req)
- 合计 dsv4p_nv SR = 24/30 = 80.0% (比 R677 的 87.2% 降, 窗口漂移)
- 全部 30 req 走 dsv4p_nv40066 容器 (非 nv_gw 40006 glm5_2_nv 链路)

### 错误分类 (30min, status!=200)
- all_tiers_exhausted × 6, avg_dur 23070ms (比 R677 的 40810ms 快, 更快失败)
  - 全是 dsv4p_nv 5key 全 429 → 非 cc2 管辖 (nv_gw 40006 glm5_2_nv)

### per-key (30min, dsv4p_nv)
- k2: 200×22 (9493ms avg)
- k3: 200×1 (4139ms avg)
- null key: 429×3 (3455ms) + 502×3 (42685ms) — 全挂后无 tier attempt

### 配置无漂移
- nv_gw env: NVU_DISABLE_MS_FALLBACK=1, buffer 5×90s=450s, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180
  - NV_GLM52_KEY_FID_BIND=0:0;2:1;4:2, NV_GLM52_KEY_MODE_BIND=0:pexec_us_rr;1:integrate_us_rr;2:pexec_us_rr;3:integrate_us_rr;4:pexec_us_rr
- cc4101 env: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=dsv4p_nv→dsv4p_nv40066:40066, STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150, FAIL_THRESHOLD=3, SKIP_S=30

### 日志
- nv_gw 30m: 无 BUFFER/WAIT/NV-ANTH-COLLECT/NV-BREAKER/IncompleteRead 日志 (cc2 无流量, 正常)
- R661 修复窗口 post-restart @08:02 UTC ~35h+ 仍无 NVAnthCollect_IncompleteRead 再现

## 验证: NOP 无需 restart
- `curl /health` nv_gw ok (5keys, glm5_2_nv default), cc4101 ok, dsv4p_nv40066 ok
- `docker ps` 容器都 Up: nv_gw ~1h, cc4101 ~2h, dsv4p_nv40066 ~2h, logs_db 4 days, nv_gw_stable 39h
- 无新错误, 无配置漂移, 无 IncompleteRead 再现

## 下一步
- 等下一波 cc4101-primary (cc2) 流量 → 查 NV-ANTH-COLLECT-BUFRETRY 日志判断 R661 是否生效
- 若 IncompleteRead 再现仍落 502 → 深查 handlers.py 触发条件
- hermes/openclaw dsv4p_nv all_tiers_exhausted 配额型持续 → 关注 dsv4p_nv40066 fallback 路径可用性
- cc2 连续 7 轮无流量 → 核心正反馈循环受阻, 但无流量则无优化素材, 只能等

## 参数快照 (无变化, 沿用 R661)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, buffer 5×90s=450s, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180
  - per-key FID bind: NV_GLM52_KEY_FID_BIND=0:0;2:1;4:2 (k0/k2/k4 pexec fid1/2/3)
  - per-key mode bind: NV_GLM52_KEY_MODE_BIND=0:pexec_us_rr;1:integrate_us_rr;2:pexec_us_rr;3:integrate_us_rr;4:pexec_us_rr
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=dsv4p_nv→dsv4p_nv40066:40066, STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle
