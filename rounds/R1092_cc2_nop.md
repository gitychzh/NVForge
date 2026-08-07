# R1092 cc2 NOP — primary 98/99=99.0% SR (1 bad=502 buffer_exhausted R1088 同 req=9baaf179 历轮已知容器尾迹, self-heal 复窗口全200); per-key 全 pexec_success 零 tier 错误; fallback 0.0%; buffer attempt-1 直flush 秒回 (k2 一次性 5s backoff) 零级联

> 轮前注入: 2026-08-07 21:38:33 CST  |  容器 nv_gw / cc4101: Up 18h
> 主链实测 30min = **98/99 = 99.0% SR, 1 bad** (同 historical tail, 非新错误)

## 本轮判断

**NOP 巡检轮 (不改码)。** 主链 SR 99.0%, 唯一 502 为 R1088/R1089/R1090/R1091 **完全同一 request_id=9baaf179** 的历轮已知容器尾迹, self-heal 复窗口零新增 502, 无配置漂移, 无持续分布, 无参数可调。

## 改动

无 (NOP)。

## 依据 (轮前注入 + DB/日志复核 2026-08-07 21:4x CST)

- **30min cc4101-primary (主 nv_gw:40006) = 97×200 + 1×502 = 98 total, SR = 99.0%**
- **唯一 bad 定位铁证**: `SELECT request_id,status,error_type,duration_ms,created_at WHERE status!=200 AND caller='cc4101-primary' AND created_at>now()-interval '60 min'`
  → **req=9baaf179, 502 buffer_exhausted, 40665ms, 2026-08-07 13:15:13 UTC**。
  该 request_id 与 R1088~R1091 已根因 req **逐字一致** (历轮已知 124K thinking 流多 IP 瞬时 SSLEOF egress blip 尾迹),
  **无任何新签名 502**。
- **self-heal 铁证**: `created_at>'2026-08-07 13:15:13.991953+00' AND status!=200` → **0 条** (9baaf179 后无任何新增 502)。
- **cc_requests 真实 SR (含 fallback)**: 98/98 = **100.0%** (0 失败), **fallback 0/98 = 0.0%** → 复窗口全走主链, bad 已计 NV 非成功。
- **tier 错误**: 30min 仅 `pexec_success` × 96, **零 tier 错误** (无 RD / 429 / cooldown 堆积)。
- **buffer 日志** (--since 30m)：复窗口绝大多数 attempt-1 verdict=success_tool_call/success_text 直 flush 秒回 (1-14s)。
  唯一一次 attempt 重试: req=95d09ffd, attempt-1 NVCF chain fail on k2 all_keys_exhausted=True → 5s backoff →
  attempt-2 success_tool_call (21s) 正常恢复 → **self-heal 机制健壮, 一次性输入段抖动, 非持续分布**。
- 容器 /health 实测 2026-08-07: 40006 nv_gw 200, 4101 cc4101 200, 40066 dsv4p_nv40066 200;
  docker ps: nv_gw / cc4101 Up 18h, dsv4p_nv40066 Up 3d。

## 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **97/98 = 99.0% SR, 1 bad** (R1088 同 req=9baaf179, 已根因) | ⚠️→self-heal 复窗口 0 新增 502 |
| 30min 错误分类 | 仅 1× buffer_exhausted (历轮已知容器尾迹) | ✅ 非新错误 |
| cc_requests 真实 SR | 98/98 = 100.0%, fallback 0/98 = 0.0% | ✅ |
| per-key / tier 错误 | 5 key 全 pexec_success (96); **零 tier 错误** | ✅ |
| buffer | 复窗口 attempt-1 直flush 秒回; 唯一 k2 5s backoff 后 attempt-2 恢复 | ✅ self-heal 正常 |
| 容器 /health | 40006/4101/40066 全 200; nv_gw/cc4101 Up 18h | ✅ |

## 下一步
- 保持 NOP 观察。本轮 1 transient 502 = R1088~R1091 完全同一 req=9baaf179 (历轮已知 124K thinking 流瞬时 SSLEOF egress blip
  尾迹), AKE fail-fast + 复窗口 attempt-1 秒回证明 self-heal 机制健壮, 非配置漂移。
- 关注点: 若同一 egress 代理线路在未来多轮连续出现同一 req 级 SSLEOFError + attempt 重试 (不再让 attempt-1 直flush),
  才查该 mihomo 代理端口; 当前一次性 k2 抖动无需动作。
- 持续 clean ≥ 数轮后再评估是否需对 124K+ thinking 大流裁减 (buffer_exhausted 概率随 input 增大属模型/流特性, 非链路 bug)。

## 参数快照 (未动, 与上轮 R1091 一致)
- cc4101: PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv,
  FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, CC4101_PRIMARY_FAIL_THRESHOLD=3,
  CC4101_PRIMARY_SKIP_S=30, UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, UPSTREAM_TIMEOUT=90,
  NV_INTEGRATE_KEY_COOLDOWN_S=90, KEY_COOLDOWN_S=30, NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150,
  TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180, MIN_OUTBOUND_INTERVAL_S=10,
  NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- Buffer 5 attempts × 90s = 450s; KeyManager 429→120-600s 指���退避, RemoteDisconnected→5-10s 短惩罚