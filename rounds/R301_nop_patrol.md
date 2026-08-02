# R301 — NOP 巡检轮 (2026-08-02 17:05 CST)

## 链路
```
cc2 → cc4101(4101, dsv4p_nv, FALLBACK=ms_gw:40007) → nv_gw(40006) → NVCF
```

## 本轮结论: NOP 巡检轮, 0 改动 0 restart

### 1. cc2 (cc4101-primary) 30min 0 req
- session 间歇空闲, 链路空闲健康. 0 fallback 0 deadline.
- 同 R275-R300.
- buffer/wait/keymanager 日志 (BUFFER-/WAIT-) 30min 空 (无 buffer 流量).

### 2. dsv4p_nv 30min 全 caller SR=95.5% (21/22)
| caller | model | status | count |
|---|---|---|---|
| hermes | dsv4p_nv | 200 | 20 |
| hermes | dsv4p_nv | 429 | 1 |
| openclaw | dsv4p_nv | 200 | 1 |

per-key (dsv4p): key2 → 20×200 + 1×429 (avg_dur 11683), key3 → 1×200 (5781).
per-egress: 203.10.96.139 → 20×100, 134.195.101.194 → 1×100.
finish_reason: tool_calls×15, stop×6 (无 zombie).
分钟趋势: 08:35-08:36 200×3 → 08:40 429×1 → 08:45-09:01 多波 200 恢复 → 09:05 200×1.
典型 NVCF function 配额周期自恢复 (429 → cooling → decay → reset → 200).

### 3. 错误分类 (DB 实测)
- 全 `all_tiers_exhausted` (1 条, all_tiers_failed_in_mapped_tier, avg_dur 1875).
- 无新错误类型, 与 R268-R300 一致.
- fallback 0/22.
- tier_attempts 30min 0 行 (function 级 429 不产生 tier attempt).
- buffer/wait 日志空.

### 4. 健康检查
- /health 200, nv_num_keys=5, default glm5_2_nv, pexec_models=[kimi_nv, dsv4p_nv, glm5_2_nv].
- 容器全 Up: nv_gw 3h, cc4101 3h, nv_gw_stable 15h, ms_gw 3 days, logs_db 3 days.

## 根因 (沿用 R278-R300 分析, 无变化)
- dsv4p_nv 5key 全绑同一 NVCF function. NVCF 429 是 function 级配额: 耗尽时 5 key 同时 429.
- buffer 5key 轮转设计针对 key/IP 级隔离, 对 function 级 429 是已知盲区 (非代码缺陷).
- 08:40 429 → 08:45-09:01 多波 200 恢复, 证明是 NVCF function 配额周期自恢复.
- 当前 cc2 流量极低, all_tiers_exhausted 罕见且自恢复, 不达介入阈值.

## 判稳
- **NOP 巡检轮**. cc2 primary 0 req, 链路空闲健康, 0 fallback 0 deadline.
- dsv4p_nv 低 SR 是 NVCF function 配额周期, 自恢复, 非 nv_gw 代码缺陷.
- 三十四轮一致 R268-R301.

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv SR.
- 关注是否出现新错误类型 (非 all_tiers_exhausted) 或 key/IP 级故障, 再决定是否介入.

## 参数快照 (无变化, 同 R300)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180,
  KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, MIN_OUTBOUND_INTERVAL_S=10,
  NVU_BUFFER_MAX_RETRIES=5 (90s×5=450s), NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4,
  NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, NVU_BUFFER_TOTAL_DEADLINE_S=450,
  TIER_TIMEOUT_BUDGET_S=180, KEY_COOLDOWN_S=30, NVU_FORCE_STREAM_UPGRADE=0,
  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
- cc4101: FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, CC4101_PRIMARY_SKIP_S=30,
  PRIMARY_UPSTREAM_MODEL=dsv4p_nv, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150, CC4101_PRIMARY_FAIL_THRESHOLD=3
