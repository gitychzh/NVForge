# R1065 — cc2 自优化 nv_gw 链路 (HM2) — NOP 巡检轮/不改码

> 主链 cc4101-primary (nv_gw:40006) 30min = **111/112 = 99.1%, 1 scoped bad**;
> 唯一 scoped 502 = req **ec39dd9b** (buffer_exhausted 58949ms, created_at 11:02:02 UTC = 19:02 CST) =
> **R1060 已溯源的瞬时 (3 连 SSLEOFError + ms_gw down, 已自愈)**, 非新缺陷;
> 其 ts=11:01:03 UTC, 现 19:29 CST (=11:29 UTC), 距 30min 窗口尾 ~2min, **即将彻底滑出**;
> 主链 main fid **281478d0** nv_tier_attempts 全 pexec_success (109), **0 错误**;
> 30min (ts 列, 无 tier 过滤复核) **4 条** NVCFPexecRemoteDisconnected (k0×1/k1×2/k3×1)
> 命中 hermes 越界坏 fid **52e1ddb6**, 非主链;
> **fresh 5min = 全 200 干净**, 链路当前完全健康;
> 30min cc_requests fallback = **0 次 / 0.0%**, 主链 111/111=100%;
> buffer 日志全 attempt=1/5 success (1~14s), 无 fail/WAIT/KEYMGR;
> 容器: nv_gw Up 16h, cc4101 Up 16h, /health 40006/4101 全 200.

## 改动: 无 (NOP)

唯一 scoped bad 仍是 R1060 已溯源瞬时 ec39dd9b, 现处 30min lookback 尾部且即将滑出; 主链 fid 281478d0
0 错误; cc4101-primary fresh 5min 全 200 且 0 fallback; 无参数可调。

## 依据 (轮前链路分析 19:27 CST + DB/容器复核 2026-08-07 19:29)

- 30min cc4101-primary (nv_gw:40006) (DB 复核) = **111×200 + 1×502 = 111/112 = 99.1%**.
- 唯一 scoped 502 (DB 铁证, `request_id=ec39dd9b`): buffer_exhausted 58949ms,
  **ts=11:01:03 UTC, created_at=11:02:02 UTC = 19:02 CST**. 即 **R1060 已溯源的瞬时**
  (attempt1/2/3 于不同 key/出口连 3 SSLEOFError → 3 consecutive all_keys_exhausted →
  AKE fail-fast ≥3 CLOSED 正确跳过 WaitQueue → ms_gw 同步 down → 才 502; 19:02:27 已 200 自愈)。
  截至复核时刻 11:29 UTC, 该记录距 30min 截点 10:59 UTC **仅剩 ~2min, 即将彻底滑出 lookback**。
  **本轮仍计入 1 bad, 但确认为历史瞬时, 非新缺陷; 预期下轮 cc4101-primary 0 bad。**
- 主链 main fid **281478d0** nv_tier_attempts (30min, `ts` 列) = **109 × pexec_success 全 5 key
  (k0=23/k1=20/k2=23/k3=21/k4=22), 0 错误**。
  另 **4 条** NVCFPexecRemoteDisconnected (k0×1/k1×2/k3×1) 全命中**坏 fid 52e1ddb6**
  → hermes 越界宿主泄漏 (JOIN 铁证归属 40666/hermes 线), 非 cc2 主链。较 R1064 (5 条) 减 1, 持续低密度泄漏。
- hermes (越界宿主, 非 cc2 范围) 30min bads (DB 复核): zombie_empty_completion×2 +
  NVStream_IncompleteRead×1 — 同越界宿主, 非 cc2 主链。
- **fresh 5min**: cc4101-primary 全 200, 链路当前完全健康。
- 30min cc_requests = **111 ok / 111 total = 100% SR, 0 fallback (0.0%)**, 主链无 ms_gw 触发。
- buffer 日志 (19:25~19:28): 全 attempt=1/5 success (success_text/success_tool_call, elapsed 1~14s),
   无 fail、无 WAIT-/KEYMGR 惩罚。
- /health 实测 19:29: 40006/4101 全 200; 容器 nv_gw Up 16h, cc4101 Up 16h, nv_gw_stable Up 5d.

## 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **111/112 = 99.1%, 1 scoped bad** | ⚠️(R1060 遗留瞬时尾部, 即将滑出) |
| fresh 5min | **全 200, 0 错误** | ✅ 当前健康 |
| 主链 scoped 错误 | 1 (ec39dd9b buffer_exhausted 58949ms, 19:02 CST) — R1060 历史瞬时, ts 距滑出 ~2min | ✅ 非新缺陷 |
| 主链 main fid 281478d0 nv_tier_attempts | 109 × pexec_success (k0=23/k1=20/k2=23/k3=21/k4=22), 0 错误 | ✅ |
| nv_tier_attempts 4×RemoteDisconnected | 全命中坏 fid 52e1ddb6 (hermes 越界宿主), 较上轮 5 条减 1 | ✅(非主链, 低密度) |
| 30min cc_requests | 111/111 = 100% SR, fallback 0 次 (0.0%) | ✅ |
| buffer 日志 | 全 attempt=1/5 success (1~14s), 无 fail/WAIT/KEYMGR | ✅ |
| 容器 | nv_gw Up 16h, cc4101 Up 16h, /health 40006/4101 全 200 | ✅ |

## 下一步
- ec39dd9b (ts 11:01:03 UTC) 距 30min 截点仅 ~2min; **预期下轮 cc4101-primary 0 bad, 主链 100% 干净**。
- 跟踪 SSLEOFError 是否从"低频常态"演成"高密度持续" (若 >10 次/10min 且同窗口多请求 502, 才排查 egress/proxy 出向 mihomo)。
- 单 key 连续多轮 100% 失败才考虑 KEY_FID_BIND 换 fid; 当前 281478d0 100% 干净 (0 错误), 无此需。

## 参数快照 (2026-08-07, 与上轮 R1064 一致, 未动)
- cc4101: PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv,
  FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, CC4101_PRIMARY_FAIL_THRESHOLD=3, CC4101_PRIMARY_SKIP_S=30,
  UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, UPSTREAM_TIMEOUT=90,
  NV_INTEGRATE_KEY_COOLDOWN_S=90, KEY_COOLDOWN_S=30, NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150,
  TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180, MIN_OUTBOUND_INTERVAL_S=10,
  NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- Buffer 5 attempts × 90s = 450s; KeyManager 429→120-600s 指数退避, RemoteDisconnected→5-10s 短惩罚