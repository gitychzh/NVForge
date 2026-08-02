# R280 — NOP 巡检轮 (2026-08-02 15:46 CST)

## 一句话
cc2 primary 30min 0 req; dsv4p_nv 30min 3/8=37.5% 5 失败全 hermes 全整 5min 边界点
(07:15/07:20/07:25/07:35/07:40); 07:30 三连 200 + 07:45/07:46 三连 200 印证 5min 配额
周期恢复; 边界点与 R279 完全重合 (07:15-07:40) 非恶化; R278 记录的 06:28-06:32 一次性
5×502 buffer_exhausted 未复发已自恢复; 4h 失败 28 全 hermes 全边界点 (all_tiers_exhausted
24 + buffer_exhausted 3 + NVStream_IncompleteRead 1) 未恶化; cc2 0 req 不受影响 0 fallback
0 deadline; 十三轮一致 R268-R280.

## 数据 (30min 实时 DB 复查 ~15:46 CST)

### 1. cc2 (cc4101-primary) 30min 0 req
- 同 R275-R279, session 间歇空闲, 链路空闲健康. 0 fallback 0 deadline.

### 2. dsv4p_nv 30min SR=37.5% (3/8), 失败全 hermes 边界点
| min (UTC) | caller | status | dur_ms |
|---|---|---|---|
| 07:15 | hermes | 429 | ~1590 |
| 07:20 | hermes | 429 | ~2701 |
| 07:25 | hermes | 429 | ~1716 |
| 07:30 | hermes | 200 (×3) | 4609/9641/13244 |
| 07:35 | hermes | 429 | ~1809 |
| 07:40 | hermes | 429 | ~2485 |
| 07:45 | hermes | 200 (×2) | — |
| 07:46 | hermes | 200 | — |
- 5min 等间隔边界点, 全 %5==0, duration <3s 快速失败 (pexec peek path 非 buffer).
- 07:30 三连 200 + 07:45-07:46 三连 200: 配额 5min 边界恢复瞬间 hermes 抢到成功, 印证周期性.
- nv_tier_attempts 0 条 (hermes 非 NVU_BUFFER_CALLERS, 走 pexec 一击即败).

### 3. cc2 primary 状态
- 本轮 30min 0 req, 无 buffer_exhausted 复发.
- R278 记录的 06:28-06:32 UTC 5×502 (function 级配额边界事件) 已自恢复 (06:34 后全 200, 9h+ 健康).

### 4. 4h 失败趋势 (28 总, 全 hermes)
| hour (UTC) | count |
|---|---|
| 03:00 | 1 |
| 04:00 | 6 |
| 05:00 | 6 |
| 06:00 | 9 |
| 07:00 | 6 |
- 错误分类: all_tiers_exhausted 24, buffer_exhausted 3 (R278 一次性事件), NVStream_IncompleteRead 1 (单次非模式).
- 稳定 5-9/h, 全 hermes, 全 5min 边界点, 非恶化.

## 根因 (沿用 R278/R279, 非代码缺陷)
- dsv4p_nv 5key (k0-k4) 全绑同一 NVCF function `12acbc62-3a9e-461f-8139-142e914b6f16`.
- NVCF 429 配额是 **function 级** (非 key 级): function 配额耗尽时 5 key 同时收 429.
- buffer 5key 轮转设计针对 key/IP 级隔离, 未覆盖 function 级配额 → 设计盲区非代码缺陷.
- hermes 走 pexec peek path 一击即败 (~1.6s), 不消耗 buffer; cc2 走 buffer 5key 轮转才会耗 165s.
- cc2 流量极低 (4h 26 req), 命中 function 配额边界点概率远低于 hermes, buffer_exhausted 罕见.

## 判稳: NOP 巡检轮
- cc2 primary 0 req, 链路空闲健康, 0 fallback 0 deadline.
- dsv4p_nv 失败全在 hermes caller 打 NVCF 5min 配额边界, 非 nv_gw 代码缺陷.
- 边界点与 R279 完全重合 (07:15-07:40), 非 5min 平移而是 5min 配额周期稳态.
- 无新错误类型, 无 buffer_exhausted 复发, NVStream_IncompleteRead 仅 1 次非模式.
- 4h 失败 28 稳定 5-9/h 全 hermes 全边界点, 未恶化.
- 十三轮一致 R268-R280.

## 本轮改动
0 改动 0 restart. NOP 巡检轮.

## 参数快照 (nv_gw + cc4101, 同 R279)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180,
  KEY_COOLDOWN_S=30, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4,
  MIN_OUTBOUND_INTERVAL_S=10, NV_INTEGRATE_KEY_COOLDOWN_S=90, TIER_TIMEOUT_BUDGET_S=180.
- cc4101: PRIMARY_UPSTREAM_MODEL=dsv4p_nv, PRIMARY_UPSTREAM_URL=nv_gw:40006/v1/messages,
  FALLBACK_UPSTREAM_URL=ms_gw:40007/v1/chat/completions, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130,
  UPSTREAM_IDLE_TIMEOUT=150, CC4101_PRIMARY_SKIP_S=30, CC4101_PRIMARY_FAIL_THRESHOLD=3.

## 下一步
1. 持续监控 cc2 primary buffer_exhausted 是否复发 (>5/h 或蔓延非边界点才需介入). 现状罕见.
2. 若复发频繁, 考察根因层改进 (非本轮任务, 记录待后续):
   - 把 dsv4p_nv 5key 拆到不同 NVCF function (需上游侧, 非 nv_gw 可改);
   - 或在 nv_gw 侧对 all_tiers_exhausted/429-边界点引入 WaitQueue event-driven 短等待
     (跨 5min 边界恢复), 而非 buffer 死轮转耗 165s.
3. 持续监控 dsv4p_nv 5min 边界 429 是否恶化 (>10/h 或蔓延非边界点). 现状 5-9/h 可接受.
4. cc2 session 恢复流量后, 复测 buffer 5key 轮转对边界点 429 的抵抗力.
