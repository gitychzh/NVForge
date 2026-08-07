# STATE.md — cc2 自优化 nv_gw 链路 (HM2)

> 当前轮: **R1127 (NOP 巡检轮/不改码 — 确认 6d1ecf8c 归宿 & 主链恢复; cc2 主链 30min 104/105 SR 含同一
> 6d1ecf8c transient 502 (ts 16:03:47 = R1125/R1126 已归因 multi-egress SSLEOF blip, 非新),
> 最近独立 10min 41/41=100% SR 零非-200 主链自愈; tier 错误 8× RD + 1× empty_200 全单请求分布式一次性
> self-heal 未上浮; fallback 0%; 6d1ecf8c 1 次 AKE-FASTM fail-fast 正确)**
> cc4101-primary (主 nv_gw:40006) 实测 30min = **104/105 SR, 1 bad (同 6d1ecf8c, ts 16:03:47, 非新)**
> — 最近独立 10min **41/41 = 100% SR, 零非-200** → 主链完全自愈
> 非-200 归属: **1× buffer_exhausted (cc2 专属, req=6d1ecf8c, avg 43.3s, =R1125/R1126 已归因同一条 transient)**
> fallback: 0% (40min 零 fallback_occurred, 未走 ms_gw)
> tier 错误: 30min 8× NVCFPexecRemoteDisconnected + 1× empty_200, 各 key/time 分散单点
> (k0×3, k1×1, k2×2, k3×1, k4×2 / 15:41~16:20), 全单请求一次性 self-heal 未上浮
> buffer: 最近 30min 除旧 6d1ecf8c 外全 attempt-1 direct flush 无 WAIT/无新 exhaust
> SSLEOF/RD: 延续 [[ssleof-error-transient-egress-blip]] 模式, 全分布式单点, steady background
> 容器 (/health 2026-08-08 ~00:28 CST): nv_gw 200, cc4101 200, dsv4p40066 200 (Up 21h/20h/3d)
> 上轮: R1126 (NOP, 确认 R1125 归因成立; 主链 45/46 含同一 6d1ecf8c transient)

## 本轮 (R1127) 改动 + 依据 + 验证

### 改动: 无 (NOP。30min 唯一 1×502 (req 6d1ecf8c, ts 16:03:47 UTC) 是 R1125/R1126 已完整归因的
### 同一条 transient 多-egress SSLEOF blip, 已老化出新鲜窗口, 无新错误。最近独立 10min 41/41
### =100% SR 零非-200, 主链自愈。fail-fast 仅在该旧 blip 正确生效, 无级联。cc2 范围无配置回归 → 不改码)

### 依据 (本 session 实拉 2026-08-08 ~16:28 UTC)

- **30min nv_requests (cc4101-primary)**: `200|104` + `502|1` = **104/105 SR**; 唯一 502 =
  req **6d1ecf8c, ts 16:03:47 UTC** (=R1125/R1126 已归因那条 transient), 40min 窗口内仅此 1 条非-200。
- **最近独立 10min (cc4101-primary)**: `41|41` = **100% SR, 零非-200** → 主链自愈。
- **30min 错误分类 (cc4101-primary)**: `buffer_exhausted|1` (avg 43.3s) = 同一条 6d1ecf8c。
- **30min nv_tier_attempts 非-success**: 8× NVCFPexecRemoteDisconnected + 1× empty_200,
  各 key/time 分散单点 (k0×3, k1×1, k2×2, k3×1, k4×2 / 15:41~16:20), 全单请求一次性 self-heal
  (后续 attempt 成功), 无 multi-key 连续复发, 未上浮 surface。
- **buffer 日志 (30min)**: 除旧 6d1ecf8c 外全 attempt-1 direct flush success, 无 WAIT/无新 exhaust;
  AKE-FASTM fail-fast 仅在该旧 blip 正确生效 (跳 WaitQueue 省 ~180s)。
- **fallback (40min)**: `fallback_occurred` = 0 — fallback 0%, 未走 ms_gw。
- **容器 /health 2026-08-08 ~00:28 CST**: nv_gw 200, cc4101 200, dsv4p40066 200 — 全链路健康。

### 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| cc2 主链 (40006) 30min | cc4101-primary **104/105 SR, 1 bad** (同一 6d1ecf8c transient, 非新) | ✅ 无新错误 |
| 最近独立 10min | **41/41 = 100% SR, 零非-200** | ✅ 主链自愈 |
| cc2 专属错误分类 | buffer_exhausted ×1 (req 6d1ecf8c, =R1125/R1126 已归因同一条) | ✅ transient |
| fallback 触发率 | 0% (40min 零 fallback_occurred, 未走 ms_gw) | ✅ |
| per-key tier 错误 | 8× RD + 1× empty_200, 全单请求分布式一次性 self-heal 未上浮 | ✅ |
| buffer | 仅旧 6d1ecf8c 1 次 AKE-FASTM fail-fast; 其余全 attempt-1 direct flush 无 WAIT | ✅ fail-fast 正确 |
| container /health | nv_gw 200, cc4101 200, dsv4p40066 200 (Up 21h/20h/3d) | ✅ |

## 下一步
- 延续 NOP。6d1ecf8c 已是三条 NOP round (R1125/1126/1127) 连续确认的同一条 transient, 主链已连续
  独立窗口全绿自愈, 无参数可调。
- **观测 SSLEOF/RD 趋势**: 若窗口回升尖峰 (>30 次/30min) 或出现同 key 多请求连续复发 RD
  (非单请求瞬时), 再查该 key 对应 mihomo 端口线路。当前 8× RD 全分布式单点, steady background 无需动。
- **ms_gw**: ms 链不可调, fallback 0% 未触发, 无需动作。
- 下轮关注: 保持主链连续 100% SR; 若 6d1ecf8c 已彻底老化出 30min+ 窗口后仍 100% 全绿, 可判定
  该 transient 完全闭合。