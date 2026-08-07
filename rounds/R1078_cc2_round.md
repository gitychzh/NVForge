# R1078 — cc2 NOP 巡检轮 (2026-08-07 21:00 CST)

## 结论: NOP, 不改码

cc2 主链 (cc4101-primary → nv_gw:40006, dsv4f0731_nv) 30min 绝大多数时间完全健康, 仅 1 个 transient bad:
**110/111 = 99.1% SR, 1 bad (buffer_exhausted 502, avg_dur 62796ms)**; fallback 0 次。
该 1 bad 与 R1077 同签名: **transient SSLEOFError `UNEXPECTED_EOF_WHILE_READING`** 多 key egress 抖动,
本轮注入窗口 (20:28 CST) 为 20:19 尾段 `c107bc7e` 残迹, ~20:20:30 后全部恢复 (后续 110×200 clean 全 attempt=1), 参数无需改动。

## 依据

- 注入轮前链路分析 (20:28 CST): cc4101-primary|dsv4f0731_nv|200|110 + 502|1 (err=buffer_exhausted, avg_dur 62796ms)。
  dsv4f0731_nv 整体 SR=99.3% (150/151, 主链统计); hermes 40×200 + 1×502 (out-of-scope)。
  错误分类 buffer_exhausted×1 (root-cause=SSLEOFError egress 抖动), zombie_empty_completion×1 (参考)。
  per-key 0=24/1=19(+1 RemoteDisconnected)/2=22/3=23/4=20 全 pexec_success; 30min fallback 0 次 (0%)。
- 容器 /health 复核: 40006 nv_gw 200, 4101 cc4101 200; nv_gw Up 17h, cc4101 Up 17h。

## root cause 分析 (1 bad: buffer_exhausted)

- nv_gw 日志 (--since 30m) 复核: 2 个同签名 transient buffer_exhausted (`2d088060`@20:15 + `c107bc7e`@20:19),
  均为 **SSLEOFError `UNEXPECTED_EOF_WHILE_READING`** 依次命中 k3/5→k1→k2, 每次轮转不同 key 仍全挂。
- 3 次 consecutive all_keys_exhausted 触发 **AKE fail-fast** (`c107bc7e`@20:19:55, skip WaitQueue 省 180s, state CLOSED)
  → 尝试 ms_gw fallback → ms_gw 未接管 (time-locked 同瞬时窗口) → 报 502 给 CC。
- **AKE fail-fast + buffer 超时链工作完全符合设计**: 60s 内 fail-fast, 未浪费 450s buffer 预算。
- 我复核日志确认 **20:20:30 后 nv_gw 再 0 条 SSLEOFError、0 条 buffer/wait 活动**, 后续全 attempt=1 success ——
  已自愈, 与 R1077 模式完全一致 (离散 egress 抖动, 故障在上游 TLS 连接中断, 非配置漂移, 无参数可调)。

## 数据表

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **110/111 = 99.1% SR, 1 bad** (buffer_exhausted) | ⚠️ 1 transient bad |
| 30min fallback | 0 次 (0.0%), 全走主链 | ✅ |
| dsv4f0731_nv 整体 | 150/151 = 99.3% | ✅ |
| 错误分类 | buffer_exhausted×1 (20:19 残迹), zombie×1 (参考) | ⚠️ root-caused |
| root cause | transient SSLEOFError egress 抖动, 20:20:30 后全恢复 | ✅ 无参数可调 |
| per-key | 0/2/3/4 pexec_success, key1 19+1 RemoteDisconnected (常态单键抖动) | ✅ |
| buffer 日志 | 20:20:30 后 0 SSLEOF/0 buffer/0 wait, 全 attempt=1 success | ✅ |
| 容器 /health | 40006/4101 全 200; nv_gw Up 17h, cc4101 Up 17h | ✅ |

## 下一步

- 保持 NOP 观察。连续 2 轮 (R1077+R1078) 各 1 个 bad 均同签名 transient SSLEOFError egress 离散抖动, 已自愈, 非配置漂移。
- 若 SSLEOFError 复现且呈**持续分布** (非单次离散抖动), 才查 egress IP / mihomo 代理健康 (7900-7904 线路),
  但那属 dsv4f0731_nv 链路 / 宿主机代理问题, 超出 nv_gw 参数调整范围 (记入 ssleof-error-transient-egress-blip)。
- 持续监控 key1 RemoteDisconnected 是否连续多轮单键 100% 失败才考虑 KEY_FID_BIND 换 fid; 当前单次抖动后恢复, 无需动作。

## 参数快照 (未动, 与 R1077 一致)
- cc4101: PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv,
  FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, CC4101_PRIMARY_FAIL_THRESHOLD=3, CC4101_PRIMARY_SKIP_S=30,
  UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, UPSTREAM_TIMEOUT=90,
  NV_INTEGRATE_KEY_COOLDOWN_S=90, KEY_COOLDOWN_S=30, NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150,
  TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180, MIN_OUTBOUND_INTERVAL_S=10,
  NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- Buffer 5 attempts × 90s = 450s; KeyManager 429→120-600s 指数退避, RemoteDisconnected→5-10s 短惩罚