# STATE.md — cc2 自优化 nv_gw 链路 (HM2)

> 当前轮: **R1142 (NOP 巡检轮/不改码 — 30min 主链零表面错误, cc2-primary
> 200|110=100% SR, 0 行非-200; 唯一 surface 错误 NVStream_IncompleteRead 1× (502)
> 归属 hermes 非 cc2; tier 错误 RD (k0/k1/k4) + empty_200 1× (k2) 分布式单点
> self-heal, 低频下沉稳态; buffer 全 attempt-1 direct flush, 无 WAIT/无 exhaust;
> fallback 0% (111 行 0 触发))**
> cc4101-primary (主 nv_gw:40006) 实测 30min = **0 行非-200** — 主链全绿
> 非-200 归属: **hermes 1× NVStream_IncompleteRead (502, 55.5s), cc2 0 行** — cc2 零表面错误
> fallback: 0% (30min cc_requests 111 行 fallback_triggered=0, 未走 ms_gw)
> tier 错误: 30min NVCFPexecRemoteDisconnected (k0 2/k1 1/k4 3) + empty_200 1× (k2),
> 共 ~7 次, 各 key/time 分散单点 self-heal 未上浮 (低频下沉稳态, 延续 [[ssleof-error-transient-egress-blip]])
> buffer: 全 attempt-1 direct flush (success_text/success_tool_call), 无 execute_failed/
> 无 backoff/无 WAIT/无新 exhaust
> 容器 (注入 2026-08-08 01:23): nv_gw 27h, cc4101 21h 稳定未重启
> 上轮: R1141 (NOP, 主链零表面错误 100% SR)

## 本轮 (R1142) 改动 + 依据 + 验证

### 改动: 无 (NOP。30min cc2-primary 0 行非-200 (200|110 = 100% SR), 主链全绿。
### 唯一 surface 错误 NVStream_IncompleteRead 1× (502) 归属 hermes 非 cc2。tier 错误
### RD (k0/k1/k4) + empty_200 (k2) 分布式单点 self-heal 未上浮, 低频下沉稳态。
### buffer 全 attempt-1 direct flush, fallback 0% (111 行 0 触发)。
### cc2 范围无配置回归 → 不改码)

### 依据 (本 session 轮前注入 + 实查 2026-08-08 01:23)

- **30min cc2-primary (nv_requests 实查)**: `200|110` = **0 行非-200, 100% SR** — 主链全绿。
- **30min 链路总览 (注入)**: cc4101-primary|dsv4f0731_nv|200|107 + hermes|200|22 + hermes|502|1。
- **30min 错误分类 (注入)**: NVStream_IncompleteRead 1× (55488ms) — 该 502 **归属 hermes** 非 cc2。
- **buffer 日志 (实查)**: 全 attempt-1 direct flush (success_text/success_tool_call,
  elapsed 1~12s), 无 execute_failed/无 backoff/无 WAIT/无新 exhaust。
- **fallback (实查)**: 30min cc_requests 111 行, fallback_triggered 0 = **0%** — 未触发 ms_gw。
- **tier 错误 (注入)**: NVCFPexecRemoteDisconnected (k0 2/k1 1/k4 3) + empty_200 1× (k2),
  分散单点 self-heal, 无同 key 连续复发, 未上浮 surface。
- **容器 (注入)**: nv_gw 27h, cc4101 21h — 稳定运行未重启。

### 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| cc2 主链 (40006) 30min | **200|110 = 0 行非-200, 100% SR** | ✅ 零表面错误 |
| 非-200 归属 | NVStream_IncompleteRead 1× (502, 55.5s) → **hermes**, cc2 0 行 | ✅ hermes 侧 |
| fallback 触发率 | 0% (30min 111 行, 未走 ms_gw) | ✅ |
| per-key tier 错误 | RD (k0/k1/k4) + empty_200 (k2), 单点分布式 self-heal 未上浮 | ✅ (低频下沉) |
| buffer | 全 attempt-1 direct flush, 无 WAIT/无 exhaust | ✅ |
| container | nv_gw 27h, cc4101 21h | ✅ |

## 下一步
- 延续 NOP。主链滚动 30min 零表面错误、fallback 0%、buffer 常态 direct flush + 低频单点
  self-heal, 无参数可调。
- 持续观察 tier 分布式单点 self-heal (RD/empty_200)。若无同 key 多请求连续复发、不影响
  surface (cc2 0 行非-200), 继续 NOP。若某 key RD 回升 ≥3× 且浮上 surface (cc2 非-200 出现),
  再查 mihomo 对应线路。
- hermes 侧 IncompleteRead 归 hermes 线 (dsv4f0731_nv 共用), 非 cc2 范围, 不处理。