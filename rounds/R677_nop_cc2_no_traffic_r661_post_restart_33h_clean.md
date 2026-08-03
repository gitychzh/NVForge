# R677 — NOP 巡检轮 (2026-08-03 17:15 CST)

## 改动: 不改码 (NOP)

## 依据 (30min 窗口实测, 轮前链路分析注入)

### cc2 链路 (cc4101-primary / glm5_2_nv)
- 30min: **0 请求** (cc2 自身无流量, 与 R672-R676 同型态)

### nv_gw 30min 总览 (全 hermes + openclaw caller → dsv4p_nv 路径)
- 200×34 + 429×1 + 502×4 = 39 req, dsv4p_nv **SR 87.2%**
  - hermes/dsv4p_nv: 200×30 + 429×1 + 502×3 (SR 90.9%)
  - openclaw/dsv4p_nv: 200×4 + 502×1 (SR 80%)
- 4 个 502 全是 `all_tiers_exhausted` (dsv4p_nv 5key 全 429), avg_dur 40810ms — **配额型**, 非 cc2 链路
- 1 个 429 (null key, 7269ms) — dsv4p_nv 单 key 配额拒绝
- per-key: k2 200×30 (9574ms avg), k3 200×4 (8302ms avg), null-key 502×4 (全挂后无 tier attempt)
- per-egress-IP: 203.10.96.139 200×30 (100%), 134.195.101.194 200×4 (100%), null 5 (0% = 全挂后无 egress)
- dsv4p 200 finish_reason: tool_calls×31 + stop×3 (无 zombie)
- fallback 发生率: f=39 (全部 hermes/openclaw→dsv4p_nv, 非 cc2 链路)
- nv_tier_attempts 30min: **0 行** (dsv4p_nv 5key 全 429 → 无 tier attempt 记录)

### 关键回归监控
- NVAnthCollect_IncompleteRead: **无再现** (R661 post-restart @08:02 UTC ~33h+ clean, 与 R676 一致)
- 无 BUFFER/WAIT/NV-ANTH-COLLECT/NV-BREAKER 日志

### 容器健康
- /health: nv_gw ok (5keys), cc4101 ok (primary glm5_2_nv), dsv4p_nv40066 ok
- docker ps: nv_gw Up ~1h, cc4101 Up ~2h, dsv4p_nv40066 Up ~2h, logs_db Up 4 days
- 配置无漂移

## 验证: NOP 无需 restart

## 下一步
- 等下一波 cc4101-primary (cc2) 流量 → 查 NV-ANTH-COLLECT-BUFRETRY 日志判断 R661 是否生效
- 若 IncompleteRead 再现仍落 502 → 深查 handlers.py 触发条件
- hermes/openclaw dsv4p_nv all_tiers_exhausted 配额型持续 → 关注 dsv4p_nv40066 fallback 路径可用性

## 参数快照 (无变化, 沿用 R661)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, buffer 5×90s=450s, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180
  - per-key FID bind: NV_GLM52_KEY_FID_BIND=0:0;2:1;4:2 (k0/k2/k4 pexec fid1/2/3)
  - per-key mode bind: NV_GLM52_KEY_MODE_BIND=0:pexec_us_rr;1:integrate_us_rr;2:pexec_us_rr;3:integrate_us_rr;4:pexec_us_rr
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=dsv4p_nv→dsv4p_nv40066:40066, STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle
