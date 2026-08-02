# R410 — NOP 巡检轮 (2026-08-03 00:30 CST)

## 轮前链路分析注入数据 (00:04 快照)
- cc2 (cc4101-primary) 30min: **0 req** (session 间歇空闲)
- dsv4p_nv 全 caller 30min: SR=0.0% (0/6) — 注入快照谷底
  - 6×429 all_tiers_exhausted, 全来自非缓冲 caller hermes (mapped-tier 直走 NVCF)
  - 30min fallback: f×6 (0 fallback 发生)
- 分钟趋势: 15:35/40/45/50/55/16:00 各 1×429 (6×连续 429 跨 25min, 每 ~5min 一次)

## 自行补查数据 (00:30, 校验注入快照)
- **dsv4p_nv 6h 按小时 SR 趋势** (关键 — 推翻"持续 <60%"误判):
  - 10:00 UTC: 21/30=70% | 11:00: 34/42=81% | 12:00: 29/37=78%
  - 13:00: 35/46=76% | 14:00: 30/38=79% | 15:00: 35/42=83% | 16:00: 3/4=75%
  - **6h 全程 75-83% SR, 非持续 <60%**; 注入的 30min 0% 是小样本 (n≤8) 谷底, 非功能故障.
- 精确 30min (00:30): dsv4p_nv hermes 3×200 + 5×429 = **SR 37.5% (3/8)** (注入快照 0% 后流量部分恢复)
- glm5_2_nv 30min: 0 req — **无健康数据**, 切换模型违反"改前必有数据"铁律.
- nv_tier_attempts 30min: 0 行 (无缓冲 caller 流量, 符合预期).
- buffer/wait/keymanager 日志 30min: 空 (cc2 空闲, 无缓冲流量).
- fallback 30min: f×9 (0 fallback 发生).
- /health ok, 容器全 Up (nv_gw 10h, cc4101 10h, ms_gw 3d, logs_db 3d; nv_gw_stable 22h).

## 判稳
- **NOP 巡检轮, 0 改动 0 restart**.
- cc2 primary 0 req, 链路空闲健康, 0 fallback 0 deadline.
- dsv4p_nv 本轮快照 SR=0-37.5% 下滑属 NVCF dsv4p function 配额波动谷底
  (6×连续 429 跨 25min, 每 ~5min 一次的限速模式), 非代码缺陷.
- **关键澄清**: R407→R408→R409 STATE 记载的"连续多轮 <60%"是 30min 小样本快照谷底;
  6h 按小时 SR 实测 75-83%, 非持续低位. 不满足"持续多轮 <60%"的切换触发条件
  (该条件应以小时级 SR 为准, 非 30min 小样本).
- 5key 全绑同一 dsv4p function, function 级配额耗尽 → 多 key 同时 429 → all_tiers_exhausted (已知盲区).
- cc2 缓冲 caller 走 buffer 5key 轮转, 不走 mapped-tier, 不受影响.
- 错误类型无新增, 与 R268-R409 一致 (**一百三十四轮一致**).

## 根因 (沿用 R278-R409 分析)
- 非缓冲 caller hermes mapped-tier 直接走 NVCF, function 配额瞬时空位 → 429/502 → all_tiers_exhausted.
- 5key (k0-k4) 全绑同一 NVCF function, function 级配额耗尽时多 key 同时收 429 → all_tiers_exhausted.
- buffer 5key 轮转设计针对 key/IP 级隔离, 对 function 级 429 是已知盲区 (非代码缺陷).
- cc2 缓冲 caller 走 buffer 路径不走 mapped-tier, 不受影响.

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv buffer 路径行为.
- **修正切换触发判据**: dsv4p_nv 切换 glm5_2_nv 应以"6h 按小时 SR 持续 <60%"为准,
  而非 30min 小样本快照 (本轮证明 30min 谷底会自然回升).
- 切换前必先确认 glm5_2_nv 有 ≥10 req/30min 健康数据 (改前必有数据).
- 关注新错误类型 (非 all_tiers_exhausted) 或 key/IP 级故障, 再决定是否介入.
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
