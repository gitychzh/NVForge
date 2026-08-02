# R419 — NOP 巡检轮 (2026-08-03 00:39 CST)

## 数据快照 (注入, 30min 窗口 ~16:09-16:35)
- cc2 (cc4101-primary) 30min: 0 req (session 间歇空闲, 连续第 11 轮).
- dsv4p_nv 全 caller 30min SR=90.6% (29/32) — 较 R418 95.3% 略降, 仍在 NVCF function 配额波动区间.
  - 29×200 全 key2 + egress 203.10.96.139, avg 11314ms (ttfb 10931, max 30653, min 5153),
    finish tool_calls×23 + stop×6, 无 IP 归属 fail.
  - 3×all_tiers_exhausted (avg 13041ms, mapped-tier 直接失败, 无 key/IP 归属).
  - 2×429 (16:30/16:35, 限速模式) + 1×502 (16:09, 恢复期偶发).
  - 30min fallback: f×32 (0 fallback 发生).
  - 分钟趋势: 16:09 1×502 → 16:10-16:26 连续出 29×200 → 16:30/16:35 2×429.
- glm5_2_nv 30min: 0 req — 无健康数据.
- 30min nv_tier_attempts: 0 行 (无缓冲 caller 流量, 无 tier 尝试日志).
- 30min nv_gw buffer/wait/keymanager 日志: 无 (无缓冲 caller 流量).

## 判稳
- **NOP 巡检轮, 0 改动 0 restart**.
- dsv4p_nv SR=90.6% (29/32), 较 R418 略降 4.7pp, 仍在 NVCF function 配额波动区间, 非代码缺陷.
- 错误类型无新增, 与 R268-R418 一致 (**一百四十三轮一致**).
- 0 fallback, 0 deadline 链问题.
- /health ok, nv_gw/cc4101/logs_db 容器健康 (uptime 23h/10h).

## 根因 (沿用 R278-R418 分析, 非代码缺陷)
- 非缓冲 caller hermes mapped-tier 直接走 NVCF, function 配额瞬时空位 → 429/502 → all_tiers_exhausted.
- 5key (k0-k4) 全绑同一 NVCF function, function 级配额耗尽时多 key 同时收 429 → all_tiers_exhausted.
- buffer 5key 轮转设计针对 key/IP 级隔离, 对 function 级 429 是已知盲区.
- cc2 缓冲 caller 走 buffer 路径不走 mapped-tier, 不受影响.

## dsv4p_nv SR 趋势 (近 9 轮 30min 快照, 全非缓冲 caller, cc2 0 req)
- R409 25.0% → R410 37.5% → R411 68.4% → R412 82.8% → R413 88.2% → R414 91.4% → R416 95.3% → R417 95.3% → R418 95.3% → **R419 90.6% (29/32)** — 小幅回落, 仍在高位波动区间.
- 仍在 NVCF function 配额波动区间, 非代码缺陷.
- 切换判据应以小时级 SR 为准, 非 30min 小样本.

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv buffer 路径行为.
- 关注新错误类型 (非 all_tiers_exhausted) 或 key/IP 级故障, 再决定是否介入.
- dsv4p_nv 小时级 SR 持续 <70% + cc2 缓冲流量恢复后再评估是否切换 cc4101 PRIMARY_UPSTREAM_MODEL 到 glm5_2_nv.
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
