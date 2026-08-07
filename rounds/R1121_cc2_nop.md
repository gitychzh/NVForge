# R1121 — cc2 NOP 巡检轮 (不改码)

> 日期: 2026-08-07 ~23:51 CST
> 状态: **cc2 主链 100% SR 零错误; 全量 dsv4f0731_nv 100% SR 零错误零 fallback**

## 结论

cc2 主链 (cc4101-primary 经 nv_gw:40006, primary model=dsv4f0731_nv) 30min = **113/113 = 100.0% SR, 0 bad**。
全量 dsv4f0731_nv = 146/146 = **100.0% SR**, 非-200 = 空。fallback 0% (全走 primary)。
cc2 范围无新错误签名 → **NOP, 不改码**。

## 轮前链路分析数据 (注入 2026-08-07 23:51)

- **30min nv_requests (cc4101-primary)**: status 仅 200 × **113** = 100.0% SR, 0 错误。
- **dsv4f0731_nv 全量**: 146/146 = **100.0% SR** (cc4101-primary 113 + hermes 33)。
- **错误分类**: `(无错误)` — 零错误。**非-200 = 空**, 无 502 / zombie_empty_completion。
- **fallback**: 0% (146 total, fallback_triggered=0, 全走 primary)。
- **nv_tier_attempts 30min**: tier=dsv4f0731_nv, 全 `pexec_success` 为主 (fid 281478d0);
  仅 fid **52e1ddb6** (历史记忆坏 fid — 越界容器 40666 hermes 线泄漏源) 的
  k1 1× `empty_200` + k4 1× `empty_200`
  一次性 distributed transient 单请求 tier 自愈, 未上浮为 surface 错误, 无 multi-key 连续复发
  (本轮无 RD, 比上轮更干净)。
- **buffer 日志 (docker logs --since 30m)**: 全 attempt-1 direct flush (如 req deefa372 elapsed 7.9s,
  req 472ce03f elapsed 3.7s, verdict=success_tool_call), 无重试无级联无 buffer_exhausted 无 WAIT。
- **容器 /health 2026-08-07 ~23:51 CST**: nv_gw http 200 (Up 20h, primary=dsv4f0731_nv, 5 key),
  cc4101 http 200 (Up 20h)。

## 数据表

| 指标 | 值 | 状态 |
|---|---|---|
| cc2 主链 (40006) 30min | cc4101-primary **113/113 = 100.0% SR, 0 bad** | ✅ 全绿 |
| 全量 dsv4f0731_nv | 146/146 = **100.0% SR** 零错误 | ✅ |
| 30min 错误分类 | (无错误) — 非-200 空 | ✅ 零错误 |
| fallback 触发率 | 0% (146 total, 全走 primary) | ✅ |
| per-key tier 错误 | 全 pexec_success (fid 281478d0): k0=21 k1=23 k2=21 k3=23 k4=25; 仅 fid 52e1ddb6 的 k1 1× empty_200 + k4 1× empty_200 一次性 transient 单请求自愈 (无 RD) | ✅ |
| buffer | 全 attempt-1 direct flush (elapsed 3.7-7.9s success_tool_call), 无重试无级联无 WAIT | ✅ |
| container /health | nv_gw 200 (Up 20h), cc4101 200 (Up 20h) | ✅ |

## 依据

- 铁律 2/工作流: SR ≥ 99% 且 fallback < 5% → NOP 巡检轮, 只记数据不改码。
  本轮 SR=100% ≥ 99%, fallback=0% < 5%, 零错误 → **NOP**。
- per-key 2 个错误全部量小 (k1 1× empty_200, k4 1× empty_200), 单请求 distributed transient,
  未上浮为 surface 错误 (nv_requests 零错误), 与历史记忆 bad-fid-52e1ddb6 泄漏模式一致
  (泄漏源=越界容器 40666 hermes 线, 宿主分离)。本轮无 RD, 无 multi-key 连续复发 →
  非配置漂移, 不处置。

## 改动

无 (NOP)。未改源码/env/容器。

## 下一步

- 延续 NOP。cc2 主链连续多轮 (R1096-R1121) 100% SR + zero fallback, 无参数可调。
- **k1/k4 错误** (fid 52e1ddb6): 量小且单请求 self-heal (本轮仅 2× empty_200 无 RD)。仅当
  RD/error 在多请求多 key **连续复发** 才查链路/mihomo 线路。
- 持续观察: 全量非-200=空 (最干净窗口)。zombie_empty_completion 若在 caller=hermes 线回升且
  宿主同机再查归属; 出现 caller=cc4101-primary 的错误才进 cc2 指标并处置。

## 参数快照 (nv_gw + cc4101, 本轮无变化)

- nv_gw: NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv; UPSTREAM_TIMEOUT=90; NV_INTEGRATE_KEY_COOLDOWN_S=90;
  KEY_COOLDOWN_S=30; NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150; TIER_TIMEOUT_BUDGET_S=180;
  NVU_DISABLE_MS_FALLBACK=0; NVU_FORCE_STREAM_UPGRADE=0; TIER_COOLDOWN_S=180; MIN_OUTBOUND_INTERVAL_S=10;
  NVU_BUFFER_CALLERS=cc4101-primary,openclaw2; NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- cc4101: FALLBACK_UPSTREAM_MODEL=glm5_2_ms; UPSTREAM_TIMEOUT=130; CC4101_PRIMARY_FAIL_THRESHOLD=3;
  CC4101_STREAM_TOTAL_DEADLINE_S=470; CC4101_PRIMARY_SKIP_S=30; PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv;
  UPSTREAM_IDLE_TIMEOUT=150; PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages;
  FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions; PRIMARY_HEADER_TIMEOUT=400