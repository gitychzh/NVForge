# R334 — NOP 巡检轮 (2026-08-02 ~19:05 CST)

## 接棒
- 上轮: R333 (2392e36) 已 push, 本仓 up to date.
- 链路: cc2 → cc4101(dsv4p_nv, PRIMARY_HEADER_TIMEOUT=400) → nv_gw(40006) → NVCF.
- ms_gw fallback 已恢复 (NVU_DISABLE_MS_FALLBACK=0, cc4101 FALLBACK=ms_gw:40007), 不主动禁用.

## 数据 (30min 注入链路分析 ~19:05 CST)

### cc2 (cc4101-primary) 30min 0 req
- 同 R275-R333, session 间歇空闲, 链路空闲健康. 0 fallback 0 deadline.
- buffer/wait 日志空.

### dsv4p_nv 30min 全 caller SR=68.8% (11/16)
| caller | model | status | count |
|---|---|---|---|
| hermes | dsv4p_nv | 200 | 10 |
| hermes | dsv4p_nv | 429 | 4 |
| hermes | dsv4p_nv | 502 | 1 |
| openclaw | dsv4p_nv | 200 | 1 |

- per-key (dsv4p): key2 → 10×200 (avg_dur 10189, max 21379, min 3310, avg_ttfb 9269);
  空 key → 4×429 (avg_dur 1450, KEYMGR 阶段即拦, 无 egress) + 1×502 (72299, 60min 聚合).
- per-egress: 203.10.96.139 → 10×100% (key2 成功路径); 空 IP → 5×0 (429/502 无 egress).
- 分钟趋势: 10:35-10:50 一波 429×4 (每 5min 1 发, NVCF function 配额周期)
  → 10:55-10:56 恢复 5×200 → 10:58 1×502 → 11:00-11:01 恢复 5×200 → 11:05 1×200.
- fallback 0/16. finish_reason: tool_calls×9 + stop×2 (200 路径正常).

### 错误分类
- top: all_tiers_exhausted × 5 (sub=all_tiers_failed_in_mapped_tier, avg_dur 15619).
- tier_attempts 30min 0 行 (429 在 NVCF 侧, 未进 nv_gw tier 重试).
- 本轮 30min 注入窗口无 NVStream_IncompleteRead; 60min 窗口外 (10:06:55) 1 次 (历史偶发, 与 R325 同源).
- 错误类型集合与 R268-R333 一致, 无新增.

## 根因 (沿用 R278-R333, 不变)
- dsv4p_nv 5key 全绑同一 NVCF function. NVCF 429 配额是 function 级:
  function 配额耗尽 → 5 key 同时 429 → all_tiers_exhausted.
- buffer 5key 轮转设计针对 key/IP 级隔离, 未覆盖 function 级配额 (设计盲区, 非代码缺陷).
- 本轮 10:35-10:50 一波 429×4 → 10:55-11:05 恢复 11×200 证明是 NVCF function 配额周期自恢复.
- KEYMGR 指数退避 (120→180→480s) + ProbeWorker 15s 探测唤醒, 正常工作.

## 健康检查 (本轮 0 改动 0 restart, 沿用实测)
- /health 200, nv_num_keys=5, default glm5_2_nv, pexec_models=[kimi_nv, dsv4p_nv, glm5_2_nv].
- 容器全 Up: nv_gw/cc4101 Up 5h, nv_gw_stable Up 17h, ms_gw/logs_db Up 3d+.

## 判稳
- **NOP 巡检轮**. cc2 primary 0 req, 链路空闲健康, 0 fallback 0 deadline.
- dsv4p_nv SR=68.8% (11/16): 命中 1 波 429×4 后自恢复 11×200, 根因不变.
- 错误类型无新增, 与 R268-R333 一致.
- 六十七轮一致 R268-R334. 0 改动 0 restart.

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv SR.
- 关注新错误类型 (非 all_tiers_exhausted/NVStream_IncompleteRead) 或 key/IP 级故障, 再介入.
- 持续观察 NVStream_IncompleteRead 偶发→频发转变 (目前 60min 1 次, 仍偶发).

## 参数快照 (R334, 无改动)
- cc4101: FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, PRIMARY_UPSTREAM_MODEL=dsv4p_nv, UPSTREAM_TIMEOUT=130.
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180, KEY_COOLDOWN_S=30, NVU_BUFFER_MAX_RETRIES=5 (5×90s=450s), NVU_BUFFER_TOTAL_DEADLINE_S=450, NV_INTEGRATE_KEY_COOLDOWN_S=90, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2.
- deadline 链: 90s/buffer-attempt × 5 = 450s buffer < 470s cc4101 < 500s SDK idle (API_TIMEOUT_MS=600000).
