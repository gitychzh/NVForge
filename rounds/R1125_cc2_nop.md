# R1125 — cc2 NOP 巡检轮 (不改码, 附 1×502 事故注释)

> 轮次: R1125 | 日期: 2026-08-08 (~00:05 CST) | 容器: nv_gw, cc4101
> 上一轮: R1124 (NOP, cc4101-primary 106/106=100%)

## 结论
**NOP (不改码)。** cc2 主链 (cc4101-primary 经 nv_gw, primary model=dsv4f0731_nv) 30min
**100/101 = 99.0% SR, 1× 502 buffer_exhausted** — 中断 R1096-R1124 连续 100% SR。
该 1× 502 **非配置漂移**, 由 transient 多-egress SSLEOFError blip (req=6d1ecf8c 43s 内 3 连续
不同 egress 端口全 SSLEOF) + ms_gw fallback 同一时刻瞬时失败 双重叠加触发; fail-fast 已正确
生效防级联 (跳 WaitQueue 省 ~180s), ms_gw 现已恢复 → 无需改码。

## 轮前链路分析 (注入 2026-08-08 00:05 CST + 本 session 实拉复核)

- **30min nv_requests (cc4101-primary)**: `200|100` (avg 10s) + `502|1` (avg 43.3s, buffer_exhausted)
  = **100/101 = 99.0% SR**。
- **30min 全量**: dsv4f0731_nv `200|135` (cc4101-primary 100 + hermes 35) + `502|1`。全量 SR=99.3%。
- **30min 错误分类**: `buffer_exhausted|1|43383ms` — 唯一 surface 错误 (cc2 专属)。
- **fallback**: `f|136` → 0% (ms_gw 仅在 NVCF 5 败后 fail-fast 触发 1 次, 且失败)。
- **30min nv_tier_attempts per-key**:
  - k0~k4 全 `pexec_success` 为主 (19-22× 各 key)。
  - 一次性分布式: `0|RD 1×`, `2|RD 1×`, `4|RD 1× + empty_200 1×` — 单 key 单请求 transient,
    未上浮为 surface 错误, 无 multi-key 连续复发。
- **buffer 日志 (req=6d1ecf8c 完整链)**:
  - attempt-1 k5(:7899) SSLEOF → AKE → 5s/10s backoff → retry
  - attempt-2 k1(:7901) SSLEOF → AKE → retry
  - attempt-3 k2(:7894) SSLEOF → AKE
  - **3 连续 AKE ≥3 → AKE-FASTM fail-fast 生效** → 跳 WaitQueue → 走 ms_gw
  - ms_gw fallback 同一时刻瞬时失败 → 502 buffer_exhausted 给 CC

## 事故归因 (1× 502 buffer_exhausted)

`req=6d1ecf8c` (input=84911c, thinking=True) 在 **43s 内 3 个连续 buffer attempt 命中 3 个不同
egress 端口** 的 SSLEOFError (:7899, :7901, :7894) → 3 consecutive all_keys_exhausted → fail-fast。
三个不同 mihomo 端口几乎同时 SSLEOF = **共享上游 (NVCF/mihomo 网关级) 瞬时多-egress blip**,
非单一端口可修。fail-fast 按设计正确生效 (省 ~180s WaitQueue)。唯一使该请求从"tier 重试会自愈"
变成硬 502 的是 **ms_gw fallback 同一时刻瞬时失败** — 但 ms_gw 现健康 (Up 2 days, /health 200),
且 ms_gw 属 ms 链 (proxy/ms-gw, 铁律 3 不碰), 其为一次性故障非本链路配置回归。
SSLEOF 6h 总 230 次, 但集中 18:00-23:00 前一时段 (224 次), 本窗口回落至 steady 背景
(4-16 次/15min, 非尖峰), 与历史 [[ssleof-error-transient-egress-blip]] 自愈模式一致。

## 变更
无 (NOP)。fail-fast 链路行为正确无需调参; SSLEOF 为上游 egress 级无法在 nv_gw 单点修复;
ms_gw 瞬时失败属 ms 链不碰。仅同步 STATE.md。

## 验证
- 30min cc2 SR 复核 CLI: **total=101 ok=100 sr=99.0%**。
- `AKE-FASTM` 触发 1 次, `WAIT-` 0 次 → fail-fast 防级联正确。
- ms_gw `/health` 200 (Up 2 days) — fallback 目标已恢复。
- 容器 (docker ps): nv_gw, cc4101 均正常运行。

## 下一步
- 延续 NOP。本窗口 1× 502 为 transient 多-egress SSLEOF + ms_gw 瞬时失败双重叠加的一次性碰撞,
  非系统性回归。SSLEOF 已回落 background, 无参数可调。
- **观测 SSLEOF 趋势**: 若 6h 窗口回升到尖峰 (>30 次/30min) 或连续多请求多 key 复发 SSLEOF
  (非单请求 2-3 连中), 则查 mihomo 上游线路/NVCF egress (3 端口共享原因)。当前为稳态无需动。
- **ms_gw**: ms 链不可调。仅记录其 1 次瞬时 fallback 失败为该请求 502 的叠加因素。
- 下轮关注: cc4101-primary 是否恢复连续 100% SR。