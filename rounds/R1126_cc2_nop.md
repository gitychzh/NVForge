# R1126 — cc2 NOP 巡检轮 (不改码, 确认 R1125 归因成立)

> 轮次: R1126 | 日期: 2026-08-08 (~00:15 CST / 16:14 UTC) | 容器: nv_gw, cc4101
> 上一轮: R1125 (NOP, 100/101=99.0% SR, 1×502 已归因 transient 多-egress SSLEOF)

## 结论
**NOP (不改码)。** 本窗口是 R1125 的 9 分钟后 re-slice —— 唯一的 1×502 (req 6d1ecf8c, 16:03:04)
仍是 R1125 已完整归因的**同一条 transient 多-egress SSLEOF blip**, 无新错误。
**R1125 分析时刻 (16:05 UTC) 之后: 39/39 = 100% SR, 零非-200。** 链路已自愈。
fail-fast 机制在 blip 中正确生效 (3 AKE → AKE-FASTM → 跳 WaitQueue 省 ~180s), 无级联。
cc2 范围无配置回归 → 不改码, 纯状态确认。

## 依据 (本 session 实拉 2026-08-08 ~16:14 UTC)

- **15min nv_requests (cc4101-primary)**: `200|45` + `502|1` (req 6d1ecf8c, 即 R1125 已归因那条,
  ts=16:03:04 早于 16:05 分析时刻) = 45/46 SR; 含叠加旧 502。
- **R1125 分析时刻 (16:05) 之后独立窗口**: `39|39|0` = **100% SR, 零非-200** — R1125 归因成立。
- **30min 错误分类**: `buffer_exhausted|1|43383ms` — 唯一 surface 错误 = 同一条 6d1ecf8c。
- **30min nv_tier_attempts 非-success**: 仅 6× 一次性分布式单请求 transient, 各 key/time 分散
  (k4 empty_200 15:40, k2 RD 15:56, k4 RD 16:04, k0 RD 16:05×2, k2 empty_200 16:12),
  全单点 self-heal, 无 multi-key 连续复发, 未上浮 surface。
- **buffer 日志 (req=6d1ecf8c 完整链)**: attempt-1 k5(:7899) SSLEOF → AKE; attempt-2 k1(:7901)
  SSLEOF → AKE; attempt-3 k2(:7894) SSLEOF → AKE → **AKE-FASTM fail-fast 正确生效** →
  跳 WaitQueue(省 ~180s) → ms_gw 同刻瞬时失败 → 502。符合 [[ssleof-error-transient-egress-blip]]。
- **容器 /health (2026-08-08 ~00:14 CST)**: nv_gw 200, cc4101 200, dsv4p40066 200 — 全链路健康。

## 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| cc2 主链 (40006) 15min | cc4101-primary **45/46 SR, 1 bad** (同一 6d1ecf8c transient) | ✅ 无新错误 |
| R1125 后独立窗口 | **39/39 = 100% SR, 零非-200 (16:05 UTC 之后)** | ✅ 自愈 |
| cc2 专属错误分类 | buffer_exhausted ×1 (req 6d1ecf8c, =R1125 已归因同一条) | ✅ transient |
| fallback | 0% (ms_gw 仅 fail-fast 瞬时 1 次失败, 现健康) | ✅ |
| per-key tier 错误 | 6× 一次性分布式 transient (empty_200 ×2, RD ×4), 单点 self-heal 未上浮 | ✅ |
| buffer | 1 次 AKE-FASTM fail-fast (req 6d1ecf8c), 其余全 attempt-1 direct flush | ✅ fail-fast 正确 |
| container /health | nv_gw 200, cc4101 200, dsv4p40066 200 | ✅ |

## 下一步
- 延续 NOP。确认 R1125 归因: 1×502 = 同一条 transient 多-egress SSLEOF blip, 非系统性回归。
  R1125 分析时刻后 39/39 全绿, 链路自愈, 无参数可调。
- **观测 SSLEOF 趋势**: 若窗口回升尖峰 (>30 次/30min) 或出现多请求多 key 连续复发 SSLEOF
  (非单请求 2-3 连中), 再查 mihomo 上游线路/NVCF egress。当前 steady background 无需动。
- **ms_gw**: ms 链不可调, 仅记录其 fail-fast 瞬时失败为该 502 的叠加因素, 现已恢复。