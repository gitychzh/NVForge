# R663: NOP 巡检轮 — R661 改后窗口无流量, cc2 链路持平, deadline 健康

> 时间: 2026-08-03 16:20 CST (08:12 UTC)
> 上轮: R662 (NOP, R661 collect-buffer-retry 改后窗口无流量待验)
> 容器: nv_gw Up 11min (R661 restart @08:02 UTC), cc4101 Up 59min, dsv4p_nv40066 Up 53min

## 判稳结论: NOP (不改码)

R661 (handlers.py:1853 NV-ANTH-COLLECT-BUFRETRY 块) restart @08:02 UTC 后, ~10min 窗口 cc4101-primary 流量为 0, 无法验证 collect-buffer-retry 效果。但:
- cc2 链路 60min nv_gw SR 92.9% (13/14), cc4101 SR 100% (含 1×dsv4p fallback 成功)
- 唯一 502 (c1297569 @07:20:16) 是 R661 restart **之前 42min** 的事件, 非 R661 改后回归
- deadline 链 6h stream_total_deadline=0 (健康)
- 配置无漂移, /health ok 5keys, 无启动错误
- 无新错误类型

→ 沿用 R662 判断: 等 IncompleteRead 再现 + 下一波 cc4101-primary 流量验证 R661。

## 基线 (R663 实测 60min)

### cc2 链路 (cc4101-primary → glm5_2_nv → nv_gw)
- 14req: 13×200 + 1×502 → nv_gw SR 92.9%
- cc4101 真实 SR 100% (16req, 1×fallback 到 dsv4p 成功)
- 唯一 502: c1297569 @07:20:16 NVAnthCollect_IncompleteRead 34384ms (R661 restart 前事件, 修复目标)
- avg_dur 200: 44579ms (正常, 含长 reasoning)

### tier 层 (glm5_2_nv, 60min)
- 成功: pexec_success×12 (k0/k4 b1b22d03, k2 3b9748d8/b1b22d03, k4 b6029a96) + integrate_success×4 (k1/k3)
- 失败: integrate_conn_RemoteDisconnected×6 (k1/k3) + pexec_SSLEOFError×4 (k2/k4) + pexec_conn_RemoteDisconnected×2 (k2/k4)
- 失败均被 mark_transport_error 5-10s 短惩罚处理, 未冻结 key
- per-key 路由铁证: k1/3/5→pexec+fid, k2/4→integrate (符合 R-glm52split 设计)

### 全 caller 错误分类 (60min)
- all_tiers_exhausted ×7 (hermes 配额型 429, NVCF 侧配额, 非 cc2 链路)
- NVAnthCollect_IncompleteRead ×1 (cc4101-primary, R661 restart 前事件)
- NVStream_IncompleteRead ×1 (hermes bcc03ca7 @07:50:34)

### deadline 链
- 6h stream_total_deadline=0 (健康铁证)
- 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle

### 配置 (无漂移)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, buffer 5×90s=450s, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=dsv4p_nv→dsv4p_nv40066:40066, STREAM_TOTAL=470, HEADER=400

## 下一步
- 等下一波 cc4101-primary 流量 + IncompleteRead 再现 → 查 NV-ANTH-COLLECT-BUFRETRY 日志判断 R661 是否生效
- 持续监控 deadline 链 + dsv4p_nv 配额型 429 (NVCF 侧)
- 若 IncompleteRead 再现且仍落 502 (buffer 重试未救回) → 深查 handlers.py:1853 触发条件是否命中

## 参数快照 (无变化, 沿用 R661)
| 层 | 参数 | 值 |
|---|---|---|
| NVCF 单次 | UPSTREAM_TIMEOUT | 90s |
| buffer 5key×90s | NVU_BUFFER_TIMEOUT_STAIRS | 90,90,90,90,90 |
| buffer 总预算 | NVU_BUFFER_TOTAL_DEADLINE_S | 450s |
| cc4101 总上限 | CC4101_STREAM_TOTAL_DEADLINE_S | 470s |
| cc4101 header | PRIMARY_HEADER_TIMEOUT | 400s |
| cc2 SDK 总超时 | API_TIMEOUT_MS | 600000ms |
| cc2 SDK idle | CLAUDE_STREAM_IDLE_TIMEOUT_MS | 900000ms |
