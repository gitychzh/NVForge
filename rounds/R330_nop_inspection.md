# R330 — NOP 巡检轮 (2026-08-02 ~18:50 CST)

## 接棒
- 主仓已 pull: `1f1ed56 R329` (up to date).
- 本仓 master: 上轮 R329 (e358fb5) 已 push.
- 架构沿用: cc4101(dsv4p_nv) → nv_gw(40006) → NVCF.
- `NVU_DISABLE_MS_FALLBACK=0` (ms_gw fallback 已恢复, 不主动禁用).

## 本轮数据 (30min 链路分析注入 ~18:50 CST)

### 1. cc2 (cc4101-primary) 30min 0 req
- 同 R275-R329, session 间歇空闲, 链路空闲健康. 0 fallback 0 deadline.
- buffer/wait 日志 (BUFFER-/WAIT-) 30min 空 (无 buffer 流量).

### 2. dsv4p_nv 30min 全 caller SR=33.3% (3/9)
| caller | model | status | count |
|---|---|---|---|
| hermes | dsv4p_nv | 200 | 3 |
| hermes | dsv4p_nv | 429 | 6 |

per-key (dsv4p): key2 → 3×200 (avg_dur 7657); 空 key → 6×429 (2378).
per-egress: 203.10.96.139 → 3×100; 空 IP → 6×0 (429).
finish_reason (200): tool_calls×3 (无 zombie).
分钟趋势: 10:20 恢复 3×200 (配额周期自恢复), 10:21-10:45 一波 429×6 → all_tiers_exhausted.
延迟 (200): avg_dur 7657, max 10023, min 5102, avg_ttfb 7452.
fallback 0/9.

### 3. 错误分类 (DB 实测)
- 6 错误: 6× all_tiers_exhausted (sub=all_tiers_failed_in_mapped_tier, avg_dur 2378).
- 10:21-10:45 一波 429 → 5key 同 function 同时挂 → all_tiers_exhausted.
- 本轮无 NVStream_IncompleteRead (R325 有 1, 历史偶发 mid-stream 软挂单发, 非新错误类型).
- 与 R268-R329 错误类型集合一致 (all_tiers_exhausted + NVStream_IncompleteRead 历史仍存在).
- tier_attempts 30min 0 行 (429 在 NVCF 侧, 未进入 nv_gw tier 重试).
- buffer/wait 日志空.

### 4. 健康检查 (本轮 0 改动 0 restart, 沿用 R329 实测)
- /health 200: nv_num_keys=5, default glm5_2_nv, pexec_models=[kimi_nv, dsv4p_nv, glm5_2_nv].
- 容器全 Up: nv_gw/cc4101 Up 4h, nv_gw_stable Up 17h, ms_gw/logs_db Up 3d.

## 根因 (沿用 R278-R329 分析, 非本轮新发现)
- dsv4p_nv 5key (k0-k4) 全绑同一 NVCF function.
- NVCF 429 配额是 function 级: function 配额耗尽时 5key 同时收 429.
- buffer 5key 轮转设计针对 key/IP 级隔离, 未覆盖 function 级配额 → all_tiers_exhausted.
- 设计盲区非 nv_gw 代码缺陷. 10:21-10:45 一波 429×6 是 NVCF function 配额周期自恢复.
- KEYMGR 指数退避 (120→180→480s) + ProbeWorker 探测唤醒正常工作.
- 本轮 cc2 流量极低 (0 req), all_tiers_exhausted 罕见且自恢复, 不达介入阈值.

## 判稳
- **NOP 巡检轮**. cc2 primary 0 req, 链路空闲健康, 0 fallback 0 deadline.
- dsv4p_nv 本轮 SR=33.3% (3/9) (窗口命中 1 波 429×6, NVCF function 配额周期;
  总 req 9 少, 故 SR 数值偏低但根因不变).
- 错误类型无新增, 与 R268-R329 一致.
- 六十三轮一致 R268-R330.

## 改动
- 0 改动, 0 restart.

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv SR.
- 关注是否出现新错误类型 (非 all_tiers_exhausted/NVStream_IncompleteRead) 或 key/IP 级故障, 再决定是否介入.

## 参数快照 (R330, 沿用主仓 1f1ed56, 无改动)
- cc4101: FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, PRIMARY_UPSTREAM_MODEL=dsv4p_nv, UPSTREAM_TIMEOUT=130.
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180, KEY_COOLDOWN_S=30, NVU_BUFFER_MAX_RETRIES=5 (5×90s=450s), NVU_BUFFER_TOTAL_DEADLINE_S=450, NV_INTEGRATE_KEY_COOLDOWN_S=90, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2.
- deadline 链: 90s/buffer-attempt × 5 = 450s buffer < 470s cc4101 < 500s SDK idle (API_TIMEOUT_MS=600000).
