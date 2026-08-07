# R1074 — cc2 NOP 巡检轮 (2026-08-07 20:05 CST)

## 结论: NOP, 不改码

cc2 主链 (cc4101-primary → nv_gw:40006, dsv4f0731_nv) 完全健康:
30min = **103/103 = 100% SR, 0 bad**; cc_requests 106 条全走主链, fallback 0 次 (0.0%);
唯一 bads 均 **host_machine=opc2sname-dsv4f40666** (hermes 越界宿主 40666 容器, 非 cc2 范围, 2× zombie_empty_completion);
zombie 铁证: request_id JOIN cc_requests 无行 → 非主链请求;
per-key 全 5 key pexec_success (20/17/26/19/21), key1 一次 NVCFPexecRemoteDisconnected 后 17 次 success (常态单键抖动);
buffer 日志全 attempt=1 即 success_tool_call (7-12s, input 67-72K tokens), 无 fail/WAIT/KEYMGR 死锁;
容器 /health 全 200 (40006 nv_gw, 40066 dsv4p, 4101 cc4101), nv_gw Up 17h, cc4101 Up 16h.

## 依据

- 注入轮前链路分析 (20:05 CST): cc4101-primary|dsv4f0731_nv|200|103 (100%, 0 bad);
  dsv4f0731_nv 整体 SR=98.9% (174/176), 2×502 zombie_empty_completion; per-key 0/1/3/4 pexec_success, key1 16 success + 1 RemoteDisconnected.
- 独立 DB 复核: zombie×2 归属 proxy_role=passthrough, host_machine=opc2sname-dsv4f40666 (越界 40666 hermes 线),
  request_id JOIN cc_requests 无行 → 非 cc2 主链; cc_requests 106 条 fallback=0.
- per-key 抽查: key1 一次 NVCFPexecRemoteDisconnected 后 17 次 success, 非持续性, 无动作。
- buffer 日志抽查 20:06: 4 条 BUFFER-START 全部 attempt=1 即 success_tool_call 并 flushed (7-12s), verdict=success, 无 fail/WAIT/KEYMGR。

## 数据表

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **103/103 = 100% SR, 0 bad** | ✅ |
| 30min cc_requests | 106 条, fallback 0 次 (0.0%), 全走主链 | ✅ |
| dsv4f0731_nv 整体 | 174/176 = 98.9% (作参考) | ✅ |
| hermes 越界宿主 (40666, 非 cc2) | zombie_empty_completion×2, 铁证 host_machine=opc2sname-dsv4f40666 | ⚠️ 非主链 |
| per-key | 全 5 key pexec_success; key1 一次 RemoteDisconnected 后恢复 | ✅ |
| buffer 日志 | 全 attempt=1 success (7-12s), 无 fail/WAIT/KEYMGR | ✅ |
| 容器 /health | 40006/40066/4101 全 200; nv_gw Up 17h, cc4101 Up 16h | ✅ |

## 下一步

- 保持 NOP 观察。主链连续多轮 0 bad 已到完全健康基线, 无参数可调。
- 仅当 cc2 主链自身出现 bad 或 fallback > 约 10% 才行动; hermes 越界宿主 40666 bads 不计入 cc2 范围。
- key1 NVCFPexecRemoteDisconnected 持续监控: 若连续多轮单键 100% 失败才考虑 KEY_FID_BIND 换 fid; 当前单次抖动后恢复, 无需动作。

## 参数快照 (未动, 与上轮 R1073 一致)

- cc4101: PRIMARY=http://nv_gw:40006/v1/messages model=dsv4f0731_nv; FALLBACK=http://ms_gw:40007 model=glm5_2_ms;
  STREAM_TOTAL_DEADLINE=470s, PRIMARY_HEADER_TIMEOUT=400, PRIMARY_FAIL_THRESHOLD=3, PRIMARY_SKIP_S=30,
  UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, UPSTREAM_TIMEOUT=90,
  NV_INTEGRATE_KEY_COOLDOWN=90, KEY_COOLDOWN=30, NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150,
  TIER_TIMEOUT_BUDGET=180, TIER_COOLDOWN=180, MIN_OUTBOUND_INTERVAL=10, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2
- Buffer 5×90s=450s; cc4101 fallback 受 ms_gw (铁律: 不主动禁用, 当前 0 触发)。