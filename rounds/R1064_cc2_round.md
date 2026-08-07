# R1064 — cc2 自优化 nv_gw 链路 (HM2) — NOP 巡检轮/不改码

> 主链 cc4101-primary (nv_gw:40006) 30min = **111/112 = 99.1%, 1 scoped bad**;
> 唯一 scoped 502 = req **ec39dd9b** (buffer_exhausted 58949ms, created_at 11:02:02 UTC = 19:02 CST) =
> **R1060 已溯源的瞬时 (3 连 SSLEOFError + ms_gw down, 已自愈)**, 非新缺陷;
> fresh 5min = **20/20 全 200 干净**, 链路当前完全健康;
> 主链 main fid **281478d0** nv_tier_attempts 全 pexec_success (109), **0 错误**;
> 全部 NVCFPexecRemoteDisconnected (5 条, k0×1/k1×2/k2×1/k3×1) 命中 hermes 越界坏 fid **52e1ddb6**, 非主链;
> 30min cc_requests fallback = **0 次 / 0.0%**;
> 容器: nv_gw Up 16h, cc4101 Up 15h, /health 40006/4101 全 200.

## 改动: 无 (NOP)

唯一 scoped bad 仍是 R1060 已溯源瞬时 ec39dd9b, 现处 30min lookback 尾部; 主链 fid 281478d0 0 错误; cc4101-primary fresh 5min 100% 干净且 0 fallback; 无参数可调。

## 依据 (轮前链路分析 19:22 CST + DB/容器复核 2026-08-07)

- 30min cc4101-primary (nv_gw:40006) = **111/112 = 99.1%, 1 scoped bad** (per-DB 复核, 较轮前注入 109 略增为 111 因窗口随时间滑动)。
- **fresh 5min = 20/20 全 200, 0 错误** → 当前链路完全健康。
- 唯一 scoped 502 (DB 铁证, `request_id=ec39dd9b`): buffer_exhausted 58949ms,
  **created_at=11:02:02 UTC = 19:02 CST**, 即 **R1060 已溯源的瞬时** (attempt1/2/3 于不同 key/出口
  连 3 SSLEOFError → 3 consecutive all_keys_exhausted → AKE fail-fast ≥3 CLOSED 正确跳过 WaitQueue →
  ms_gw 同步 down → 才 502; 19:02:27 已 200 自愈)。其 nv_tier_attempts 本轮已 0 行 (旧 attempt 记录已过期),
  进一步证明为历史瞬时。**仍落 lookback 尾部 (19:02 距今 ~8min), 抵触仅耗时, 非新缺陷。**
- 主链 main fid **281478d0** nv_tier_attempts (30min) = **109 × pexec_success, 0 错误** (全 5 key)。
  另 5 条 NVCFPexecRemoteDisconnected (k0×1/k1×2/k2×1/k3×1) 全命中**坏 fid 52e1ddb6**
  → hermes 越界宿主泄漏 (V40531 持续溯源), 非 cc2 主链。
- hermes (越界宿主, 非 cc2 范围) 30min 错误 (DB 复核): zombie_empty_completion×2 (59bd8bb6 19:13,
  20982d20 19:21) + NVStream_IncompleteRead×1 (36b31ca1 18:01) — 同宿主, 非主链。
- 30min cc_requests fallback = **0 次 / 0.0%**, 主链无 ms_gw 触发。
- buffer 日志 (19:23~19:24): 全 attempt=1/5 success (success_tool_call, elapsed 7~12s), 无 fail,
  无 WAIT-/KEYMGR 惩罚。
- /health 实测: 40006/4101 全 200; 容器 nv_gw Up 16h, cc4101 Up 15h, nv_gw_stable Up 5d.

## 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **111/112 = 99.1%, 1 scoped bad** | ⚠️(R1060 遗留瞬时尾部) |
| fresh 5min | **20/20 全 200, 0 错误** | ✅ 当前健康 |
| 主链 scoped 错误 | 1 (ec39dd9b buffer_exhausted 58949ms, 19:02 CST) — R1060 历史瞬时已自愈, 落窗口尾部 | ✅ 非新缺陷 |
| 主链 main fid 281478d0 nv_tier_attempts | 109 × pexec_success, 0 错误 | ✅ |
| nv_tier_attempts 5×RemoteDisconnected | 全命中坏 fid 52e1ddb6 (hermes 越界宿主) | ✅(非主链) |
| 30min cc_requests | fallback 0 次 (0.0%) | ✅ |
| buffer 日志 | 全 attempt=1/5 success (7~12s), 无 fail/WAIT/KEYMGR | ✅ |
| 容器 | nv_gw Up 16h, cc4101 Up 15h, /health 40006/4101 全 200 | ✅ |

## 下一步
- 保持 NOP 观察。ec39dd9b (19:02 CST) 再过 ~8min 彻底滑出 30min lookback; 预期下轮 cc4101-primary 0 bad。
- 跟踪 SSLEOFError 是否从"低频常态"演成"高密度持续" (若 >10 次/10min 且同窗口多请求 502, 才排查 egress/proxy 出向 mihomo)。
- 单 key 连续多轮 100% 失败才考虑 KEY_FID_BIND 换 fid; 当前 281478d0 100% 干净 (0 错误), 无此需。

## 参数快照 (2026-08-07, 与上轮 R1063 一致, 未动)
- cc4101: PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv,
  FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, CC4101_PRIMARY_FAIL_THRESHOLD=3, CC4101_PRIMARY_SKIP_S=30,
  UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, UPSTREAM_TIMEOUT=90,
  NV_INTEGRATE_KEY_COOLDOWN_S=90, KEY_COOLDOWN_S=30, NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150,
  TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180, MIN_OUTBOUND_INTERVAL_S=10,
  NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- Buffer 5 attempts × 90s = 450s; KeyManager 429→120-600s 指数退避, RemoteDisconnected→5-10s 短惩罚