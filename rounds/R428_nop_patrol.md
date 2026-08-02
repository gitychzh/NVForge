# R428 — NOP 巡检轮 (2026-08-03 01:12 CST)

## 摘要
- NOP 巡检轮, 0 改动 0 restart. cc2 (cc4101-primary) 30min 2 req 全 200 (session 间歇空闲).
- DB 快照 (01:10): dsv4p_nv 全 caller 30min SR=54.5% (6/11).
  - cc2 primary 2×200 (R427 avg 3414ms, 本轮 buffer 路径 1 attempt success, elapsed 3279ms, 15615b flush, verdict=success_thinking, fr=stop).
  - hermes caller: 3×200 + 5×429 (mapped-tier 直接走 NVCF, function 配额空位 → all_tiers_exhausted, avg 1903ms).
  - openclaw caller: 1×200.
  - per-key (R427 快照): k0×1/k1×1/k2×3/k3×1 = 6×200; 5×429 无 key 归属.
- 30min fallback: 0 发生 (f×11 = 11 req 全 0 fallback).
- 30min nv_tier_attempts: 0 行 (cc2 缓冲 caller 2 req 直接成功不进 tier 尝试; hermes mapped-tier 不记 tier).
- 30min buffer/wait/keymanager 日志: 仅 1 条 NV-BUFFER (cc2 req cb100555), 1 attempt success.
- 错误类型无新增, 与 R268-R427 一致 (一百五十轮一致).
- 链路自恢复 (ProbeWorker + KeyManager decayed reset + buffer 5key 轮转) 持测有效.
- 容器健康: nv_gw /health=ok (11h), cc4101 (25min), ms_gw, logs_db, nv_gw_stable Up.

## 判稳
- **NOP 巡检轮**. cc2 primary 2/2 (100% SR), 链路健康, 0 fallback 0 deadline.
- dsv4p_nv 本轮快照 SR=54.5% (6/11), 与 R427 完全一致, 仍在 NVCF function 配额波动区间
  (R420=86.4%, R421=76.5%, R422=76.5%, R423=61.5%, R424=33.3%, R425=25.0%, R426=25.0%, R427=54.5%, R428=54.5%).
- dsv4p 错误类型无新增, 与 R268-R427 一致 (一百五十轮一致).
- 切换 PRIMARY_UPSTREAM_MODEL 到 glm5_2_nv 是大改: glm5_2_nv 30min 0 req,
  无 buffer 路径数据支撑, 不满足"改前必有数据"铁律 → 暂不切.

## 根因 (沿用 R278-R427, 非代码缺陷)
- 非缓冲 caller hermes mapped-tier 直接走 NVCF, function 配额瞬时空位 → 429/all_tiers_exhausted.
- 5key (k0-k4) 全绑同一 NVCF function, function 级配额耗尽时多 key 同时收 429.
- buffer 5key 轮转设计针对 key/IP 级隔离, 对 function 级 429 是已知盲区.
- cc2 缓冲 caller 走 buffer 路径不走 mapped-tier, 不受影响 (本轮 2×200 直接成功).

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv buffer 路径行为.
- 关注新错误类型 (非 all_tiers_exhausted) 或 key/IP 级故障, 再决定是否介入.
- dsv4p_nv 小时级 SR 持续 <70% + cc2 缓冲流量恢复后再评估是否切换 cc4101 PRIMARY_UPSTREAM_MODEL.
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
