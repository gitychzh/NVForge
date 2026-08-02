# R337 — NOP 巡检轮 (cc2 0req, dsv4p_nv SR=90.9% 30/33, all_tiers_exhausted×3, 根因不变)

**时间**: 2026-08-02 19:21 CST
**上轮**: R336 (NOP, ae17b6d)
**本轮**: NOP 巡检轮. 0 改动 0 restart.

## 接棒
- 主仓 `git pull --ff-only origin main`: ae17b6d → 已同步.
- STATE.md 上轮 R336: cc2 primary 0 req, dsv4p_nv SR=88.9% (24/27), all_tiers_exhausted×3 + 1×502 RemoteDisconnected transport hang.

## 本轮数据 (30min 实时链路分析注入 ~19:21 CST)

### 1. cc2 (cc4101-primary) 30min 0 req
- 同 R275-R336, session 间歇空闲, 链路空闲健康. 0 fallback 0 deadline.
- buffer/wait 日志 (BUFFER-/WAIT-) 30min 空 (无 buffer 流量).

### 2. dsv4p_nv 30min 全 caller SR=90.9% (30/33)
| caller | model | status | count |
|---|---|---|---|
| hermes | dsv4p_nv | 200 | 29 |
| hermes | dsv4p_nv | 429 | 2 |
| hermes | dsv4p_nv | 502 | 1 |
| openclaw | dsv4p_nv | 200 | 1 |

per-key (dsv4p): key2 → 29×200 (avg_dur 10580); key3 → 1×200 (3310);
空 key → 2×429 (1261) + 1×502 (72299, transport-level hang, 空IP/0% — 同 R336 模式).
per-egress: 203.10.96.139 → 29×100%; 134.195.101.194 → 1×100%; 空 IP → 3×0.
finish_reason (200): tool_calls×26 + stop×4 (无 zombie).
分钟趋势: 10:55-11:16 持续 29×200 (配额自恢复周期); 11:16 2×429 + 1×502 (一波 function 级降级).
延迟 (200): avg_dur 10338, max 25900, min 3047, avg_ttfb 10000.
fallback 0/33.

### 3. 错误分类 (30min)
| error_type | sub | count | avg_dur_ms |
|---|---|---|---|
| all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 3 | 24940 |

- 3 错误 = 3× all_tiers_exhausted (2×429 + 1×502 long-dur).
- 429 (2×): NVCF function 级配额周期, 11:16 一波, key2 同时挂 → all_tiers_exhausted.
- 502 (1×, dur 72299ms): 同 R336 RemoteDisconnected transport-level hang (单发, 偶发).
- 本轮无 NVStream_IncompleteRead.
- tier_attempts 30min 0 行 (429/502 在 NVCF 侧, 未进 nv_gw tier 重试).
- buffer/wait 日志空.

### 4. 健康检查 (上轮 R336 实测, 容器时间未变)
- /health 200, nv_num_keys=5, default glm5_2_nv, pexec_models=[kimi_nv, dsv4p_nv, glm5_2_nv].
- 容器全 Up: nv_gw 17h, cc4101 5h, nv_gw_stable/ms_gw/logs_db 持续.

## 根因: buffer 对 function 级 429 无保护 (设计盲区, 非代码缺陷, 沿用 R278-R336 分析)

### 3× all_tiers_exhausted 现象
- dsv4p_nv 5key (k0-k4) 全绑同一 NVCF function.
- NVCF 429 配额是 function 级: function 配额耗尽时, 5 key 同时收 429.
- buffer 5key 轮转设计假设 "单 key 429 切下一 key 绕过", 对 function 级 429 失效:
  5 key 全打同一 function → 5 key 同时 429 → all_tiers_exhausted.
- 设计盲区非 nv_gw 代码缺陷. R-nvonly 5key 5IP 设计针对 key/IP 级隔离, 未覆盖 function 级配额.
- 11:16 一波 429 证明是 NVCF function 配额周期自恢复, 非 nv_gw 代码缺陷.
- KEYMGR 指数退避 (120→180→480s) 正常工作, 429 后 key 进入冷却, 配额恢复后 ProbeWorker 探测唤醒.
- 502 RemoteDisconnected transport hang: 同 R336, NVCF 单 function 偶发 transport 级断连, peer 也降级时返回 502 (设计). 12h 仍偶发 (本轮 1 次), 不达介入阈值.

### 结论
- **非 nv_gw 代码缺陷, 无需本轮改码**. NVCF function 级配额是上游硬限制.
- buffer 5key 轮转对 key/IP 级 429 仍有效 (R268-R336 验证), 对 function 级 429 是已知盲区.
- 当前 cc2 流量极低, all_tiers_exhausted 罕见且自恢复, 不达介入阈值.

## 判稳
- **NOP 巡检轮**. cc2 primary 0 req, 链路空闲健康, 0 fallback 0 deadline.
- dsv4p_nv SR=90.9% (30/33): 命中 1 波 429×2 + 1×502 transport hang, 总 req 少 (33) 故 SR 偏低, 根因不变.
- 错误类型无新增, 与 R268-R336 一致 (all_tiers_exhausted + 偶发 transport hang 502).
- 七十轮一致 R268-R337. 0 改动 0 restart.

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv SR.
- 关注新错误类型 (非 all_tiers_exhausted) 或 key/IP 级故障, 再介入.
- 持续观察 502 RemoteDisconnected transport hang 频次 (12h 仍偶发, 若转频发可考虑:
  (a) 让 `NVCFPexecRemoteDisconnected` 匹配 startup-retry conn-err 过滤器 (加 "RemoteDisconnected"/"Disconnected" 匹配);
  (b) 或在 pexec RemoteDisconnected 后显式调用 `_km_mark_transport` 短惩罚 + cycle 下一 key.
  改前需更多样本, 改动收益/风险比不足.)

## 参数快照 (R337, 无改动)
- cc4101: FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, PRIMARY_UPSTREAM_MODEL=dsv4p_nv, UPSTREAM_TIMEOUT=130.
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180, KEY_COOLDOWN_S=30, NVU_BUFFER_MAX_RETRIES=5 (5×90s=450s), NVU_BUFFER_TOTAL_DEADLINE_S=450, NV_INTEGRATE_KEY_COOLDOWN_S=90, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_KEYMGR_CONN_FAIL_THRESHOLD=3, NVU_KEYMGR_CONN_BASE_COOLDOWN=30, NVU_KEYMGR_CONN_MAX_COOLDOWN=60, NVU_KEYMGR_CONN_LONG_COOLDOWN=120, NVU_CONNECT_RESERVE_S=0.
- deadline 链: 90s/buffer-attempt × 5 = 450s buffer < 470s cc4101 < 500s SDK idle (API_TIMEOUT_MS=600000).
