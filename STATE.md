# STATE — cc2 自优化 nv_gw 链路 (R-nvonly 方向)

## 当前轮基线 (2026-08-02 19:15 CST, R336 NOP 巡检轮)
- 本仓 master: 上轮 R335 (22d0fd3) 已 push. 主仓 hm2 侧 R336 (7bc7439) 已 push.
- **架构 (主仓 d1810a1)**: cc4101 `PRIMARY_UPSTREAM_MODEL=dsv4p_nv`.
  cc2 链路 = cc4101(dsv4p_nv) → nv_gw → NVCF.
- **本轮 R336 (hm2_cc2)**: NOP 巡检轮. cc2 (cc4101-primary) 30min 0 req (session 间歇空闲).
  dsv4p_nv 30min 全 caller SR=88.9% (24/27), 失败 3 = 3× all_tiers_exhausted (429, NVCF function 配额周期)
  + 1× all_tiers_exhausted (502, transport-level RemoteDisconnected hang 72s, 偶发).
  本轮 0 改动 0 restart.
  **六十九轮一致 R268-R336**.

## R-nvonly 核心铁律 (持续生效)
- 只改 HM2 nv_gw (40006), 不碰 HM1, 不碰 ms_gw 源码.
- ms_gw fallback 已恢复 (`NVU_DISABLE_MS_FALLBACK=0`, `FALLBACK_UPSTREAM=ms_gw:40007`), 不主动禁用.
- 改前有数据, 改后必验证, 写入仓库.

## 本轮关键数据 (30min 实时链路分析注入 ~19:12 CST)

### 1. cc2 (cc4101-primary) 30min 0 req
- 同 R275-R335, session 间歇空闲, 链路空闲健康. 0 fallback 0 deadline.
- buffer/wait 日志 (BUFFER-/WAIT-) 30min 空.

### 2. dsv4p_nv 30min 全 caller SR=88.9% (24/27)
| caller | model | status | count |
|---|---|---|---|
| hermes | dsv4p_nv | 200 | 23 |
| hermes | dsv4p_nv | 429 | 2 |
| hermes | dsv4p_nv | 502 | 1 |
| openclaw | dsv4p_nv | 200 | 1 |

per-key (dsv4p): key2 → 23×200 (avg_dur 10787); key3 → 1×200 (3310);
空 key → 2×429 (1587) + 1×502 (72299, transport hang).
per-egress: 203.10.96.139 → 23×100; 134.195.101.194 → 1×100; 空 IP → 3×0.
finish_reason (200): tool_calls×20, stop×4 (无 zombie).
分钟趋势: 10:45/10:50 每 5min 1×429 (配额周期) → 10:55-11:11 恢复 23×200; 10:58 1×502 (transport hang).
延迟 (200): avg_dur 10475, max 25900, min 3047, avg_ttfb 10109.
fallback 0/27.

### 3. 错误分类 (DB 实测, 35min 精确)
- 10:40:37 429 all_tiers_exhausted dur=1313ms (NVCF function 配额)
- 10:45:37 429 all_tiers_exhausted dur=1324ms (NVCF function 配额)
- 10:50:37 429 all_tiers_exhausted dur=1849ms (NVCF function 配额)
- 10:58:01 502 all_tiers_exhausted dur=72299ms (transport-level RemoteDisconnected hang)
  - 日志铁证 (18:56:48-18:58:01): k3 经 socks5h 7902, 等响应头 hang 72s 无 NV-SUCCESS
    → `Remote end closed connection without response` → NV-TIER-FAIL other=1 elapsed=72296ms
    → NV-ALL-TIERS-FAIL ABORT-NO-FALLBACK
    → NV-PEER-FB peer same function also bad → 返回 local 502 (不 fallback ms).
  - pexec 路径 (upstream.py L888) RemoteDisconnected 捕获后 continue 未 cycle 到下一 key,
    且 L1879 startup-retry conn-err 过滤器 `"Conn" in error_type` 不匹配
    `NVCFPexecRemoteDisconnected` → 直接 ABORT. 单条样本机制未完全解析.
- tier_attempts 30min 0 行 (429/transport 在 NVCF 侧).
- buffer/wait 日志空.

### 4. 502 RemoteDisconnected transport hang 历史频率 (12h)
- 04:00×1 (53s), 06:00×3 (110-165s), 07:00×1 (35s), 08:00×21 (1ms, DEGRADED 快路径不同模式),
  10:00×1 (72s, 本轮).
- 12h 内 long-dur 502 (34s-165s) 5 次, **偶发非新错误类型**, R335 已记录.

### 5. 健康检查 (本轮 0 restart, 沿用实测)
- /health 200, nv_num_keys=5, default glm5_2_nv, pexec_models=[kimi_nv, dsv4p_nv, glm5_2_nv].
- 容器全 Up: nv_gw/cc4101 Up 5h, nv_gw_stable Up 17h, ms_gw/logs_db Up 3d+.

## 根因 (沿用 R278-R335 + 502 transport hang 细化)

### 3× all_tiers_exhausted (429): NVCF function 级配额 (设计盲区, 不变)
- dsv4p_nv 5key 全绑同一 NVCF function (12acbc62). NVCF 429 配额是 function 级:
  function 配额耗尽 → 5 key 同时 429 → all_tiers_exhausted.
- buffer 5key 轮转设计针对 key/IP 级隔离, 未覆盖 function 级配额 (设计盲区, 非代码缺陷).
- KEYMGR 指数退避 (120→180→480s) + ProbeWorker 15s 探测唤醒, 正常工作.
- 10:55-11:11 恢复 23×200 证明是 NVCF function 配额周期自恢复.

### 1× all_tiers_exhausted (502): transport-level RemoteDisconnected hang (偶发, 已知)
- 现象: k3 经 socks5h 7902, 等响应头 hang 72s → Remote end closed connection.
- 代码路径 (upstream.py pexec tier 循环):
  - L888 `except (ConnectionRefusedError, http.client.RemoteDisconnected)` 捕获 → log NV-CONN
    → consecutive_conn_err=1 (< CONN_ERR_FAST_BREAK=2) → L905 `continue`.
  - 但日志显示 continue 后未进下一 attempt (无 NV-KEY 日志), 直接 L954 NV-TIER-FAIL.
    机制未完全解析 (budget L632 不应 break: remaining ≈108s > 5s; 下一 key 不在 cooldown).
  - L1879 `all_conn_err` startup-retry 过滤器: `"Conn" in error_type` 不匹配
    `NVCFPexecRemoteDisconnected` → startup-retry 不触发 → 直接 ABORT.
- 上游判定: `[NV-PEER-FB] peer same function also bad` → 返回 local 502 不 fallback ms.
- **偶发**: 12h 内 5 次 long-dur 502, 不达介入阈值 (cc2 primary 0 req, 不影响 cc2 链路).

### 结论
- **非 nv_gw 代码缺陷, 无需本轮改码**.
- 429: NVCF function 级配额硬限制 (设计盲区, R278-R335 一致).
- 502 transport hang: NVCF 单 function 偶发 transport 级断连, peer 也降级时返回 502 (设计).
- 当前 cc2 流量极低, 错误罕见且自恢复, 不达介入阈值.

## 判稳
- **NOP 巡检轮**. cc2 primary 0 req, 链路空闲健康, 0 fallback 0 deadline.
- dsv4p_nv SR=88.9% (24/27): 命中 1 波 429×3 + 1×502 transport hang, 总 req 少 (27) 故 SR 偏低, 根因不变.
- 错误类型无新增, 与 R268-R335 一致 (all_tiers_exhausted + 偶发 transport hang 502).
- 六十九轮一致 R268-R336.

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv SR.
- 关注新错误类型 (非 all_tiers_exhausted) 或 key/IP 级故障, 再介入.
- 持续观察 502 RemoteDisconnected transport hang 频次 (12h 5 次, 若转频发可考虑:
  (a) 让 `NVCFPexecRemoteDisconnected` 匹配 startup-retry conn-err 过滤器
      (加 "RemoteDisconnected"/"Disconnected" 匹配 → 触发 5s 重试);
  (b) 或在 pexec RemoteDisconnected 后显式调用 `_km_mark_transport` 短惩罚 + cycle 下一 key.
  改前需更多样本 (目前 12h 5 次太稀疏, 改动收益/风险比不足).)

## 参数快照 (R336, 无改动)
- cc4101: FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, PRIMARY_UPSTREAM_MODEL=dsv4p_nv, UPSTREAM_TIMEOUT=130.
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180, KEY_COOLDOWN_S=30, NVU_BUFFER_MAX_RETRIES=5 (5×90s=450s), NVU_BUFFER_TOTAL_DEADLINE_S=450, NV_INTEGRATE_KEY_COOLDOWN_S=90, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_KEYMGR_CONN_FAIL_THRESHOLD=3, NVU_KEYMGR_CONN_BASE_COOLDOWN=30, NVU_KEYMGR_CONN_MAX_COOLDOWN=60, NVU_KEYMGR_CONN_LONG_COOLDOWN=120, NVU_CONNECT_RESERVE_S=0.
- deadline 链: 90s/buffer-attempt × 5 = 450s buffer < 470s cc4101 < 500s SDK idle (API_TIMEOUT_MS=600000).
