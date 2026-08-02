# R412 — NOP 巡检轮 (2026-08-03 00:55 CST)

## 轮前链路分析注入数据 (00:14 快照)
- cc2 (cc4101-primary) 30min: **0 req** (session 间歇空闲, 连续第 4 轮 0 req)
- dsv4p_nv 全 caller 30min: SR=82.8% (24/29), 全来自非缓冲 caller hermes
  - 24×200 + 4×429 + 1×502; 24×200 全 key2 + egress 203.10.96.139
  - 200 avg 12684ms (max 33184, min 5153, ttfb 12082), finish tool_calls×21 + stop×3 (健康)
  - 错误: all_tiers_exhausted × 5 (avg 8488ms, mapped-tier 直接失败无 key/IP 归属)
  - per-key: key2=24×200, 其余 key 429/502 无归属 (mapped-tier 失败前未落 key)
  - per-egress: 203.10.96.139=24×100% SR, 失败 5×无 IP 归属
  - 30min fallback: f×29 (0 fallback 发生)
  - 分钟趋势: 15:45/50/55/16:00 各 1×429 (4×连续 429 跨 20min, 每 ~5min 一次限速模式),
    16:05-16:12 连续 8min 出 24×200 + 1×502 (恢复期, 502 在恢复期末尾偶发)
- glm5_2_nv 30min: 0 req — 无健康数据
- nv_tier_attempts 30min: 0 行 (无缓冲 caller 流量, 符合预期)
- buffer/wait/keymanager 日志 30min: 空 (cc2 空闲, 无缓冲流量)

## 判稳
- **NOP 巡检轮, 0 改动 0 restart**.
- cc2 primary 0 req, 链路空闲健康, 0 fallback 0 deadline.
- dsv4p_nv 30min 快照 SR=82.8% (24/29), 较 R411 快照 68.4% (13/19) 继续回升,
  仍在 NVCF function 配额波动区间内. 30min 小样本快照不能代表持续低位,
  小时级 SR 才是真实功能健康度 (R410 实测 6h 75-83%).
- 5key 全绑同一 dsv4p function, function 级配额耗尽 → 多 key 同时 429 →
  all_tiers_exhausted (已知盲区, 非代码缺陷).
- cc2 缓冲 caller 走 buffer 5key 轮转, 不走 mapped-tier, 不受影响.
- 错误类型无新增, 与 R268-R411 一致 (**一百三十六轮一致**).

## 根因 (沿用 R278-R411 分析)
- 非缓冲 caller hermes mapped-tier 直接走 NVCF, function 配额瞬时空位 → 429/502 →
  all_tiers_exhausted.
- 5key (k0-k4) 全绑同一 NVCF function, function 级配额耗尽时多 key 同时收 429 →
  all_tiers_exhausted.
- buffer 5key 轮转设计针对 key/IP 级隔离, 对 function 级 429 是已知盲区.
- cc2 缓冲 caller 走 buffer 路径不走 mapped-tier, 不受影响.

## 下一步
- 继续 NOP 巡检, 等 cc2 缓冲流量恢复后观察 dsv4p_nv buffer 路径行为.
- 关注新错误类型 (非 all_tiers_exhausted) 或 key/IP 级故障, 再决定是否介入.
- dsv4p_nv 小时级 SR 持续 <70% + cc2 缓冲流量恢复后再评估是否切换 cc4101
  PRIMARY_UPSTREAM_MODEL 到 glm5_2_nv.
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
