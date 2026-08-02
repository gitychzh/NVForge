# R408 — NOP 巡检轮 (2026-08-02 23:58 CST)

## 轮前链路分析注入数据
- cc2 (cc4101-primary) 30min: **0 req** (session 间歇空闲)
- dsv4p_nv 全 caller 30min: SR=33.3% (3/9) — 显著低于 R407 快照 77.8%
  - 3×200 全 key2, egress 203.10.96.139, avg 12951ms, 无 fail IP 归属
  - 6×fail: all_tiers_exhausted (无 key/IP 归属, mapped-tier 直接失败), avg 2633ms
  - 30min fallback: f×9 (0 fallback 发生)
- 分钟趋势: 15:26 1×200, 15:30 2×200, 15:31/35/40/45/50/55 各 1×429 (5×连续 429 跨 25min)
- 无 buffer/wait 日志 (cc2 空闲, 无缓冲流量)

## 判稳
- **NOP 巡检轮, 0 改动 0 restart**.
- cc2 primary 0 req, 链路空闲健康, 0 fallback 0 deadline.
- dsv4p_nv 本轮 SR=33.3% 下滑属 NVCF dsv4p function 配额波动谷底 (5×连续 429 跨 25min), 非代码缺陷.
- 5key 全绑同一 dsv4p function, function 级配额耗尽 → 多 key 同时 429 → all_tiers_exhausted (已知盲区).
- cc2 缓冲 caller 走 buffer 5key 轮转, 不走 mapped-tier, 不受影响.
- 错误类型无新增, 与 R268-R407 一致 (**一百三十二轮一致**).
- /health ok, 容器全 Up (nv_gw 9h, cc4101 9h, ms_gw 3d, logs_db 3d; nv_gw_stable 22h).

## 改动
- 无 (NOP).

## 验证
- 无改动 → 无 restart/编译验证.
- /health: {"status":"ok","nv_num_keys":5,"nvcf_pexec_models":["kimi_nv","dsv4p_nv","glm5_2_nv"]}
- docker ps: nv_gw/cc4101/ms_gw/logs_db/nv_gw_stable 全 Up.

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv buffer 路径行为.
- 关注新错误类型 (非 all_tiers_exhausted) 或 key/IP 级故障, 再决定是否介入.
- dsv4p_nv SR 持续低位 (连续多轮 <60%) 再评估是否切换 cc4101 PRIMARY_UPSTREAM_MODEL 到 glm5_2_nv.
- all_tiers_exhausted 持续 >=5/h 再评估 buffer/KeyManager 参数.

## 参数快照 (本轮未改)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180,
  TIER_COOLDOWN_S=180, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90,
  MIN_OUTBOUND_INTERVAL_S=10, NVU_FORCE_STREAM_UPGRADE=0,
  NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv,
  NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- cc4101: PRIMARY_UPSTREAM_MODEL=dsv4p_nv, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages,
  FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  PRIMARY_HEADER_TIMEOUT=400, CC4101_STREAM_TOTAL_DEADLINE_S=470,
  CC4101_PRIMARY_FAIL_THRESHOLD=3, CC4101_PRIMARY_SKIP_S=30,
  UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150
- deadline 链: 90s/attempt × 5 = 450s buffer < 470s cc4101 < 500s SDK idle
- settings.json: contextWindow=170000, autoCompactWindow=155000, API_TIMEOUT_MS=600000
