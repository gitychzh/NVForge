# R322 — NOP 巡检轮 (2026-08-02 18:24 CST)

## 数据 (30min 实时链路分析注入 ~18:24 CST)

### cc2 (cc4101-primary) 30min 0 req
- session 间歇空闲, 链路空闲健康. 0 fallback 0 deadline.
- buffer/wait 日志 (BUFFER-/WAIT-) 30min 空 (无 buffer 流量).

### dsv4p_nv 30min 全 caller SR=93.5% (29/31)
| caller | model | status | count |
|---|---|---|---|
| hermes | dsv4p_nv | 200 | 29 |
| hermes | dsv4p_nv | 429 | 1 |
| hermes | dsv4p_nv | 502 | 1 |

per-key (dsv4p): key2 → 29×200 (avg_dur 10716) + 1×502 (33960), 空 key → 1×429 (7298).
per-egress: 203.10.96.139 → 30×97, 空 IP → 1×0 (429).
finish_reason (200): tool_calls×25, stop×4 (无 zombie).
分钟趋势: 09:55-10:20 恢复 29×200 (配额周期自恢复), 10:21 一波 429.
延迟 (200): avg_dur 10716, max 32671, min 3038, avg_ttfb 10291.
fallback 0/31.

### 错误分类
- 2 错误: 1× NVStream_IncompleteRead (502, 33960ms) + 1× all_tiers_exhausted (7298ms, sub=all_tiers_failed_in_mapped_tier).
- 10:21 一波 429 → 5key 同 function 同时挂 → all_tiers_exhausted.
- NVStream_IncompleteRead 单发 mid-stream 软挂, nv_breaker 未累积到 OPEN, 历史偶发非新错误类型.
- 与 R268-R321 错误类型集合一致.
- tier_attempts 30min 0 行 (429 在 NVCF 侧).
- buffer/wait 日志空.

## 根因 (沿用 R278-R321 分析)
- 429 是 NVCF function 级配额周期: function 配额耗尽时 5key 同时收 429 → all_tiers_exhausted.
- buffer 5key 轮转对 key/IP 级 429 有效, 对 function 级 429 是已知盲区 (非代码缺陷).
- KEYMGR 指数退避 (120→180→480s) 正常, 配额恢复后 ProbeWorker 探测唤醒.
- NVStream_IncompleteRead 单发 mid-stream 软挂, 自恢复, 非代码缺陷.

## 判稳
- **NOP 巡检轮**. cc2 primary 0 req, 链路空闲健康, 0 fallback 0 deadline.
- dsv4p_nv SR=93.5% (29/31) (窗口命中 1 波 429 + 1 IncompleteRead; 总 req 31 少, SR 数值偏低但根因不变).
- 错误类型无新增, 与 R268-R321 一致.
- 五十五轮一致 R268-R322.

## 改动
- 0 改动 0 restart.

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv SR.
- 关注是否出现新错误类型 (非 all_tiers_exhausted/NVStream_IncompleteRead) 或 key/IP 级故障, 再决定是否介入.

## 参数快照 (无变化, 同 R321)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180,
  KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, MIN_OUTBOUND_INTERVAL_S=10,
  NVU_BUFFER_MAX_RETRIES=5 (90s×5=450s), NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv.
- cc4101: FALLBACK_UPSTREAM_URL=ms_gw:40007, CC4101_STREAM_TOTAL_DEADLINE_S=470,
  PRIMARY_HEADER_TIMEOUT=400, PRIMARY_UPSTREAM_MODEL=dsv4p_nv, UPSTREAM_TIMEOUT=130.
