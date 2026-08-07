# R1061 — cc2 NOP 巡检 (纯纪录, 不改码)

> 判稳结论: **NOP 巡检轮.** 主链 30min SR = 99.1% (105/106), 唯一 scoped bad 为
> **上轮 R1060 已溯源的历史瞬时** ec39dd9b (19:02 buffer_exhausted, SAID 已自愈); 当前
> **新窗口 (近5min) 100% 干净 (19/19)**. main fid 281478d0 百万错误零. fallback 0%.
> **本轮无任何配置/码改动**, 纯纪录. R1060 遗留瞬时仍在当前 lookback 内, 非新缺陷.

## 轮前注入 (19:10 CST) 对照实测

| 项 | 注入值 | 实测复核 | 结论 |
|---|---|---|---|
| cc4101-primary status | 200×104 + 502×1 | 200×105 + 502×1 (又+1 成功) | ✅ 一致, 增一条成功 |
| scoped 502 | req ec39dd9b buffer_exhausted 58949ms | 同 19:02:02, 已自愈 | ✅ R1060 历史瞬时 |
| nv_tier_attempts RemoteDisconnected | 2 | 3 (k0/k1/k2) | ✅ 全在坏 fid 52e1ddb6 |
| fallback | — | 0 次 (0.0%), SR 100% | ✅ |
| buffer/wait 日志 | 无 | 全 attempt1 success, 无 fail | ✅ |

## 本轮数据 (实测 2026-08-07 19:12 CST)

- **cc4101-primary (主 nv_gw:40006) 30min = 105/106 = 99.1% SR, 1 scoped bad**.
- **fresh 5min = 19/19 = 100%**, 0 错误 → 当前链路完全健康.
- 唯一 scoped bad = req ec39dd9b (buffer_exhausted, 58949ms, **DB created_at=11:02:02 UTC = 19:02 CST**),
  即 **R1060 已详溯源的瞬时**: 19:01:37~19:02:02 连续 3 连 SSLEOFError (dist :7899/:7901/:7894) →
  AKE fail-fast (≥3 CLOSED) 正确跳过 WaitQueue → ms_gw 同步 fail → 才 502. 19:02:27 起下一条 200 自愈.
  **本轮它只是仍落在 lookback 里, 不是新错误.**
- **nv_tier_attempts main fid 281478d0** = k0 22 / k1 19 / k2 22 / k3 20 / k4 21, **全 pexec_success, 0 错误**.
  nv_tier_attempts 3 条 NVCFPexecRemoteDisconnected (k0/k1/k2) **全部命中坏 fid 52e1ddb6** → hermes 越界宿主,
  request_id JOIN 已归 hermes, 非主链.
- **30min cc_requests fallback = 0 次 / 0.0%**, SR **100%** (106/106).
- **buffer 日志**: 本轮窗口 19:09~19:11 全 attempt=1/5 success (success_text / success_tool_call), 无任何 fail.
- **容器**: /health 40006 + 4101 全 200; nv_gw Up 16h, cc4101 Up 15h, nv_gw_stable Up 5d.

## 本轮改动

**无 (NOP).** 唯一 scoped bad = R1060 历史瞬时仍留 lookback, 无参数可调. 主链 fid 281478d0 零错误,
SSLEOFError 为低频常态噪声 (每 ~3min 一组, 多被单次 retry+10s backoff 吸收).

## 下一步
- 保持 NOP 观察. 跟踪 SSLEOFError 是否从"低频常态 (~3min 1 组)"演成"高密度持续"
  (若 >10 次/10min 且同窗口多请求 502, 才排查 egress/proxy 出向 mihomo).
- 确认 ec39dd9b 滑出 30min lookback 后本窗口为 0 bad (预期).
- 单 key 连续多轮 100% 失败才考虑 KEY_FID_BIND 换 fid; 当前 281478d0 100% 干净, 无此需.

## 参数快照 (与 R1060 全一致, 未动)
- cc4101: PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv,
  FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, CC4101_PRIMARY_FAIL_THRESHOLD=3,
  CC4101_PRIMARY_SKIP_S=30, UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, UPSTREAM_TIMEOUT=90,
  NV_INTEGRATE_KEY_COOLDOWN_S=90, KEY_COOLDOWN_S=30, NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150,
  TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180, MIN_OUTBOUND_INTERVAL_S=10,
  NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- Buffer 5 attempts × 90s = 450s; KeyManager 429→120-600s 指数退避, RemoteDisconnected→5-10s 短惩罚.