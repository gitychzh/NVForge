# R1128 — cc2 NOP 巡检轮 (不改码, 6d1ecf8c 第 4 轮确认同一条 transient, 主链连续全绿自愈)

> 轮次: R1128 | 日期: 2026-08-08 (~00:40 CST / 16:40 UTC) | 容器: nv_gw, cc4101
> 上一轮: R1127 (NOP, 确认 R1125/R1126 归因成立; 主链 41/41 100% SR)

## 结论
**NOP (不改码)。** 40min cc4101-primary 唯一 1×502 (req **6d1ecf8c**, ts **16:03:04 UTC**) 仍是
R1125/R1126/R1127 **已完整归因的同一条 transient 多-egress SSLEOF blip** — 现已第 **4** 轮 NOP 连续确认。
**最近独立 10min (blip 老化后) = 43/43 = 100% SR, 零非-200** — 主链连续全绿自愈。
tier 错误 8× RD + 1× empty_200 全为单请求分布式一次性 transient, 单点 self-heal 未上浮。
fallback 0%, buffer 新窗口全 attempt-1 direct flush 无 WAIT/无新 exhaust。cc2 范围无配置回归 → 不改码。

## 依据 (本 session 实拉 2026-08-08 ~00:35 CST / 16:35 UTC)

- **40min nv_requests (cc4101-primary, 含 request_id)**: `200|146` + `502|1`; 唯一 502 =
  req **6d1ecf8c, ts 16:03:04 UTC, duration=43383ms, error=buffer_exhausted** — 与 R1125/R1126/R1127
  完全同一 req id, 40min 窗口仍仅此 1 条非-200, 全无新错误。
- **最近独立 10min (cc4101-primary, blip 老化后)**: `200|43` = **100% SR, 零非-200** — 主链完全自愈。
- **30min 错误分类 (cc4101-primary)**: `buffer_exhausted|1` — 唯一 surface 错误 = 同一条 6d1ecf8c
  (avg_dur=43.3s, 与其 buffer 3×90s fail-fast 链吻合)。
- **30min nv_tier_attempts 非-success**: 8× NVCFPexecRemoteDisconnected + 1× empty_200,
  各 key/time 分散单点 (k0×3, k1×1, k2×2, k3×1, k4×2), 全单请求一次性 self-heal
  (后续 attempt 成功), 无 multi-key 连续复发, 未上浮 surface。
- **buffer 日志 (最近 30min)**: 新窗口全 attempt-1 direct flush success (0f9736bb / a7b2523a /
  59dc042b 等, verdict=success_tool_call, elapsed 7~12s), 无 WAIT、无新 exhaust; fail-fast 仅旧 blip。
- **fallback_occurred (40min)**: 0 — fallback 0%, 未触发 ms_gw。
- **容器 /health 2026-08-08 ~00:35 CST**: nv_gw 200 (5 key, pexec 全模型 200), cc4101 200
  (primary dsv4f0731_nv), dsv4p40066 200 — 全链路健康。

## 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| cc2 主链 (40006) 40min | cc4101-primary 唯一 1×502 = 同一 6d1ecf8c transient, 无新错误 | ✅ 4 轮确认同一条 |
| 最近独立 10min | **43/43 = 100% SR, 零非-200** | ✅ 主链连续全绿自愈 |
| cc2 专属错误分类 | buffer_exhausted ×1 (req 6d1ecf8c, ts 16:03:04, =R1125/26/27 同一条) | ✅ transient 老化中 |
| fallback 触发率 | 0% (40min 零 fallback, 未走 ms_gw) | ✅ |
| per-key tier 错误 | 8× RD + 1× empty_200, 全单请求分布式一次性 self-heal 未上浮 | ✅ |
| buffer | 新窗口全 attempt-1 direct flush success, 无 WAIT/无新 exhaust | ✅ |
| container /health | nv_gw 200, cc4101 200, dsv4p40066 200 | ✅ |

## 下一步
- 延续 NOP。6d1ecf8c 已第 4 轮确认归宿 (单请求 transient multi-egress SSLEOF, R1125 已完整归因),
  且该 blip (ts 16:03) 已老化出 30min 窗口外, 主链最近 10min 43/43 全绿自愈, 无参数可调。
- **观测 SSLEOF/RD 趋势**: 若回升尖峰 (>30 次/30min) 或出现同 key 多请求连续复发 RD
  (非单请求瞬时), 再查该 key 对应 mihomo 端口线路。当前 8× RD 全分布式单点, steady background。
- **ms_gw**: ms 链不可调, fallback 0% 未触发, 无需动作。
- **关闭判定**: 6d1ecf8c 已连续 4 轮 NOP 确认同一条 transient 无误新, 且已老化出 30min+ 窗口
  后主链仍 100% 全绿 — 可判定该 transient 基本闭合。下轮若窗口内仍零表面错误, 正式标记闭合。