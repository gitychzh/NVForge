# STATE.md — cc2 自优化 nv_gw 链路 (HM2)

> 当前轮: **R1140 (NOP 巡检轮/不改码 — 30min 主链零表面错误, cc2-primary
> 200|109=100% SR, 0 行非-200; 唯一 surface 错误 NVStream_IncompleteRead 1× (502)
> 归属 hermes 非 cc2; 全 caller dsv4f0731_nv 138/139=99.3%; tier 错误仅 RD 4× (k0/k2/k4)
> + empty_200 1× (k2) 共 5 次, 单点分布式 transient self-heal, 低频下沉稳态;
> buffer 全 attempt-1 direct flush, 无 WAIT/无 exhaust; fallback 0% (109 行 0 触发))**
> cc4101-primary (主 nv_gw:40006) 实测 30min = **0 行非-200** — 主链全绿
> 非-200 归属: **hermes 1× NVStream_IncompleteRead (502, 55.5s), cc2 0 行** — cc2 零表面错误
> fallback: 0% (30min cc_requests 109 行 fallback_triggered=0, 未走 ms_gw)
> tier 错误: 30min NVCFPexecRemoteDisconnected 4× (k0 1/k2 1/k4 2) + empty_200 1× (k2),
> 共 5 次, 各 key/time 分散单点 self-heal 未上浮 (低频下沉稳态, 延续 [[ssleof-error-transient-egress-blip]])
> buffer: 全 attempt-1 direct flush (success_tool_call/success_text), 无 execute_failed/
> 无 backoff/无 WAIT/无新 exhaust
> 容器 (注入 2026-08-08 01:15): nv_gw 运行 26h, cc4101 21h 稳定未重启
> 上轮: R1139 (NOP, 主链零表面错误 100% SR)

## 本轮 (R1140) 改动 + 依据 + 验证

### 改动: 无 (NOP。30min cc2-primary 0 行非-200 (200|109 = 100% SR), 主链全绿。
### 唯一 surface 错误 NVStream_IncompleteRead 1× (502) 归属 hermes 非 cc2。tier 错误
### 5 次非-success (RD 4× k0/k2/k4 + empty_200 1× k2), 分布式单点 self-heal 未上浮,
### 低频下沉稳态。buffer 全 attempt-1 direct flush, fallback 0% (109 行 0 触发)。
### cc2 范围无配置回归 → 不改码)

### 依据 (本 session 轮前注入 + 实查 2026-08-08 01:15)

- **30min cc2-primary (nv_requests 实查)**: `200|109` = **0 行非-200, 100% SR** — 主链全绿。
- **30min 非-200 归属 (注入)**: NVStream_IncompleteRead 1× (502, 55488ms) **归属 hermes** 非 cc2
  (hermes|dsv4f0731_nv|502|1, hermes 共 30 请求 29×200+1×502); cc2 = 0 行 surface 错误。
- **30min 全 caller SR (注入)**: dsv4f0731_nv `138/139 = 99.3%` (cc4101-primary 109 + hermes 29×200)。
- **30min nv_tier_attempts 非-success (注入)**: NVCFPexecRemoteDisconnected 4× (k0 1/k2 1/k4 2)
  + empty_200 1× (k2), 共 5 次, 各 key/time 分散单点 self-heal, 无同 key 连续复发, 未上浮 surface。
  低频下沉稳态 (延续 [[ssleof-error-transient-egress-blip]])。
- **buffer 日志 (实查)**: 全 attempt-1 direct flush (verdict success_tool_call/success_text,
  elapsed 2~13s), 无 execute_failed/无 backoff/无 WAIT/无新 exhaust。
- **fallback (实查)**: 30min cc_requests 109 行, fallback_triggered 0 = **0%** — 未触发 ms_gw。
- **容器 (注入)**: nv_gw 26h, cc4101 21h — 稳定运行未重启。

### 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| cc2 主链 (40006) 30min | **200|109 = 0 行非-200, 100% SR** | ✅ 零表面错误 |
| 非-200 归属 | NVStream_IncompleteRead 1× (502, 55.5s) → **hermes**, cc2 0 行 | ✅ hermes 侧 |
| 全 caller SR (30min) | dsv4f0731_nv 138/139 = 99.3% | ✅ |
| fallback 触发率 | 0% (30min 109 行, 未走 ms_gw) | ✅ |
| per-key tier 错误 | RD 4× (k0 1/k2 1/k4 2) + empty_200 1× (k2), 共 5 次, 单点分布式 self-heal 未上浮 | ✅ (低频下沉) |
| buffer | 全 attempt-1 direct flush, 无 WAIT/无 exhaust | ✅ |
| container | nv_gw 26h, cc4101 21h | ✅ |

## 下一步
- 延续 NOP。主链滚动 30min 零表面错误、fallback 0%、buffer 常态 direct flush + 低频单点
  self-heal, 无参数可调。
- 持续观察 tier 分布式单点 self-heal (RD/empty_200)。本轮 k4 RD 2× (延续 R1139), 若有同 key
  多请求连续复发 RD 或 k4 回升 ≥3×, 再查 mihomo 对应线路 (k4→7899)。
- hermes 侧 IncompleteRead 归 hermes 线 (dsv4f0731_nv 共用), 非 cc2 范围, 不处理。