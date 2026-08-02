# R335 — NOP 巡检轮 (2026-08-02 ~19:08 CST)

## 接棒
- 上轮: R334 (7875c61) 已 push, 本仓 up to date.
- 链路: cc2 → cc4101(dsv4p_nv, PRIMARY_HEADER_TIMEOUT=400) → nv_gw(40006) → NVCF.
- ms_gw fallback 已恢复 (NVU_DISABLE_MS_FALLBACK=0, cc4101 FALLBACK=ms_gw:40007), 不主动禁用.

## 数据 (30min 注入链路分析 ~19:08 CST)

### cc2 (cc4101-primary) 30min 0 req
- 同 R275-R334, session 间歇空闲, 链路空闲健康. 0 fallback 0 deadline.
- buffer/wait 日志空 (无 buffer 流量).

### dsv4p_nv 30min 全 caller SR=81.8% (18/22)
| caller | model | status | count |
|---|---|---|---|
| hermes | dsv4p_nv | 200 | 17 |
| hermes | dsv4p_nv | 429 | 3 |
| hermes | dsv4p_nv | 502 | 1 |
| openclaw | dsv4p_nv | 200 | 1 |

- per-key (dsv4p): key2 → 17×200 (avg_dur 10972, max 25900, min 3310, avg_ttfb 10167);
  key3 → 1×200 (3310); 空 key → 3×429 (avg_dur 1495, KEYMGR 阶段即拦, 无 egress) + 1×502 (72299, 60min 聚合).
- per-egress: 203.10.96.139 → 17×100% (key2 成功路径); 134.195.101.194 → 1×100% (key3);
  空 IP → 4×0 (429/502 路径无 egress).
- 分钟趋势: 10:40/45/50 每 5min 1×429 (NVCF function 配额周期)
  → 10:55-11:07 恢复 18×200 (配额自恢复).
- fallback 0/22. finish_reason: tool_calls×15 + stop×3 (200 路径正常).

### 错误分类
- top: all_tiers_exhausted × 4 (sub=all_tiers_failed_in_mapped_tier, avg_dur 19196).
  注入数据 "502×1 avg_dur 72299" 为 60min 窗口聚合; 30min 窗口内实际 4× all_tiers_exhausted (key_idx 空, egress 空).
- tier_attempts 30min 0 行 (429 在 NVCF 侧, 未进 nv_gw tier 重试).
- 错误类型集合与 R268-R334 一致, 无新增.

## 根因 (沿用 R278-R334, 不变)
- dsv4p_nv 5key 全绑同一 NVCF function. NVCF 429 配额是 function 级:
  function 配额耗尽 → 5 key 同时 429 → all_tiers_exhausted.
- buffer 5key 轮转设计针对 key/IP 级隔离, 未覆盖 function 级配额 (设计盲区, 非代码缺陷).
- 本轮 10:40-10:50 一波 429×3 → 10:55-11:07 恢复 18×200 证明是 NVCF function 配额周期自恢复.
- KEYMGR 指数退避 (120→180→480s) + ProbeWorker 15s 探测唤醒, 正常工作.

## 健康检查 (本轮 0 改动 0 restart, 沿用 R334 实测)
- /health 200, nv_num_keys=5, default glm5_2_nv, pexec_models=[kimi_nv, dsv4p_nv, glm5_2_nv].
- 容器全 Up: nv_gw/cc4101 Up 5h, nv_gw_stable Up 17h, ms_gw/logs_db Up 3d+.

## 判稳
- **NOP 巡检轮**. cc2 primary 0 req, 链路空闲健康, 0 fallback 0 deadline.
- dsv4p_nv SR=81.8% (18/22): 命中 1 波 429×3 后自恢复 18×200, 根因不变 (NVCF function 配额周期).
- 错误类型无新增, 与 R268-R334 一致.
- 六十八轮一致 R268-R335. 0 改动 0 restart.

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv SR.
- 关注新错误类型 (非 all_tiers_exhausted/NVStream_IncompleteRead) 或 key/IP 级故障, 再介入.
- 持续观察 NVStream_IncompleteRead 偶发→频发转变 (目前 60min 1 次, 仍偶发).

## 参数快照 (R335, 无改动)
- cc4101: FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, PRIMARY_UPSTREAM_MODEL=dsv4p_nv, UPSTREAM_TIMEOUT=130.
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180, KEY_COOLDOWN_S=30, NVU_BUFFER_MAX_RETRIES=5 (5×90s=450s), NVU_BUFFER_TOTAL_DEADLINE_S=450, NV_INTEGRATE_KEY_COOLDOWN_S=90, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2.
- deadline 链: 90s/buffer-attempt × 5 = 450s buffer < 470s cc4101 < 500s SDK idle (API_TIMEOUT_MS=600000).
