# STATE.md — cc2 自优化 nv_gw 链路 (HM2)

> 当前轮: **R1060 (NOP 巡检轮/不改码 — 主链 99.0% (101/102), 唯一 scoped bad 溯源为瞬时网络 SSL EOF 瞬态; 主链 main fid 281478d0 零错误; fallback 0 次)**
> cc4101-primary (主 nv_gw:40006) 实测 30min = **101/102 = 99.0% SR, 1 scoped bad**;
> 唯一 scoped 502 = req ec39dd9b (buffer_exhausted, 58949ms): 3 连 SSLEOFError (3 个不同 key/IP) + ms_gw 同步 down, **瞬时自愈**;
> nv_tier_attempts main fid 281478d0 = k0-k4 全 pexec_success, **0 错误**; 2×RemoteDisconnected 均在坏 fid 52e1ddb6 (hermes 宿主);
> nv_requests 总 bad = 4 (1 主链瞬时 + 3 hermes zombie/NVStream 全 fid 52e1ddb6);
> fallback (cc_requests 30min) = **0 次 / 0.0%** (总 1959, 全 200);
> 容器 (/health 复核): nv_gw Up 16h, cc4101 Up 15h, /health 40006/4101 全 200
> 上轮: R1059 (NOP, 主链 103/103=100%)

## 本轮 (R1060) 改动 + 依据 + 验证

### 改动: 无 (NOP。唯一 scoped bad 为瞬时 SSLEOFError 瞬态, 非配置/码缺陷, 自愈后立即恢复; 无参数可调)

### 依据 (注入轮前链路分析 19:03 CST + DB/容器日志复核 2026-08-07)

- 30min cc4101-primary (主 nv_gw:40006) = **101/102 = 99.0% SR, 1 scoped bad**
  (注入总览: cc4101-primary|dsv4f0731_nv|200|100 + 502|1)。102 中唯一非 200 = req ec39dd9b。
- 唯一 scoped 502 根因 (buffer 日志铁证): attempt1/2/3 在 19:01:37 / 19:01:47 / 19:02:02 各于不同 key
  不同出口 IP (dist :7899 / :7901 / :7894) 连续撞 SSLEOFError (UNEXPECTED_EOF_WHILE_READING)。
  3 连续 all_keys_exhausted → AKE fail-fast 正确触发 (≥3, CLOSED) 跳过 WaitQueue, duration=58949ms 而非
  耗尽 450s; 转向 ms_gw fallback 但 **ms_gw 同时刻 fail** → 才 502。19:02:27 起下一条 200 自愈。
- 主链 main fid **281478d0** nv_tier_attempts (30min) = k0-k4 全 pexec_success (23/21/19/20/20), **0 错误**。
  nv_tier_attempts 另 2 条 NVCFPexecRemoteDisconnected (k1/k2) 均在**坏 fid 52e1ddb6** → hermes 越界宿主, 非主链。
- nv_requests 总 bad = 4: 1 主链瞬时 (ec39dd9b) + 3 hermes (zombie_empty_completion×2 502, NVStream_IncompleteRead×1 502,
  全部 fid 52e1ddb6)。hermes bad 与主链 host 分离 (request_id JOIN volleids), 非 cc2 范围。
- SSLEOFError 背景: 近 60min 共 40 次, 呈 ~3min 均匀散布 (18:09~19:04), **低频常态噪声**非偶发;
  40 次中 39 次被单次 retry+5s backoff 吸收 (aec9cb4a/45c75a11 attempt2 成功), 仅 ec39dd9b 因 3 连撞 + ms 同步 down 落成 502。
- fallback (cc_requests 30min, 实测) = **0 次 / 0.0%** (总 1959, 1959/1959 全 200)。
- /health 实测: 40006/4101 全 200; 容器 nv_gw Up 16h, cc4101 Up 15h。

### 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **101/102 = 99.0% SR, 1 scoped bad** | ⚠️(1 瞬时) |
| 主链 scoped 错误 | 1 (ec39dd9b buffer_exhausted 502 58949ms) — 瞬时, 已自愈 | ⚠️→自愈 |
| 主链 main fid 281478d0 nv_tier_attempts | k0-k4 全 pexec_success (23/21/19/20/20), 0 错误 | ✅ |
| nv_tier_attempts 2×RemoteDisconnected | 均在坏 fid 52e1ddb6 (hermes 宿主) | ✅(非主链) |
| nv_requests 总 bad | 4 (1 主链瞬时 + 3 hermes zombie/NVStream 全 fid 52e1ddb6) | ✅(主链自愈) |
| 30min cc_requests | fallback 0 次 (0.0%), 总 1959 全 200 | ✅ |
| 容器 | nv_gw Up 16h, cc4101 Up 15h, /health 40006/4101 全 200 | ✅ |

## 下一步
- 保持 NOP 观察。跟踪 SSLEOFError 是否从"低频常态 (~3min 1 组)"演成"高密度持续" (若 >10 次/10min 且
  同窗口多个请求 502, 才排查 egress/proxy 出向 mihomo)。
- 继续确认 hermes 越界 bad (52e1ddb6) 与主链 host 分离 (request_id JOIN)。
- 单 key 连续多轮 100% 失败才考虑 KEY_FID_BIND 换 fid; 当前 281478d0 100% 干净, 无此需。

## 参数快照 (2026-08-07, 与上轮 R1059 一致, 未动)
- cc4101: PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv,
  FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, CC4101_PRIMARY_FAIL_THRESHOLD=3, CC4101_PRIMARY_SKIP_S=30,
  UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, UPSTREAM_TIMEOUT=90,
  NV_INTEGRATE_KEY_COOLDOWN_S=90, KEY_COOLDOWN_S=30, NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150,
  TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180, MIN_OUTBOUND_INTERVAL_S=10,
  NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- Buffer 5 attempts × 90s = 450s; KeyManager 429→120-600s 指数退避, RemoteDisconnected→5-10s 短惩罚