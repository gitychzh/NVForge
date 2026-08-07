# R1143 cc2 NOP 巡检轮 — 2026-08-08

## 结论: NOP (不改码)

30min cc2 主链（40006）**零表面错误**，cc2-primary `200|112` = **100% SR**（0 行非-200）。
唯一 surface 错误 NVStream_IncompleteRead 1× (502) **归属 hermes** 非 cc2。
tier 非-success 仅 NVCFPexecRemoteDisconnected (k0/k1/k2/k4 分散) + empty_200 1× (k2)
分布式单点 self-heal。buffer 5× execute_failed 单点（k3/k5/k4/k5/k4 分散时间戳）但
**全部 attempt-2 自愈**（25~42s elapsed 成功 flush），无 exhaust/无 WAIT。fallback 0%。
cc2 范围无配置回归。

## 依据 (本 session 轮前注入 + 实查 2026-08-08 01:35)

- **30min cc2-primary (nv_requests 实查)**: `200|112` = **0 行非-200, 100% SR** — 主链全绿。
- **30min 链路总览 (注入)**: cc4101-primary|dsv4f0731_nv|200|110 + hermes|200|22 + hermes|502|1。
- **30min 错误分类 (注入)**: NVStream_IncompleteRead 1× (55488ms) — 该 502 **归属 hermes**
  (hermes|dsv4f0731_nv|502|1)，cc2 = 0 行 surface 错误。
- **buffer 日志 (实查)**: 5× `NV-BUFFER-EXEC-FAIL` 分散时间戳 (01:06 k3 / 01:08 k5 / 01:13 k4 /
  01:21 k5 / 01:26 k4), 全部 attempt=1 `all_keys_exhausted=True`, 但逐条 request_id 追踪 (实查):
  - 2e42c974 (k3): attempt-2 SUCCESS flush 1072b, elapsed 25590ms
  - 51241101 (k5): attempt-2 SUCCESS flush 1017b, elapsed 37214ms
  - 82ffe629 (k4): attempt-2 SUCCESS flush 3657b, elapsed 34360ms
  - 8c77bb1d (k5): attempt-2 SUCCESS flush 6375b, elapsed 41771ms
  - 50990a15 (k4): attempt-2 SUCCESS flush 10326b, elapsed 25009ms
  → **全部 retry 自愈, 无 exhaust/无 WAIT**, 呼应 [[ssleof-error-transient-egress-blip]]
  分布式单点 egress 抖动脉冲。
- **fallback (实查)**: 30min cc_requests 112 行, fallback_triggered 0 = **0%** — 未触发 ms_gw。
- **tier 错误 (注入)**: NVCFPexecRemoteDisconnected (k0 1/k1 1/k2 1/k4 2) + empty_200 2× (k2),
  分散单点 self-heal, 无同 key 连续复发。
- **容器 (注入)**: nv_gw 27h, cc4101 22h — 稳定运行未重启。

## 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| cc2 主链 (40006) 30min | **200|112 = 0 行非-200, 100% SR** | ✅ 零表面错误 |
| 非-200 归属 | NVStream_IncompleteRead 1× (502, 55.5s) → **hermes**, cc2 0 行 | ✅ hermes 侧 |
| fallback 触发率 | 0% (30min 112 行, 未走 ms_gw) | ✅ |
| buffer self-heal | 5× execute_failed 单点 (k3/k4/k5), 全部 attempt-2 自愈 (25~42s)，无 exhaust/WAIT | ✅ (低频下沉) |
| per-key tier 错误 | RD (k0/k1/k2/k4) + empty_200 (k2), 单点分布式 non-recurring | ✅ (低频下沉) |
| container | nv_gw 27h, cc4101 22h | ✅ |

## 下一步
- 延续 NOP。主链滚动 30min 零表面错误、fallback 0%、buffer 低频单点 self-heal（全部 attempt-2
  自愈），无参数可调。
- 持续观察 buffer execute_failed / tier RD 分布式单点。若无同 key 多 req 连续复发、不影响
  surface (cc2 0 行非-200)，继续 NOP。若同 key RD/execute_failed 回升且浮上 surface (cc2 非-200 出现)，
  再查 mihomo 对应线路 (k3→7897, k4→7899, k5→?)。
- hermes 侧 IncompleteRead 归 hermes 线 (dsv4f0731_nv 共用)，非 cc2 范围，不处理。