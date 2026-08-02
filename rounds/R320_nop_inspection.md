# R320 — NOP 巡检轮 (2026-08-02 18:16 CST)

## 本轮改了什么
- 0 改动 0 restart. NOP 巡检轮.

## 依据 (轮前链路分析注入 ~18:16 CST)

### cc2 (cc4101-primary) 30min 0 req
- 同 R275-R319, session 间歇空闲, 链路空闲健康. 0 fallback 0 deadline.
- buffer/wait 日志 (BUFFER-/WAIT-) 30min 空.

### dsv4p_nv 30min 全 caller SR=92.0% (23/25)
| caller | model | status | count |
|---|---|---|---|
| hermes | dsv4p_nv | 200 | 23 |
| hermes | dsv4p_nv | 429 | 1 |
| hermes | dsv4p_nv | 502 | 1 |

per-key (dsv4p): key2 → 23×200 (avg_dur 10853) + 1×502 (33960), 空 key → 1×429 (1782).
per-egress: 203.10.96.139 → 24×96, 空 IP → 1×0 (429).
finish_reason (200): tool_calls×20, stop×3 (无 zombie).
分钟趋势: 09:50 一波 429, 09:55-10:16 恢复 23×200 (配额周期自恢复).
延迟 (200): avg_dur 10853, max 32671, min 3363, avg_ttfb 10392.
fallback 0/25.

### 错误分类 (DB 实测)
- 2 错误: 1× NVStream_IncompleteRead (502, 33960ms)
  + 1× all_tiers_exhausted (avg_dur 1782, sub=all_tiers_failed_in_mapped_tier).
- 09:50 一波 429 → 5key 同 function 同时挂 → all_tiers_exhausted.
- NVStream_IncompleteRead 单发 mid-stream 软挂, nv_breaker 未累积到 OPEN, 历史偶发非新错误类型.
- tier_attempts 30min 0 行 (429 在 NVCF 侧, 未进入 nv_gw tier 重试).
- buffer/wait 日志空.
- 错误类型集合与 R268-R319 一致.

## 根因 (沿用 R278-R319, 非代码缺陷)
- NVCF 429 配额是 function 级: function 配额耗尽时 5 key 同时收 429.
- buffer 5key 轮转对 key/IP 级 429 有效, 对 function 级 429 是已知设计盲区.
- 本轮 09:50 一波 429 证明是 NVCF function 配额周期自恢复, 非 nv_gw 代码缺陷.
- KEYMGR 指数退避 (120→180→480s) 正常, ProbeWorker 探测唤醒恢复.
- NVStream_IncompleteRead 单发 mid-stream 软挂, nv_breaker 未 OPEN, 自恢复.

## 健康检查 (本轮 curl 确认)
- /health 200, nv_num_keys=5, default glm5_2_nv, pexec_models=[kimi_nv, dsv4p_nv, glm5_2_nv].
- 容器全 Up: nv_gw/cc4101 Up 4h, ms_gw/logs_db Up 3d.

## 判稳
- **NOP 巡检轮**. cc2 primary 0 req, 链路空闲健康, 0 fallback 0 deadline.
- dsv4p_nv 本轮 SR=92.0% (23/25) (窗口命中 1 波 429 + 1 IncompleteRead, NVCF function 配额周期; 总 req 25 少, SR 数值受窗口影响但根因不变).
- 错误类型无新增, 与 R268-R319 一致.
- 五十三轮一致 R268-R320.

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv SR.
- 关注是否出现新错误类型 (非 all_tiers_exhausted/NVStream_IncompleteRead) 或 key/IP 级故障, 再决定是否介入.

## 参数快照 (无变化, 同 R319)
- cc4101: PRIMARY_UPSTREAM_MODEL=dsv4p_nv, FALLBACK_UPSTREAM_URL=ms_gw:40007, CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400.
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, UPSTREAM_TIMEOUT=90, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv.
