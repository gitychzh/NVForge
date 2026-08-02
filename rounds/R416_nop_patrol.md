# R416 — NOP 巡检轮 (2026-08-03 00:27 CST)

## 摘要
- **NOP 巡检轮, 0 改动 0 restart**. cc2 (cc4101-primary) 30min 0 req (session 间歇空闲, 连续第 8 轮).
- DB 快照 (00:27): dsv4p_nv 全 caller 30min SR=95.3% (41/43), 全来自非缓冲 caller hermes.
  - 41×200 全 key2 + egress 203.10.96.139, avg 12569ms (ttfb 12011, max 33184, min 5153), finish tool_calls×35 + stop×6, 无 IP 归属 fail.
  - 2×all_tiers_exhausted (avg 18748ms, 无 key/IP 归属, mapped-tier 直接失败) + 1×429 + 1×502.
  - 30min fallback: f×43 (0 fallback 发生).
  - 分钟趋势: 16:00 1×429 (限速模式), 16:09 1×502 (恢复期偶发),
    16:05-16:26 连续 22min 出 41×200.
- glm5_2_nv 30min 0 req — 无健康数据.
- 30min nv_tier_attempts: 0 行 (无缓冲 caller 流量, 无 tier 尝试日志).
- 30min nv_gw buffer/wait/keymanager 日志: 空 (无缓冲 caller 流量).
- 错误类型无新增, 与 R268-R415 一致 (**一百四十轮一致**).

## SR 趋势
- R409 25.0% → R410 37.5% → R411 68.4% → R412 82.8% → R413 88.2% → R414 91.4% → R415 92.1% → **R416 95.3% (41/43)** — 持续回升, 逼近 99% 目标.
- 仍在 NVCF function 配额波动区间, 非代码缺陷.

## 根因 (沿用 R278-R415 分析)
- 非缓冲 caller hermes mapped-tier 直接走 NVCF, function 配额瞬时空位 → 429/502 → all_tiers_exhausted.
- 5key (k0-k4) 全绑同一 NVCF function, function 级配额耗尽时多 key 同时收 429.
- buffer 5key 轮转设计针对 key/IP 级隔离, 对 function 级 429 是已知盲区.
- cc2 缓冲 caller 走 buffer 路径不走 mapped-tier, 不受影响.

## 判稳
- **NOP 巡检轮**. cc2 primary 0 req, 链路空闲健康, 0 fallback 0 deadline.
- dsv4p_nv 本轮快照 SR=95.3% (41/43), 较 R415 持续回升, 仍在 NVCF 配额波动区间.
- dsv4p 错误类型无新增 (一百四十轮一致).
- 切换 PRIMARY_UPSTREAM_MODEL 到 glm5_2_nv: cc2 缓冲 caller 0 req + glm5_2_nv 30min 0 req,
  无 buffer 路径数据支撑, 不满足"改前必有数据"铁律 → 暂不切.

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv buffer 路径行为.
- 关注新错误类型 (非 all_tiers_exhausted) 或 key/IP 级故障, 再决定是否介入.
- dsv4p_nv 小时级 SR 持续 <70% + cc2 缓冲流量恢复后再评估是否切 glm5_2_nv.

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
