# R350 — NOP 巡检轮 (cc2 0req, dsv4p_nv SR=93.5% 29/31, 根因不变)

## 元
- 轮号: R350 (NOP 巡检轮)
- 时间: 2026-08-02 20:21 CST
- 上轮: R349 (a5fc07d, cc2 仓已 push; hermes 仓 R348 8e1a41b)
- 方向: R-nvonly (HM2 nv_gw 40006, ms_gw fallback 已恢复不主动禁用)

## 本轮改动
- 0 改动 0 restart. NOP 巡检轮.

## 数据依据 (30min 链路分析注入 ~20:21 CST)

### cc2 (cc4101-primary) 30min
- 0 req (session 间歇空闲, 同 R275-R349). 0 fallback 0 deadline.
- buffer/wait 日志 (BUFFER-/WAIT-) 30min 空 (无 buffer 流量).

### dsv4p_nv 30min 全 caller (hermes) SR=93.5% (29/31)
| caller | model | status | count |
|---|---|---|---|
| hermes | dsv4p_nv | 200 | 29 |
| hermes | dsv4p_nv | 429 | 1 |
| hermes | dsv4p_nv | 502 | 1 |

- per-key (dsv4p): key2 → 29×200 (avg_dur 10192) + 1×502 (35151); 空 key → 1×429 (4887).
- per-egress: 203.10.96.139 → 30 (含 29×200 + 1×502); 空 IP → 1×429.
- finish_reason (200): tool_calls×25, stop×4 (无 zombie).
- 分钟趋势: 11:55-12:01 恢复 8×200; 12:02 单发 502; 12:06-12:16 恢复 19×200; 12:20 单发 429.
- 延迟 (200): avg_dur 10192, max 24137, min 4097, avg_ttfb 9928.
- fallback 0/31.

### 错误分类 (DB 实测)
- 2 错误: 1× all_tiers_exhausted (sub=all_tiers_failed_in_mapped_tier, avg_dur 4887) + 1× NVStream_IncompleteRead (avg_dur 35151, 502).
- 1× 429: NVCF function 级配额周期单发, key2 同时挂 → all_tiers_exhausted.
- 1× NVStream_IncompleteRead (502): transport-level 偶发单发 (R345/R347/R348/R349 出现, R346 清零, 周期低频), 不达介入阈值.
- tier_attempts 30min 0 行 (429 在 NVCF 侧, 未进 nv_gw tier 重试).
- buffer/wait 日志空.
- 与 R268-R349 错误类型集合一致.

### 健康检查 (沿用 R349, 容器无 restart)
- 容器全 Up: nv_gw/cc4101 6h, nv_gw_stable 18h, ms_gw/logs_db 3 days 持续.
- /health: status=ok, nv_num_keys=5, nv_model_tiers=[kimi_nv,dsv4p_nv,glm5_2_nv].
- 配置未变 (见参数快照).

## 根因: buffer 对 function 级 429 无保护 (设计盲区, 非代码缺陷, 沿用 R278-R349 分析)

### 现象
- dsv4p_nv 5key (k0-k4) 全绑同一 NVCF function.
- NVCF 429 配额是 function 级: function 配额耗尽时, 5 key 同时收 429.
- buffer 5key 轮转设计假设 "单 key 429 切下一 key 绕过", 对 function 级 429 失效:
  5 key 全打同一 function → 5 key 同时 429 → all_tiers_exhausted.
- 设计盲区非 nv_gw 代码缺陷. R-nvonly 5key 5IP 设计针对 key/IP 级隔离, 未覆盖 function 级配额.
- 单波 429 证明是 NVCF function 配额周期自恢复 (11:55-12:16 恢复 27×200), 非 nv_gw 代码缺陷.
- KEYMGR 指数退避 (120→180→480s) 正常工作, 429 后 key 进入冷却, 配额恢复后 ProbeWorker 探测唤醒.
- 本轮 1× NVStream_IncompleteRead (502) 是 mid-stream transport 断连偶发单发, 周期性低频不达介入阈值.

### 结论
- **非 nv_gw 代码缺陷, 无需本轮改码**. NVCF function 级配额是上游硬限制.
- buffer 5key 轮转对 key/IP 级 429 仍有效 (R268-R349 验证), 对 function 级 429 是已知盲区.
- 当前 cc2 流量极低, all_tiers_exhausted 罕见且自恢复, 不达介入阈值.
- NVStream_IncompleteRead 偶发单发不达介入阈值.

## 判稳
- **NOP 巡检轮**. cc2 primary 0 req, 链路空闲健康, 0 fallback 0 deadline.
- dsv4p_nv 本轮 SR=93.5% (29/31), 较 R349 93.1% (27/29) 基本持平 (样本极小自然变动).
- 错误类型无新增, 与 R268-R349 一致 (七十三轮一致).
- 七十三轮一致 R268-R350.

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv SR.
- 关注是否出现新错误类型 (非 all_tiers_exhausted/NVStream_IncompleteRead) 或 key/IP 级故障, 再决定是否介入.
- NVStream_IncompleteRead 若从偶发单发转为连续多发, 再评估 transport 错误分类/重试逻辑.

## 参数快照 (R350, 未变)
- cc4101: PRIMARY_UPSTREAM_URL=nv_gw:40006/v1/messages, PRIMARY_UPSTREAM_MODEL=dsv4p_nv,
  FALLBACK_UPSTREAM_URL=ms_gw:40007/v1/chat/completions, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  PRIMARY_HEADER_TIMEOUT=400, CC4101_STREAM_TOTAL_DEADLINE_S=470, UPSTREAM_TIMEOUT=130,
  UPSTREAM_IDLE_TIMEOUT=150, CC4101_PRIMARY_FAIL_THRESHOLD=3, CC4101_PRIMARY_SKIP_S=30.
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, TIER_COOLDOWN_S=180, KEY_COOLDOWN_S=30,
  NV_INTEGRATE_KEY_COOLDOWN_S=90, MIN_OUTBOUND_INTERVAL_S=10, TIER_TIMEOUT_BUDGET_S=180,
  NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4.
