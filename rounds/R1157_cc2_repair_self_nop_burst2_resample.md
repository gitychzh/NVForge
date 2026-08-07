# R1157 — cc2 NOP: Burst2 re-sample 第 3 轮确认非新事件, 整窗干净 SR 100%

- 日期: 2026-08-08 03:02 CST
- 容器: nv_gw Up 24h, cc4101 Up 23h (全未重启, 无漂移)
- 判定: **NOP 不改码**

## 数据 (注入 + 实查)

### 注入 30min (≈18:28-18:58 UTC)
- cc4101-primary: `200|91`, `502|2` (buffer_exhausted)
- 错误分类: buffer_exhausted × 2

### 实查
- **2× buffer_exhausted request_id**: `3a582e6c` (18:34:58) + `25c3a92b` (18:36:23)
  = 与 R1155/R1156 记录 **Burst2 逐一相同**。窗口边界 re-sample, 非新事件。
- **Live 10min**: cc4101-primary 31/31 = **100% SR, 0 bad**
- **Live 5min**: 13/13 = **100%, 0 非-200**
- **fallback 30min**: 1762 总请求, 0 触发 = **0%**
- **容器**: nv_gw + cc4101 /health 全 ok

## 结论
注入 2× = 已闭合 Burst2 (18:34/18:36 UTC) 的 request_id re-sample, 与上轮 R1156 完全一致。
18:37 UTC 后整窗干净, 无第 3 次独立复发。fallback 0%, tier 无 429/empty/新类型。
当前仍判定瞬时 egress 抖动非配置漂移, NOP。

## 状态
无改动。核心监控: 是否再现独立瞬时 burst 及复发间隔 (R1148/49 storm → Burst2 间隔 ~32min)。
下窗口若 ≥2× buffer_exhausted 且 request_id 全新 → 独立新事件, 按记忆深挖 mihomo egress。