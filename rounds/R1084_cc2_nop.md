# R1084 cc2 NOP — primary 103/103=100% SR 全 clean 零坏 (连续第3轮); hermes 2 bad out-of-scope; fallback 0.0%; buffer 1 次 transient k4 RD 自愈补回

日期: 2026-08-07 20:59 CST

## 结论
**NOP 巡检轮, 不改码。** 主链 cc4101-primary (nv_gw:40006) 30min = **103/103 = 100% SR, 零 bad**,
连续第 3 轮全 clean (R1082 107/108 → R1083 115/115 → R1084 103/103)。无新错误, 无 fallback, 无配置漂移。

## 依据 (轮前注入 20:55 + DB 复核 20:58 + /health 复核 2026-08-07)

- **主链 cc4101-primary = 103/103 = 100% SR, 0 bad**。SELECT status...caller='cc4101-primary' → 全 200。
- **per-caller 归属**: dsv4f0731_nv 总 149/151=98.7% 的 2 bad (NVStream_IncompleteRead×1 + zombie_empty_completion×1, 均 502)
  经 caller 复核**全归 hermes**, out-of-scope; cc4101-primary 零坏。
- **per-key 健康**: 5 key 全 pexec_success (k0 22/k1 20/k2 22/k3 20/k4 19); 仅 k3 2 次 transient
  NVCFPexecRemoteDisconnected (仍 20/22 success 部分补回), 无冷却堆积。
- **buffer 自愈铁证**: req=0c9a505f attempt-1 key=k4 execute_failed (all_keys_exhausted=True, 瞬间 5 key 同挂)
  → backoff 5s → attempt-2 success_tool_call 全量 12789b flush 补回。同 SSLEOFError egress 离散抖动家族, transient 非配置。
- **30min fallback 0/104 = 0.0%**, 全走主链。
- **/health**: 40006 nv_gw 200, 4101 cc4101 200; docker ps nv_gw Up 17h, cc4101 Up 17h。
- 无 BUFFER-EXHAUSTED/WAIT-QUEUE/KEYMANAGER 堆积日志。

## 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **103/103 = 100% SR, 0 bad** | ✅ 连续第 3 轮全 clean |
| per-caller 归属 | 主链 0 bad; hermes 2 bad 均 out-of-scope | ✅ |
| per-key 健康 | 5 key 全 pexec_success; k3 2 次 transient RD | ✅ |
| 30min fallback | 0/104 = 0.0% | ✅ |
| buffer | req 1 次 k4 RD 自愈补回; 无 EXHAUSTED/WAIT | ✅ |
| 容器 /health | 40006/4101 全 200; Up 17h | ✅ |

## 下一步
- 保持 NOP 观察。主链连续 3 轮全 clean, 外圈 transient (k4 all_keys_exhausted) 已 buffer 自愈证明退避/重试机制有效。
- 仅当主链出现**持续分布**错误 (多 key 连续多轮非 pexec_success) 或单 key 100% 失败堆积才介入
  (查 egress IP / mihomo 7900-7904 / KEY_FID_BIND), 当前无需动作。

## 参数快照 (未动, 与 R1083 一致)
- cc4101: PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv,
  FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  CC4101_PRIMARY_FAIL_THRESHOLD=3, CC4101_PRIMARY_SKIP_S=30, UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, UPSTREAM_TIMEOUT=90,
  NV_INTEGRATE_KEY_COOLDOWN_S=90, KEY_COOLDOWN_S=30, NVU_FORCE_STREAM_UPGRADE=0,
  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180,
  MIN_OUTBOUND_INTERVAL_S=10, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- Buffer 5 attempts × 90s = 450s; KeyManager 429→120-600s 指数退避, RD→5-10s 短惩罚
