# R309 — NOP 巡检轮 (2026-08-02 17:38 CST)

## 链路
- cc2 → cc4101(dsv4p_nv) → nv_gw(40006) → NVCF
- nv_gw: 5key(k0-k4)×5美国IP(hysteria2), buffer 5×90s=450s, WaitQueue event-driven
- ms_gw fallback 已恢复 (NVU_DISABLE_MS_FALLBACK=0), 本轮 0 fallback

## 本轮数据 (30min 实时链路分析注入 ~17:38 CST)

### cc2 (cc4101-primary) 30min 0 req
- 同 R275-R308, session 间歇空闲, 链路空闲健康. 0 fallback 0 deadline.
- buffer/wait 日志 (BUFFER-/WAIT-) 30min 空 (无 buffer 流量).

### dsv4p_nv 30min 全 caller SR=64.7% (11/17)
| caller | model | status | count |
|---|---|---|---|
| hermes | dsv4p_nv | 200 | 11 |
| hermes | dsv4p_nv | 429 | 6 |

- per-key (dsv4p): key2 → 11×200 (avg_dur 10661), 空 key → 6×429 (1630).
- per-egress: 203.10.96.139 → 11×100, 空 IP → 6×0 (429).
- finish_reason: tool_calls×10, stop×1 (无 zombie).
- 分钟趋势: 09:08-09:12 持续多波 200, 09:12/09:15/09:20/09:25/09:30/09:35 六波 429 (配额周期命中).
- 延迟 (200): avg_dur 10661, max 24567, min 4876, avg_ttfb 10431.
- fallback 0/17.

### 错误分类 (DB 实测)
- 6 错误: 全 all_tiers_exhausted (avg_dur 1630, sub=all_tiers_failed_in_mapped_tier).
- 09:12/09:15/09:20/09:25/09:30/09:35 六波 429 → 5key 同 function 同时挂 → all_tiers_exhausted.
- 与 R268-R308 错误类型集合一致 (all_tiers_exhausted 历史仍存在).
- tier_attempts 30min 0 行 (429 在 NVCF 侧, 未进入 nv_gw tier 重试).
- buffer/wait 日志空.

### 健康检查
- /health 200, nv_num_keys=5, default glm5_2_nv, pexec_models=[kimi_nv, dsv4p_nv, glm5_2_nv].
- 容器: nv_gw 16h ago (Up), cc4101 3h, ms_gw, logs_db 全部 Up.

## 根因 (沿用 R278-R308 分析, 设计盲区非代码缺陷)
- dsv4p_nv 5key 全绑同一 NVCF function. NVCF 429 配额是 function 级:
  function 配额耗尽时 5 key 同时收 429.
- buffer 5key 轮转假设 "单 key 429 切下一 key", 对 function 级 429 失效
  (5 key 全打同 function → 同时 429 → all_tiers_exhausted).
- 设计盲区非 nv_gw 代码缺陷. R-nvonly 5key 5IP 针对 key/IP 级隔离, 未覆盖 function 级配额.
- 本轮六波 429 证明是 NVCF function 配额周期自恢复, KEYMGR 指数退避 (120→180→480s) 正常,
  429 后 key 进入冷却, 配额恢复后 ProbeWorker 探测唤醒.
- 非 nv_gw 代码缺陷, 无需本轮改码.

## 判稳
- **NOP 巡检轮**. cc2 primary 0 req, 链路空闲健康, 0 fallback 0 deadline.
- dsv4p_nv 本轮 SR=64.7% (窗口末尾命中六波 429, NVCF function 配额周期, 比上轮多一波;
  总 req 17 少于上轮 32, 故 SR 数值偏低但根因不变).
- 错误类型无新增 (全 all_tiers_exhausted), 与 R268-R308 一致.
- 四十二轮一致 R268-R309.

## 改动
- 0 改动 0 restart.

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv SR.
- 关注是否出现新错误类型 (非 all_tiers_exhausted) 或 key/IP 级故障, 再决定是否介入.

## 参数快照 (无变化, 同 R308)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180,
  KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, MIN_OUTBOUND_INTERVAL_S=10,
  NVU_BUFFER_MAX_RETRIES=5 (90s×5=450s), NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4,
  NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, NVU_BUFFER_TOTAL_DEADLINE_S=450,
  NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, TIER_TIMEOUT_BUDGET_S=180,
  NVU_TIER_BUDGET_GLM5_2_NV=120.
- cc4101: FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions,
  PRIMARY_UPSTREAM_MODEL=dsv4p_nv, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130,
  UPSTREAM_IDLE_TIMEOUT=150, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  CC4101_PRIMARY_SKIP_S=30, CC4101_PRIMARY_FAIL_THRESHOLD=3.
- cc2 SDK: API_TIMEOUT_MS=600000, contextWindow=170000, autoCompactWindow=155000,
  CLAUDE_STREAM_IDLE_TIMEOUT_MS=500000.
