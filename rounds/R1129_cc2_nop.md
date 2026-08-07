# R1129 — cc2 NOP 巡检轮 (不改码, 6d1ecf8c 第 5 轮确认同一条 transient, 主链连续全绿自愈)

> 轮次: R1129 | 日期: 2026-08-08 (~00:45 CST / 16:45 UTC) | 容器: nv_gw, cc4101
> 上一轮: R1128 (NOP, 第 4 轮确认同一条; 主链 43/43 100% SR)

## 结论
**NOP (不改码)。** 30min cc4101-primary 唯一 1×502 (req **6d1ecf8c**, ts **16:03:04 UTC**) 仍是
R1125~R1128 **已完整归因的同一条 transient 多-egress SSLEOF blip** — 现已第 **5** 轮 NOP 连续确认
同一 req id。该 blip 仍在滚动 30min 窗口内仅因 UTC 边界采样点在 16:03 (非新发生)。
**最近独立 10min = 40/40 = 100% SR, 零非-200** — 主链连续全绿自愈。
tier 错误 8× RD + 1× empty_200 全单请求分布式一次性 transient, 单点 self-heal 未上浮。
fallback 0%, buffer 新窗口全 attempt-1 direct flush 无 WAIT/无新 exhaust。cc2 范围无配置回归 → 不改码。

## 依据 (本 session 实拉 2026-08-08 ~00:45 CST / 16:45 UTC)

- **30min nv_requests (cc4101-primary, 含 request_id)**: `200|107` + `502|1`; 唯一 502 =
  req **6d1ecf8c, ts 16:03:04 UTC, duration_ms=43383, error=buffer_exhausted** — 与 R1125/1126/1127/1128
  完全同一 req id (第 5 轮确认), 窗口内仅此 1 条非-200, 无新错误。
- **最近独立 10min (cc4101-primary)**: `200|40` = **100% SR, 零非-200** — 主链完全自愈。
- **30min 错误分类 (cc4101-primary)**: `buffer_exhausted|1` (avg_dur=43.3s) = 唯一 surface 错误
  = 同一条 6d1ecf8c。
- **30min nv_tier_attempts 非-success**: 8× NVCFPexecRemoteDisconnected + 1× empty_200,
  各 key/time 分散单点 (k0×3, k1×1, k2×1, k3×1, k4×2), 全单请求一次性 self-heal
  (后续 attempt 成功), 无 multi-key 连续复发, 未上浮 surface。
- **buffer 日志 (最近 30min)**: 新窗口全 attempt-1 direct flush success (8c735fdc / d7db93b3 /
  adb5a5d8, verdict=success_tool_call, elapsed 7~12s), 无 WAIT、无新 exhaust。
- **fallback_triggered (30min cc_requests)**: 0 / 110 total = **0%** — 未触发 ms_gw。
- **容器 /health (注入 2026-08-08 ~00:28 CST)**: nv_gw / cc4101 / dsv4p40066 全 200 —
  全链路健康 (Up 26h/21h/5d)。

## 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| cc2 主链 (40006) 30min | cc4101-primary 唯一 1×502 = 同一 6d1ecf8c transient, 无新错误 | ✅ 5 轮确认同一条 |
| 最近独立 10min | **40/40 = 100% SR, 零非-200** | ✅ 主链连续全绿自愈 |
| cc2 专属错误分类 | buffer_exhausted ×1 (req 6d1ecf8c, ts 16:03:04, =R1125~28 同一条) | ✅ transient 老化中 |
| fallback 触发率 | 0% (30min 0/110 fallback, 未走 ms_gw) | ✅ |
| per-key tier 错误 | 8× RD + 1× empty_200, 全单请求分布式一次性 self-heal 未上浮 | ✅ |
| buffer | 新窗口全 attempt-1 direct flush success, 无 WAIT/无新 exhaust | ✅ |
| container /health | nv_gw 200, cc4101 200, dsv4p40066 200 (Up 26h/21h/5d) | ✅ |

## 下一步
- 延续 NOP。6d1ecf8c 已第 5 轮确认同一条 transient (单请求 multi-egress SSLEOF, R1125 已完整归因),
  纵使滚动窗口采样仍偶现, 主链最近独立 10min 40/40 全绿自愈, 无参数可调。
- **关闭判定 (正式)**: 该 blip ts=16:03 UTC 距今已 >45min 未再发生任何同 req / 同 pattern 复发。
  下轮若窗口内零表面错误 (6d1ecf8c 彻底老化出窗口), 正式标记闭合。
- **观测 SSLEOF/RD 趋势**: 若回升尖峰 (>30 次/30min) 或同 key 多请求连续复发 RD, 再查该 key
  对应 mihomo 端口线路。当前 8× RD 全分布式单点, steady background 无需动。
- **ms_gw**: ms 链不可调, fallback 0% 未触发, 无需动作。