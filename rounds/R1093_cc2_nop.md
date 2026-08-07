# R1093 cc2 NOP — primary 103/104=99.0% SR (1 bad=502 buffer_exhausted R1088 已知 req=9baaf179 尾迹, self-heal 复窗口零新增502); cc_requests 96/96=100% fallback 0%; buffer attempt-1 直flush 4-10s 零重试; 3h 观察发现 buffer_exhausted 类级 ~1/h 复现 (3 distinct req) 列为下一轮关注点

> 轮前注入: 2026-08-07 21:42:33 CST  |  容器 nv_gw: 23h, cc4101: 18h
> 主链实测 30min = **103/104 = 99.0% SR, 1 bad** (历史已知 req=9baaf179 尾迹, 非新错误)

## 本轮判断

**NOP 巡检轮 (不改码)。** 主链 SR 99.0%, 唯一 502 仍为 R1088~R1092 **同一 request_id=9baaf179** 的历轮已知容器尾迹, self-heal 复窗口零新增 502, 无配置漂移, 无持续错误分布, 无参数可调。

**⚠️ 3h 级别新观察 (仅监测, 不动作)**: 拉 3h horizon 发现 buffer_exhausted 502 由 **3 个 distinct request_id** 组成 —
`ec39dd9b` (11:02, 58.9s)、`c107bc7e` (12:19, 62.8s)、`9baaf179` (13:15, 40.7s), 呈**类级 ~1/h 复现**, 不再是严格"单一已知尾迹"。
均同属 `buffer_exhausted` 类 (124K+ thinking 大流瞬时 egress SSLEOF blip 耗尽 buffer budget), 每次均 self-heal 零级联。
作为下一轮监测信号列入"下一步", 本轮不改 (SR 仍≥99%, fallback 0%, buffer 自愈 100%)。

## 改动

无 (NOP)。

## 依据 (轮前注入 + DB/日志复核 2026-08-07 21:4x CST)

- **30min cc4101-primary (主 nv_gw:40006) = 103×200 + 1×502 = 104 total, SR = 99.0%**
- **唯一 bad 定位铁证**: `status!=200 AND caller='cc4101-primary' AND created_at>now()-interval '90 min'` → **req=9baaf179, 502 buffer_exhausted,
  40665ms, 2026-08-07 13:15:13 UTC**, 与 R1088~R1092 已根因 req **逐字一致**, 无任何新签名 502。
- **self-heal 铁证**: `created_at>'2026-08-07 13:15:13 UTC' AND status!=200` → **0 条** (9baaf179 后复窗口零新增 502)。
- **cc_requests 真实 SR (含 fallback)**: 96/96 = **100.0%**, **fallback 0/96 = 0.0%** → 复窗口全走主链, bad 已计 NV 非成功。
- **tier 错误**: 30min 仅 `pexec_success` 全 key (k0 20 / k1 17 / k3 20 / k4 22, k2 23+1 transient RD); **零持续 tier 错误**
  (唯一 k2 1× NVCFPexecRemoteDisconnected = 一次性输入段抖动, 非分布)。
- **buffer 日志** (--since 2h, 复窗口 21:42-21:45 CST): 每条 attempt-1 verdict=success_tool_call 直 flush, 4-10s 秒回,
  **零 attempt 重试**; buffer self-heal 完全健康。
- 容器 /health 实测 2026-08-07: 40006 nv_gw 200, 4101 cc4101 200, 40066 dsv4p_nv40066 200。

## 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **103/104 = 99.0% SR, 1 bad** (R1088 同 req=9baaf179, 已根因) | ⚠️→self-heal 复窗口 0 新增 502 |
| 30min 错误分类 | 仅 1× buffer_exhausted (历轮已知容器尾迹) | ✅ 非新错误 |
| cc_requests 真实 SR | 96/96 = 100.0%, fallback 0/96 = 0.0% | ✅ |
| per-key / tier 错误 | 5 key 全 pexec_success; 仅 k2 1× 一次性 RD | ✅ 零持续 tier 错误 |
| buffer | 复窗口 attempt-1 直flush 4-10s 秒回, **零重试** | ✅ self-heal 完全健康 |
| 3h buffer_exhausted 类级 | ec39dd9b/c107bc7e/9baaf179 三 distinct req, ~1/h | ⚠️ 监测, 不改 |
| 容器 /health | 40006/4101/40066 全 200 | ✅ |

## 下一步
- 保持 NOP 观察。本轮 SR 99.0% (1 bad=9baaf179 已知尾迹), fallback 0%, buffer 自愈完全正常, 无动作。
- **新关注点 (3h 类级复现)**: 3h 内 buffer_exhausted 502 由 3 个 distinct request_id 组成 (ec39dd9b/c107bc7e/9baaf179),
  呈 ~1/h 类级复现。这不再是"单一已知尾迹", 而是 **124K+ thinking 大流在高峰期瞬时 egress SSLEOF blip 耗尽 buffer budget 的低频类事件**。
  当前每次均 self-heal 零级联, SR 仍≥99%, 但若未来多轮保持 ~1/h 稳定复现 (不再衰减), 需重新评估:
  ① 是否对 ~124K+ 超大 input thinking 流做不 buffering 直通 (skip buffer, 避免 450s 预算被一次大流耗尽);
  ② 或放大 NVU_BUFFER_TIMEOUT_STAIRS 末级预算, 给大流出更高容错。
  本轮不动作, 等 2-4 轮观察该 ~1/h 类级是否衰减或稳定后再议。

## 参数快照 (未动, 与上轮 R1092 一致)
- cc4101: PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv,
  FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, CC4101_PRIMARY_FAIL_THRESHOLD=3,
  CC4101_PRIMARY_SKIP_S=30, UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, UPSTREAM_TIMEOUT=90,
  NV_INTEGRATE_KEY_COOLDOWN_S=90, KEY_COOLDOWN_S=30, NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150,
  TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180, MIN_OUTBOUND_INTERVAL_S=10,
  NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- Buffer 5 attempts × 90s = 450s (NVU_BUFFER_MAX_RETRIES=5, NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90);
  KeyManager 429→120-600s 指数退避, RemoteDisconnected→5-10s 短惩罚