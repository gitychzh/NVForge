# R321 — NOP 巡检轮 (2026-08-02 18:20 CST)

## 基线
- 本仓 master: 上轮 R320 (a5269ca) 已 push.
- 主仓 hm2 侧: R320 (a5269ca) 已 push.
- 架构不变: cc4101 PRIMARY_UPSTREAM_MODEL=dsv4p_nv → nv_gw → NVCF.

## 本轮数据 (30min 实时链路分析注入 ~18:20 CST)

### cc2 (cc4101-primary) 30min 0 req
- 同 R275-R320, session 间歇空闲, 链路空闲健康. 0 fallback 0 deadline.
- buffer/wait 日志 (BUFFER-/WAIT-) 30min 空.

### dsv4p_nv 30min 全 caller SR=92.9% (26/28)
| caller | model | status | count |
|---|---|---|---|
| hermes | dsv4p_nv | 200 | 26 |
| hermes | dsv4p_nv | 429 | 1 |
| hermes | dsv4p_nv | 502 | 1 |

- per-key (dsv4p): key2 → 26×200 (avg_dur 11069) + 1×502 (33960), 空 key → 1×429 (1782).
- per-egress: 203.10.96.139 → 27×96, 空 IP → 1×0 (429).
- finish_reason (200): tool_calls×22, stop×4 (无 zombie).
- 分钟趋势: 09:50 一波 429, 09:55-10:16 恢复 26×200 (配额周期自恢复).
- 延迟 (200): avg_dur 11069, max 32671, min 3038, avg_ttfb 10619.
- fallback 0/28.

### 错误分类 (2 错误)
- 1× NVStream_IncompleteRead (502, 33960ms) — mid-stream 软挂单发, nv_breaker 未累积到 OPEN, 历史偶发非新错误类型.
- 1× all_tiers_exhausted (avg_dur 1782, sub=all_tiers_failed_in_mapped_tier) — 09:50 一波 429 NVCF function 配额周期 5key 同 function 同时挂 → 自恢复.
- tier_attempts 30min 0 行 (429 在 NVCF 侧未进 nv_gw tier 重试).
- 与 R268-R320 错误类型集合一致 (all_tiers_exhausted + NVStream_IncompleteRead 历史仍存在).

### 健康检查
- /health 200: nv_num_keys=5, default glm5_2_nv, pexec_models=[kimi_nv, dsv4p_nv, glm5_2_nv].
- 容器全 Up: nv_gw/cc4101 Up 4h, nv_gw_stable Up 16h, ms_gw/logs_db Up 3d.

## 根因 (沿用 R278-R320)
- 非 nv_gw 代码缺陷. NVCF function 级配额是上游硬限制.
- buffer 5key 轮转对 key/IP 级 429 有效, 对 function 级 429 是已知设计盲区 (5key 同一 function).
- 09:50 一波 429 证明是 NVCF function 配额周期自恢复, KEYMGR 指数退避 (120→180→480s) + ProbeWorker 探测唤醒正常工作.
- NVStream_IncompleteRead 单发 mid-stream 软挂, 自恢复, 非代码缺陷.

## 判稳
- **NOP 巡检轮**. cc2 primary 0 req, 链路空闲健康, 0 fallback 0 deadline.
- dsv4p_nv 本轮 SR=92.9% (26/28) (窗口命中 1 波 429 + 1 IncompleteRead, NVCF function 配额周期; 总 req 28 少, 故 SR 数值偏低但根因不变).
- 错误类型无新增, 与 R268-R320 一致.
- 五十四轮一致 R268-R321.

## 改动
- 0 改动 0 restart 0 py_compile.

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv SR.
- 关注是否出现新错误类型 (非 all_tiers_exhausted/NVStream_IncompleteRead) 或 key/IP 级故障, 再决定是否介入.

## 参数快照 (无变化, 同 R320)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180,
  KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, MIN_OUTBOUND_INTERVAL_S=10,
  NVU_BUFFER_MAX_RETRIES=5 (90s×5=450s), NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv.
- cc4101: FALLBACK_UPSTREAM_URL=ms_gw:40007, CC4101_STREAM_TOTAL_DEADLINE_S=470,
  PRIMARY_HEADER_TIMEOUT=400, PRIMARY_UPSTREAM_MODEL=dsv4p_nv, UPSTREAM_TIMEOUT=130.
