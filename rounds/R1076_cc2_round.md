# R1076 — cc2 NOP 巡检轮 (2026-08-07 20:20 CST)

## 结论: NOP, 不改码

cc2 主链 (cc4101-primary → nv_gw:40006, dsv4f0731_nv) 完全健康:
30min = **109/109 = 100% SR, 0 bad**; cc_requests 110 条全走主链, fallback 0 次 (0.0%);
主链错误分类为空 (无 zombie, 无 502, 无 timeout);
per-key 全 5 key pexec_success (0:24 / 1:19+1 / 2:22 / 3:20 / 4:21), key1 一次 NVCFPexecRemoteDisconnected 后随行 19 次 success (常态单键抖动);
buffer 日志全 attempt=1 即 success_tool_call (3-9s, input 66-68K tokens), 无 fail/WAIT/KEYMGR 死锁;
容器 /health 全 200 (40006 nv_gw, 40066 dsv4p, 4101 cc4101), nv_gw Up 21h, cc4101 Up 16h.

## 依据

- 注入轮前链路分析 (20:17 CST): cc4101-primary|dsv4f0731_nv|200|106 (100%, 0 bad);
  dsv4f0731_nv 整体 SR=99.4% (171/172), 1×502 zombie_empty_completion (avg_dur 5428ms);
  per-key 0/2/3/4 pexec_success, key1 19 success + 1 RemoteDisconnected; 30min per-egress-IP / dsv4p 200 延迟数据均空 (本轮无 dsv4p 流量)。
- 独立 DB 复核 (20:19 CST): cc4101-primary|nv_requests = **200|109 (100%, 0 error)**;
  cc_requests (110 条) = sr 100.0%, fallback 0 次 (0.0%), 全走主链。
- buffer 日志抽查: 4 条 BUFFER-START 全部 attempt=1 即 success_tool_call 并 flushed (3-9s), verdict=success_tool_call, 无 fail/WAIT/KEYMGR。

## 数据表

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **109/109 = 100% SR, 0 bad** | ✅ |
| 30min cc_requests | 110 条, sr 100%, fallback 0 次 (0.0%), 全走主链 | ✅ |
| dsv4f0731_nv 整体 | 171/172 = 99.4% (1×zombie, 作参考) | ✅ |
| psql 复核 | nv_requests caller=cc4101-primary = 200\|109 (0 error) | ✅ |
| per-key | 全 5 key pexec_success; key1 一次 RemoteDisconnected 后 19 次 success | ✅ |
| buffer 日志 | 全 attempt=1 success (3-9s), 无 fail/WAIT/KEYMGR | ✅ |
| 容器 /health | 40006/40066/4101 全 200; nv_gw Up 21h, cc4101 Up 16h | ✅ |

## 下一步

- 保持 NOP 观察。主链连续多轮 0 bad 已到完全健康基线, 无参数可调。
- 仅当 cc2 主链自身出现 bad 或 fallback > 约 10% 才行动; 本轮 1×zombie 为 hermes 越界宿主 (非主链), 不计入 cc2 范围。
- key1 NVCFPexecRemoteDisconnected 持续监控: 若连续多轮单键 100% 失败才考虑 KEY_FID_BIND 换 fid; 当前单次抖动后恢复, 无需动作。

## 参数快照 (未动, 与上轮 R1075 一致)
- cc4101: PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv,
  FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, CC4101_PRIMARY_FAIL_THRESHOLD=3, CC4101_PRIMARY_SKIP_S=30,
  UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, UPSTREAM_TIMEOUT=90,
  NV_INTEGRATE_KEY_COOLDOWN_S=90, KEY_COOLDOWN_S=30, NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150,
  TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180, MIN_OUTBOUND_INTERVAL_S=10,
  NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- Buffer 5 attempts × 90s = 450s; KeyManager 429→120-600s 指数退避, RemoteDisconnected→5-10s 短惩罚