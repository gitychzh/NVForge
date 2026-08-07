# R1142 cc2 NOP 巡检轮 — 2026-08-08

## 结论: NOP (不改码)

30min cc2 主链（40006）**零表面错误**，cc2-primary `200|110` = **100% SR**（0 行非-200）。
唯一 surface 错误 NVStream_IncompleteRead 1× (502, 55.5s) **归属 hermes** 非 cc2。
tier 非-success 仅 NVCFPexecRemoteDisconnected (k0/k1/k4 分散) + empty_200 1× (k2)
分布式单点 self-heal 未上浮，低频下沉稳态。fallback 0%，buffer 全 attempt-1 direct flush。
cc2 范围无配置回归。

## 依据 (本 session 轮前注入 + 实查 2026-08-08 01:23)

- **30min cc2-primary (nv_requests 实查)**: `200|110` = **0 行非-200, 100% SR** — 主链全绿。
- **30min 错误分类 (注入)**: NVStream_IncompleteRead 1× (55488ms) — 该 502 **归属 hermes**
  (hermes|dsv4f0731_nv|502|1)，cc2 = 0 行 surface 错误。
- **30min 链路总览 (注入)**: cc4101-primary|dsv4f0731_nv|200|107 + hermes|200|22 + hermes|502|1。
- **buffer 日志 (实查)**: **全 attempt-1 direct flush** (success_text/success_tool_call,
  elapsed 1~12s), 无 execute_failed/无 backoff/无 WAIT/无新 exhaust。
- **fallback (实查)**: 30min cc_requests 111 行, fallback_triggered 0 = **0%** — 未触发 ms_gw。
- **tier 错误 (注入)**: NVCFPexecRemoteDisconnected (k0 2/k1 1/k4 3) + empty_200 1× (k2),
  共 ~7 次, 各 key/time 分散单点 self-heal, 无同 key 连续复发, 未上浮 surface。
  延续低频下沉稳态 ([[ssleof-error-transient-egress-blip]])。

## 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| cc2 主链 (40006) 30min | **200|110 = 0 行非-200, 100% SR** | ✅ 零表面错误 |
| 非-200 归属 | NVStream_IncompleteRead 1× (502, 55.5s) → **hermes**, cc2 0 行 | ✅ hermes 侧 |
| fallback 触发率 | 0% (30min 111 行, 未走 ms_gw) | ✅ |
| per-key tier 错误 | RD (k0/k1/k4) + empty_200 (k2) 单点分布式自愈, 未上浮 | ✅ (低频下沉) |
| buffer | 全 attempt-1 direct flush, 无 WAIT/无 exhaust | ✅ |

## 下一步
- 延续 NOP。主链滚动 30min 零表面错误、fallback 0%、buffer 常态 direct flush + 低频单点
  self-heal, 无参数可调。
- 持续观察 tier 分布式单点 self-heal (RD/empty_200)。若无同 key 多请求连续复发、不影响
  surface (cc2 0 行非-200), 继续 NOP。若某 key RD 回升 ≥3× 且浮上 surface (cc2 非-200 出现),
  再查 mihomo 对应线路。
- hermes 侧 IncompleteRead 归 hermes 线 (dsv4f0731_nv 共用), 非 cc2 范围, 不处理。