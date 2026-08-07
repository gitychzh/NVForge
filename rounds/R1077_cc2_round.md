# R1077 — cc2 NOP 巡检轮 (2026-08-07 20:30 CST)

## 结论: NOP, 不改码

cc2 主链 (cc4101-primary → nv_gw:40006, dsv4f0731_nv) 30min 大多数时间完全健康, 仅 1 个 transient bad:
**102/103 = 99.0% SR, 1 bad (buffer_exhausted 502, avg_dur 62796ms)**; fallback 0 次。
该 1 bad 已根因定位为 **transient SSLEOFError 多 key 同发 egress 抖动**, 20:20:32 后全部恢复 (102×200 全 clean), 参数无需改动。

## 依据

- 注入轮前链路分析 (20:22 CST): cc4101-primary|dsv4f0731_nv|200|102 + 502|1 (err=buffer_exhausted)。
  dsv4f0731_nv 整体 SR=99.4% (162/163); 错误分类 buffer_exhausted×1, zombie_empty_completion×1。
  per-key 0/2/3/4 全 pexec_success, key1 18 success + 1 NVCFPexecRemoteDisconnected (常态单键抖动)。
  30min fallback 发生率 = 0% (164 条 f 桶全 0)。
- 容器 /health 复核: 40006 nv_gw 200, 4101 cc4101 200, 40007 ms_gw 200; nv_gw Up 17h, cc4101 Up 16h。

## root cause 分析 (1 bad: buffer_exhausted)

- 90min 内共有 **2 个**同日同签名的 transient buffer_exhausted: `ec39dd9b`(19:01-19:02) + `c107bc7e`(20:19-20:20)。
- 两者完全相同模式: **SSLEOFError `UNEXPECTED_EOF_WHILE_READING`** 依次命中 k5→k1→k2 (e-IP 7899/7901/7894),
  每次相距离散 N 分钟, 均为远端/代理 TLS 连接中断 (transport-level, 非 nv_gw 配置问题)。
- 每次 attempt 轮转不同 key 仍全挂 → 3 次 consecutive all_keys_exhausted 触发 **AKE fail-fast** (跳过 WaitQueue,
  省 180s, state=CLOSED) → 尝试 ms_gw fallback → ms_gw 也未能接管 (time-locked 同一瞬时窗口) → 报错给 CC。
- **AKE fail-fast + buffer 超时链工作完全符合设计**: 未浪费 450s buffer 预算, 60s 内即 fail-fast 释放。
- 20:20:32 后 nv_gw 再无 SSLEOFError, 后续全部 attempt=1 success (flushed 1-16s, input 60-69K tokens);
  无参数改动能预防远端 TLS EOF drop (故障在上游, 超出 nv_gw 控制)。

## 数据表

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **102/103 = 99.0% SR, 1 bad** (buffer_exhausted) | ⚠️ 1 transient bad |
| 30min fallback | 0 次 (0.0%), 全走主链 | ✅ |
| dsv4f0731_nv 整体 | 162/163 = 99.4% | ✅ |
| 错误分类 | buffer_exhausted×1 (2026 20:19), zombie×1 (参考) | ⚠️ root-caused |
| root cause | transient SSLEOFError egress 抖动, 20:20:32 后全恢复 | ✅ 无参数可调 |
| per-key | 0/2/3/4 pexec_success, key1 18+1 RemoteDisconnected 后恢复 | ✅ |
| buffer 日志 | 20:20:32 后全 attempt=1 success, 无死锁 | ✅ |
| 容器 /health | 40006/4101/40007 全 200; nv_gw Up 17h, cc4101 Up 16h | ✅ |

## 下一步

- 保持 NOP 观察。本轮 1 bad 为 transient SSLEOFError egress 抖动 (故障在上游), 已自愈, 非配置漂移。
- 若 SSLEOFError 复现且呈**持续**分布 (非单次离散抖动), 才查 egress IP / mihomo 代理健康 (7900-7904 线路),
  但那是 dsv4f0731_nv 链路 / 宿主机代理问题, 超出 nv_gw 参数调整范围。
- 持续监控 key1 RemoteDisconnected 是否连续多轮单键 100% 失败才考虑 KEY_FID_BIND 换 fid; 当前单次抖动后恢复, 无需动作。

## 参数快照 (未动, 与上轮 R1076 一致)
- cc4101: PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv,
  FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, CC4101_PRIMARY_FAIL_THRESHOLD=3, CC4101_PRIMARY_SKIP_S=30,
  UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, UPSTREAM_TIMEOUT=90,
  NV_INTEGRATE_KEY_COOLDOWN_S=90, KEY_COOLDOWN_S=30, NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150,
  TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180, MIN_OUTBOUND_INTERVAL_S=10,
  NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- Buffer 5 attempts × 90s = 450s; KeyManager 429→120-600s 指数退避, RemoteDisconnected→5-10s 短惩罚