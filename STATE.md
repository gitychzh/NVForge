# STATE.md — cc2 自优化 nv_gw 链路 (HM2)

> 当前轮: **R1088 (NOP 巡检轮/不改码 — cc2 主链 99/100=99.0% SR, 1 transient bad=502 buffer_exhausted 大thinking流多IP瞬时SSLEOF blip, self-heal fail-fast 后恢复; 30min 复窗口重归 100% clean, 零配置漂移, fallback 0.0%)**
> cc4101-primary (主 nv_gw:40006) 实测 30min = **99/100 = 99.0% SR, 1 bad**
> — 连续 6 轮全 clean 后本轮 1 个 transient bad, 根因已定位为 ~1min 多 US egress IP 瞬时 SSLEOFError (124K-token thinking 流, req=9baaf179), 3 次 consecutive all_keys_exhausted → AKE fail-fast 提前 40s 截断走 ms_gw, 之后全部请求 attempt-1 秒回 100% clean
> dsv4f0731_nv 总 144 请求 144×200 (SR=100.0%); 上轮主链 0 bad
> per-key 全 5 key 均 pexec_success (k0 19/k1 20/k2 18/k3 20/k4 19), 仅 k3 1 次 transient NVCFPexecRemoteDisconnected;
> buffer 复窗口全部 attempt-1 success 直接 flush 零重试 (除 9baaf179 1 次 3-attempt fail-fast); 无冷却堆积;
> fallback 0/145 = 0.0%;
> 容器 (/health 复核): nv_gw 200 (passthrough, 5 key), cc4101 200 (primary dsv4f0731_nv)
> 上轮: R1087 (NOP, 主链 103/103=100% 全 clean 零坏, 连续第 6 轮)

## 本轮 (R1088) 改动 + 依据 + 验证

### 改动: 无 (NOP。99/100=99.0% 仅 1 transient bad — 多 IP 瞬时 SSLEOF egress blip 已在 ~1min 内 self-heal, 之后复窗口回 100% clean, self-heal 机制工作正常, 无配置漂移, 无持续分布, 无参数可调)

### 依据 (轮前注入 21:16:33 CST + DB/日志复核 21:17 CST + 容器 /health 复核 2026-08-07)

- **30min cc4101-primary (主 nv_gw:40006) = 99/100 = 99.0% SR, 1 bad (502 buffer_exhausted 40665ms)**
  单 bad (req=9baaf179) 为 **124K-token thinking 大流**, 在 ~21:14:30–21:15:15 约 1min 窗口内
  多 key (k4 SSLEOFError 21:14:46, k5 SSLEOFError 21:15:06) 瞬时 egress 抖动,
  3 次 consecutive all_keys_exhausted → `NV-BUFFER-AKE-FASTM` fail-fast (3 连续 AKE ≥3) →
  skip WaitQueue → `NV-BUFFER-EXHAUSTED` → ms_gw (40665ms 提前截断, 未榨干 450s buffer)。
  特征与已归档 transient **SSLEOFError egress blip** 完全一致 (R1077/R1082 同签名)。
- **self-heal 铁证**: 21:15:24 起 `f7347c11/bf3150ec/b287bac5/fc57becf/34654518...` 全部 attempt=1/5 直 flush 秒回 200,
  复窗口 100% clean。fail-fast 机制 (3 连续 AKE → 30s 内截断) 工作正确, 未拖垮后续请求。
- **30min 错误分类 (nv_requests status!=200)** → 仅 1× buffer_exhausted (即上述, 已根因定位); 2h 内 2× buffer_exhausted (12:19/13:15 UTC) 间隔 1h, 非持续分布。
- **per-key 健康**: nv_tier_attempts(`created_at` 列) 全 5 key 均高 pexec_success (k0 19/k1 20/k2 18/k3 20/k4 19);
  仅 k3 1 次 NVCFPexecRemoteDisconnected (transient, 补回), 无冷却堆积, 无单 key 连续失败。
- **30min fallback 0/145 = 0.0%** (失败请求本身已计为 NV 非成功; 复窗口全走主链)。
- /health 实测: 40006 nv_gw 200 (passthrough, 5 key), 4101 cc4101 200 (primary dsv4f0731_nv)。

### 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **99/100 = 99.0% SR, 1 bad** (transient egress blip) | ⚠️→已self-heal, 复窗口100% |
| 30min 错误分类 | 仅 1× buffer_exhausted (124K thinking 流, 已根因) | ✅ 非持续分布 |
| per-caller 归属 | 主链 1 bad=transient; hermes 0 bad | ✅ |
| per-key 健康 | 5 key 全 pexec_success (18-20); 仅 k3 1x transient RD | ✅ |
| 30min fallback | 0/145 = 0.0%, 复窗口全走主链 | ✅ |
| buffer | 复窗口全部 attempt-1 直flush; 9baaf179 触发 AKE fail-fast 提前截断 | ✅ self-heal 正常 |
| 容器 /health | 40006/4101 全 200 | ✅ |

## 下一步
- 保持 NOP 观察。本轮 1 transient 502 根因=~1min 多 US egress IP 瞬时 SSLEOFError (大thinking流放大窗口敏感度),
  AKE fail-fast + 复窗口 attempt-1 秒回证明 self-heal 机制健壮, 非配置漂移。
- 关注点: 若同一 egress IP (7894/7896/7897/7899/7901) 在**未来 2h 多轮**连续出现 SSLEOFError+缓冲重试
  (不再让 attempt-1 直flush), 才查该代理线路/mihomo 端口, 当前无需动作。
- 持续 clean ≥ 数轮后再评估是否需对 124K+ thinking 大流裁减 (buffer_exhausted 概率随 input 大小上升属模型/流特性, 非链路 bug)。

## 参数快照 (未动, 与上轮 R1087 一致)
- cc4101: PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv,
  FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, CC4101_PRIMARY_FAIL_THRESHOLD=3, CC4101_PRIMARY_SKIP_S=30,
  UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, UPSTREAM_TIMEOUT=90,
  NV_INTEGRATE_KEY_COOLDOWN_S=90, KEY_COOLDOWN_S=30, NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150,
  TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180, MIN_OUTBOUND_INTERVAL_S=10,
  NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- Buffer 5 attempts × 90s = 450s; KeyManager 429→120-600s 指数退避, RemoteDisconnected→5-10s 短惩罚