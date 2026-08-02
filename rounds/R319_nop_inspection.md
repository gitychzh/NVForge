# R319 — NOP 巡检轮 (2026-08-02 18:12 CST)

## 本轮改了什么
- 0 改动 0 restart. NOP 巡检轮.

## 依据 (轮前链路分析注入 ~18:12 CST)

### cc2 (cc4101-primary) 30min 0 req
- 同 R275-R318, session 间歇空闲, 链路空闲健康. 0 fallback 0 deadline.
- buffer/wait 日志 (BUFFER-/WAIT-) 30min 空.

### dsv4p_nv 30min 全 caller SR=86.4% (19/22)
| caller | model | status | count |
|---|---|---|---|
| hermes | dsv4p_nv | 200 | 19 |
| hermes | dsv4p_nv | 429 | 2 |
| hermes | dsv4p_nv | 502 | 1 |

per-key (dsv4p): key2 → 19×200 (avg_dur 11073) + 1×502 (33960), 空 key → 2×429 (1582).
per-egress: 203.10.96.139 → 20×95%, 空 IP → 2×0 (429).
finish_reason (200): tool_calls×16, stop×3 (无 zombie).
分钟趋势: 09:45+09:50 两波 429, 09:55-10:11 恢复 19×200 (配额周期自恢复).
延迟 (200): avg_dur 11073, max 32671, min 3834, avg_ttfb 10589.
fallback 0/22.

### 错误分类 (DB 实测)
- 3 错误: 2× all_tiers_exhausted (avg_dur 1582, sub=all_tiers_failed_in_mapped_tier)
  + 1× NVStream_IncompleteRead (502, 33960ms).
- 09:45+09:50 两波 429 → 5key 同 function 同时挂 → all_tiers_exhausted.
- NVStream_IncompleteRead 单发 mid-stream 软挂, nv_breaker 未累积到 OPEN, 历史偶发非新错误类型.
- tier_attempts 30min 0 行 (429 在 NVCF 侧, 未进入 nv_gw tier 重试).
- buffer/wait 日志空.
- 错误类型集合与 R268-R318 一致.

## 根因 (沿用 R278-R318, 非代码缺陷)
- NVCF 429 配额是 function 级: function 配额耗尽时 5 key 同时收 429.
- buffer 5key 轮转对 key/IP 级 429 有效, 对 function 级 429 是已知设计盲区.
- 本轮 09:45+09:50 两波 429 证明是 NVCF function 配额周期自恢复, 非 nv_gw 代码缺陷.
- KEYMGR 指数退避 (120→180→480s) 正常, ProbeWorker 探测唤醒恢复.
- NVStream_IncompleteRead 单发 mid-stream 软挂, nv_breaker 未 OPEN, 自恢复.

## 判稳
- **NOP 巡检轮**. cc2 primary 0 req, 链路空闲健康, 0 fallback 0 deadline.
- dsv4p_nv 本轮 SR=86.4% (19/22) (窗口命中两波 429 + 1 IncompleteRead, NVCF function 配额周期; 总 req 22 少, SR 数值偏低但根因不变).
- 错误类型无新增, 与 R268-R318 一致.
- 五十二轮一致 R268-R319.

## 验证
- /health 200: nv_num_keys=5, default glm5_2_nv, pexec=[kimi_nv, dsv4p_nv, glm5_2_nv].
- 容器全 Up: nv_gw/cc4101 Up 4h, ms_gw/logs_db Up 3d, nv_gw_stable Up 16h.

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv SR.
- 关注是否出现新错误类型 (非 all_tiers_exhausted/NVStream_IncompleteRead) 或 key/IP 级故障, 再决定是否介入.

## 参数快照 (无变化, 同 R318)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180,
  KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, MIN_OUTBOUND_INTERVAL_S=10,
  NVU_BUFFER_MAX_RETRIES=5 (90s×5=450s), NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv.
- cc4101: FALLBACK_UPSTREAM_URL=ms_gw:40007, CC4101_STREAM_TOTAL_DEADLINE_S=470,
  PRIMARY_HEADER_TIMEOUT=400, PRIMARY_UPSTREAM_MODEL=dsv4p_nv, UPSTREAM_TIMEOUT=130.
