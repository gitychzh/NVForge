# R1060 cc2 — NOP (巡检) / 1 主链 scoped 502 溯源为瞬时网络 EOF 瞬态

> 日期: 2026-08-07 19:05 CST
> 上轮: R1059 (NOP, 103/103=100%)
> 决策: **NOP, 不改码** — 孤立瞬时 SSLEOFError 瞬态, 非链接缺陷, 自愈后立即恢复 100%

## 本轮数据 (30min window, 注入轮前分析 + DB 复核)

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **101/102 = 99.0% SR, 1 scoped bad** | ⚠️(1 瞬时 502) |
| 主链 scoped 错误 | 1 (req=ec39dd9b, buffer_exhausted, 502, 58949ms) | 瞬时 |
| 主链 main fid 281478d0 nv_tier_attempts | k0-k4 全 pexec_success (23/21/19/20/20), **0 错误** | ✅ |
| nv_tier_attempts 2×RemoteDisconnected | 均在**坏 fid 52e1ddb6, hermes 宿主** | ✅(非主链) |
| nv_requests 总 bad | 4 (1 主链瞬时 + 3 hermes: zombie×2, NVStream×1 全 fid 52e1ddb6) | ✅(主链 1) |
| 30min cc_requests | **1959/1959 = 100% SR, 0 fallback** | ✅ |

## 根因 (本轮唯一 scoped 502: req=ec39dd9b)

- 时间线 (buffer 日志铁证): 19:01:03 起 5 attempts; attempt1/2/3 在 19:01:37 / 19:01:47 /
  19:02:02 各在**不同 key 不同出口 IP** 连续撞 SSLEOFError (ssl_eof=1, cycles dist :7899=1 / :7901=1 / :7894=1),
  即 k5→k1→k2 三个不同 egress IP 都 SSL EOF。
- 3 连续 all_keys_exhausted → **AKE fail-fast 正确触发** (≥3, 状态 CLOSED), 跳过 WaitQueue,
  节省时间: duration=58949ms 而非耗尽 450s — R829 fail-fast 按预期工作。
- 转向 ms_gw fallback, 但 **ms_gw 同时刻也 fail** (NV-BUFFER-MS-FB-FAIL) → 才最终 502。
- 结论: 不是 fid/key/配置缺陷, 而是**瞬时代理网络瞬态 (SSL EOF 遍布出口)** + ms 同步 flap 的
  并发碰撞。19:02:27 起下一条请求立刻恢复 200 (2e5d83ab attempt1 success), **自愈即时**。

## SSLEOFError 背景 (近 60min docker logs 复核)

- 60min 内共 **40 次 SSLEOFError**, 呈 3 分钟间隔均匀散布 (18:09~19:04 每 ~3min 一组 3 行日志).
- 属于**低频常态噪声**而非偶发一次: 每个 EOF 平时被单次 retry + 5s backoff 吸收 (如 aec9cb4a /
  45c75a11 均 attempt2 成功)。**仅 ec39dd9b 一个请求**因 3 连撞 + ms 同步 down 而落成 502。
- 40 次中 39 次被 retry 吸收 → 单请求 502 是统计上必然出现的极小概率事件, 非需修复的缺陷。

## 判定

- SR 99.0% 达标 (阈值本链路 SR≥99% 且无**可修复**新错误), 唯一 bad 为瞬时网络瞬态, 非配置/码 bug。
- 主链 main fid 281478d0 零错误; 3 条 hermes bad (bad fid 52e1ddb6) 与主链 host 分离。
- 无可调参数: SSLEOF 是代理出向不可控噪声; 调 buffer/attempt 只会把稀有 502 提前而不消除 EOF;
  ms_gw 同步 flap 不可侧修复且铁律 4 禁止触碰。
- 因此 **NOP 巡检轮, 不改码**。

## 下一步
- 保持 NOP 观察。持续跟踪 SSLEOFError 是否从"低频常态"演成"高密度持续" (若某窗口 >10 次/10min
  且同时间段内多个请求 502, 才考虑 is egress/proxy 故障并排查 mihomo 出向)。
- 继续确认 hermes 越界 bad (52e1ddb6) 与主链 host 分离 (request_id JOIN)。
- 关注单 key 连续多轮 100% 失败才考虑 KEY_FID_BIND 换 fid (当前 281478d0 100% 干净, 无此需)。

## 参数快照 (2026-08-07, 与 R1059 一致, 未动)
- cc4101: PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv,
  FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, CC4101_PRIMARY_FAIL_THRESHOLD=3,
  CC4101_PRIMARY_SKIP_S=30, UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, UPSTREAM_TIMEOUT=90,
  NV_INTEGRATE_KEY_COOLDOWN_S=90, KEY_COOLDOWN_S=30, NVU_FORCE_STREAM_UPGRADE=0,
  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180,
  MIN_OUTBOUND_INTERVAL_S=10, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- Buffer 5 attempts × 90s = 450s; KeyManager 429→120-600s 指数退避, RemoteDisconnected→5-10s 短惩罚
- 容器: nv_gw Up 16h, cc4101 Up 15h, /health 40006/4101 全 200