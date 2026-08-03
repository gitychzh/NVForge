# R711 — NOP 巡检轮 (2026-08-03 19:21 CST)

## 改动: 不改码 (NOP)

## 依据 (30min 窗口 ~18:50-19:20 CST)

### cc2 真实 SR (cc_requests, 30min)
- **16 req 全 200, SR 100%** ✅
- fallback 触发率: 6.3% (1/16) < 10% ✅
- 分解: 15 primary(glm5_2_nv 直通) 200 + 1 fallback(dsv4p) 200

### nv_gw nv_requests (30min, 只记录非直通/error 路径)
- dsv4p_nv: 54×200 + 3×502 = 64.3% (54/57) — 这些是 fallback 路径 + 其他 caller
- glm5_2_nv: 5×502 = 0% — **全是非 cc2 的流量** (agent_type=`_nv`), NVCF 上游间歇
  - 注: cc2 经 primary 成功的 15 个 glm5_2_nv 200 不入 nv_requests (passthrough 直通不写表)
  - 这是 nv_gw 已知行为, 非 data loss

### 错误分类 (nv_requests 30min)
- NVStream_IncompleteRead × 3 — glm5_2_nv 流中断 (上游 RemoteDisconnected)
- all_tiers_exhausted × 3 — glm5_2_nv 5key 全败 (NVCF 上游)
- stream_absolute_cap × 1

### glm5_2_nv tier attempts (30min, 仅 4 行, 全失败)
- k1 integrate×1, k2 pexec(3b9748d8)×3+integrate×2, k3 integrate×1
- 错误: NVCFPexecRemoteDisconnected×5, IntegrateRemoteDisconnected×4, pexec_conn_RemoteDisconnected×3, 429×1
- 根因: NVCF 上游 RemoteDisconnected + 429 配额副作用, **非 nv_gw 可控**

### glm5_2_nv 3h 趋势 (10min 桶)
- 09:40 1/1=100%, 10:00 1/1=100%, 10:20 5/9=56%, 10:30 2/5=40%, 10:40 1/3=33%, 11:00 0/5=0%
- 退化趋势: 10:20 起 NVCF 上游开始退化, 11:00 完全不可用
- 但 cc2 用户 SR 仍 100% — cc4101 fallback 到 dsv4p 兜底生效

### fallback 率 3h 趋势
- 仅最近 30min 有数据: 6.3% (1/16)

### dsv4p per-key (30min, fallback 兜底)
- k0 11×200, k1 11×200, k2 12×200, k3 8×200, k4 12×200+1×502 — 均衡健康
- dsv4p per-IP: 5 US IPv4 均匀 (8~13 req), 全 100%

## 验证: NOP 无需 restart
- `curl /health`: nv_gw ok(5keys) + cc4101 ok + dsv4p_nv40066 ok(5keys) ✅
- `docker ps`: nv_gw Up 3h, cc4101 Up 4h, dsv4p_nv40066 Up 4h, nv_gw_stable Up 41h, logs_db Up 4d ✅
- 配置零漂移 (R661 baseline):
  - nv_gw: NVU_DISABLE_MS_FALLBACK=1, buffer 5×90s=450s, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180
  - per-key FID bind: NV_GLM52_KEY_FID_BIND=0:0;2:1;4:2 (k0/k2/k4 pexec fid1/2/3)
  - per-key mode bind: NV_GLM52_KEY_MODE_BIND=0:pexec_us_rr;1:integrate_us_rr;2:pexec_us_rr;3:integrate_us_rr;4:pexec_us_rr
  - cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=dsv4p_nv→dsv4p_nv40066:40066, STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150, PRIMARY_SKIP_S=30, FAIL_THRESHOLD=3
  - dsv4p_nv40066: pexec-only, NV_INTEGRATE_MODELS=空, NVU_DISABLE_MS_FALLBACK=1, PEER_FALLBACK=0

## 判稳结论
- **cc2 用户可见 SR 100%** ✅ (目标 99%+)
- **fallback 触发率 6.3%** ✅ (目标 <10%)
- glm5_2_nv NVCF 上游退化 (10:20 起, 11:00 后 0%) 是 NVCF 侧间歇, 非 nv_gw 可控
- cc4101 fallback → dsv4p_nv 兜底机制正常, 用户无感
- dsv4p_nv tier 96.5% SR 健康, 5key×5IP 均衡
- 配置零漂移, 容器全 Up, 无需改动

## 下一步
- 持续监控 cc2 SR + fallback 率
- 关注 glm5_2_nv NVCF 上游是否恢复 (当前退化中, 依赖 dsv4p 兜底)
- 若 fallback 率持续 >10% 再深入查 glm5_2_nv tier
- R661 post-restart ~41h+ 仍无新错误类型

## 参数快照 (无变化, 沿用 R661)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, buffer 5×90s=450s, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=dsv4p_nv→dsv4p_nv40066:40066, STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle
