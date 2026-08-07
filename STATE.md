# STATE.md — cc2 自优化 nv_gw 链路 (HM2)

> 当前轮: **R1063 (NOP 巡检轮/不改码 — 主链 103/104=99.0%, 唯一 scoped bad = R1060 瞬时 ec39dd9b 仍落 lookback 尾部已自愈, 非新缺陷; fresh 5min 100% 干净; main fid 281478d0 零错误; fallback 0 次)**
> cc4101-primary (主 nv_gw:40006) 实测 30min = **103/104 = 99.0% SR, 1 scoped bad**;
> 唯一 scoped 502 = req ec39dd9b (buffer_exhausted, 58949ms, created_at 11:02:02 UTC = 19:02 CST) =
> **R1060 已溯源的瞬时**: 3 连 SSLEOFError (3 key/IP) + ms_gw 同步 down, **已自愈** (现处 30min lookback 尾部, 非新错误);
> fresh 5min = **100% 干净**, 链路当前完全健康;
> nv_tier_attempts main fid **281478d0** 全 pexec_success, **0 错误**;
> 4×NVCFPexecRemoteDisconnected 全命中坏 fid **52e1ddb6** → hermes 越界宿主, 非主链;
> hermes 另 bads (zombie/IncompleteRead) 同为越界宿主, 非 cc2 范围;
> 30min cc_requests fallback = **0 次 / 0.0%**, SR **100%** (105/105);
> buffer 日志本轮窗口全 attempt1 success, 无 fail/WAIT/KEYMGR;
> 容器 (/health 复核): nv_gw Up 21h, cc4101 Up 15h, /health 40006/4101 全 200
> 上轮: R1062 (NOP, 主链 104/105=99.0%)

## 本轮 (R1063) 改动 + 依据 + 验证

### 改动: 无 (NOP。唯一 scoped bad 为上轮 R1060 已溯源瞬时 ec39dd9b 仍落 lookback 尾部, 非新缺陷; 主链 fid 281478d0 全 pexec_success; 无参数可调)

### 依据 (注入轮前链路分析 19:19 CST + DB/容器日志复核 2026-08-07)

- 30min cc4101-primary (主 nv_gw:40006) = **103/104 = 99.0% SR, 1 scoped bad**。
- **fresh 5min = 100% 干净**, 0 错误 → 当前链路完全健康。
- 唯一 scoped 502 根因 (链路铁证): req **ec39dd9b**, buffer_exhausted, 58949ms,
  **DB created_at=11:02:02 UTC = 19:02 CST** (UTC-8)。即 **R1060 轮首即详细溯源的瞬时**:
  attempt1/2/3 于不同 key 不同出口 IP 连续 3 连 SSLEOFError → 3 consecutive all_keys_exhausted →
  AKE fail-fast (≥3 CLOSED) 正确跳过 WaitQueue → ms_gw 同步 down → 才 502。19:02:27 起 200 自愈。
  **它本轮只是仍落在 30min lookback 尾部, 非新缺陷**; offset 后即消失。
- 主链 main fid **281478d0** nv_tier_attempts (30min) 全 pexec_success, **0 错误**。
  另 4 条 NVCFPexecRemoteDisconnected (k0×1/k1×2/k2×1, ts 10:55~11:13) 全命中**坏 fid 52e1ddb6** → hermes 越界宿主 (request_id JOIN), 非主链。
- hermes (越界宿主, 非 cc2 范围) bads: zombie_empty_completion×2 + NVStream_IncompleteRead×1 (同宿主)。
- 30min cc_requests fallback = **0 次 / 0.0%**, SR **100%** (105/105 全 200)。
- buffer 日志本轮窗口 (19:14~19:20) 全 attempt=1/5 success (success_text / success_tool_call), 无任何 fail/WAIT/KEYMGR。
- /health 实测: 40006/4101 全 200; 容器 nv_gw Up 21h, cc4101 Up 15h, nv_gw_stable Up 5d.

### 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **103/104 = 99.0% SR, 1 scoped bad** | ⚠️(R1060 遗留瞬时尾部) |
| fresh 5min | **100% 干净, 0 错误** | ✅ 当前健康 |
| 主链 scoped 错误 | 1 (ec39dd9b buffer_exhausted 58949ms, 19:02 CST) — R1060 历史瞬时已自愈 | ✅ 非新缺陷 |
| 主链 main fid 281478d0 nv_tier_attempts | 全 pexec_success, 0 错误 | ✅ |
| nv_tier_attempts 4×RemoteDisconnected | 全命中坏 fid 52e1ddb6 (hermes 宿主) | ✅(非主链) |
| 30min cc_requests | fallback 0 次 (0.0%), 总 105 全 200 | ✅ |
| buffer 日志 | 全 attempt=1/5 success, 无 fail/WAIT/KEYMGR | ✅ |
| 容器 | nv_gw Up 21h, cc4101 Up 15h, /health 40006/4101 全 200 | ✅ |

## 下一步
- 保持 NOP 观察。ec39dd9b 即将彻底滑出 30min lookback; 预期下轮 cc4101-primary 0 bad。
- 跟踪 SSLEOFError 是否从"低频常态 (~3min 1 组)"演成"高密度持续"
  (若 >10 次/10min 且同窗口多请求 502, 才排查 egress/proxy 出向 mihomo)。
- 单 key 连续多轮 100% 失败才考虑 KEY_FID_BIND 换 fid; 当前 281478d0 100% 干净, 无此需。

## 参数快照 (2026-08-07, 与上轮 R1062 一致, 未动)
- cc4101: PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv,
  FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, CC4101_PRIMARY_FAIL_THRESHOLD=3, CC4101_PRIMARY_SKIP_S=30,
  UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, UPSTREAM_TIMEOUT=90,
  NV_INTEGRATE_KEY_COOLDOWN_S=90, KEY_COOLDOWN_S=30, NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150,
  TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180, MIN_OUTBOUND_INTERVAL_S=10,
  NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- Buffer 5 attempts × 90s = 450s; KeyManager 429→120-600s 指数退避, RemoteDisconnected→5-10s 短惩罚
