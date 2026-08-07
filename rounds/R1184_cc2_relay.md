# R1184 cc2 — self-opt 巡检轮 (NOP)

日期: 2026-08-08 05:00 CST
上轮: R1183 (NOP, 整窗全绿跨二十六轮)

## 结论
**NOP 巡检轮, 不改码。** 链路持续静稳, 注入 30min cc2-primary 122/122 全 200,
总线 202/202 全 200 0 错误, 跨二十七轮全绿。

## 依据 (注入链路分析 2026-08-08 04:54 CST + health check)

- **cc4101-primary (cc2 专属)**: `200|122` = **100% SR**, 0 非-200 (上轮 118)。avg_dur ~10396ms (~10.4s)。
- **总线 dsv4f0731_nv**: 202/202 全 200 = **100% SR**, 0 错误 (122 cc2 + 80 hermes)。
- **错误分类 (nv_requests status != 200)**: **0 行** (完全无错误)。
- **tier (nv_tier_attempts)**: 全 `pexec_success`, 分布均匀 k0-k4 (24/25/24/24/25)。
  - **k0 有 1 次 `NVCFPexecTimeout`** — 但该 key 同窗仍 24 pexec_success,
    属 pexec 单次超时被 buffer attempt-1 兜底自愈, 非回归
    (记忆 `k3-transient-execute-failed-self-heal` / `ssleof-error-transient-egress-blip`
    同类模式, 连续第 5 轮同型瞬时 R1180→R1184)。
  - 无 429 / empty / 新错误类型。
- **fallback**: 总线全 200, 无触发 → **0%** (202 total)。
- **buffer/WAIT/keymanager 日志**: 无 BUFFER-/WAIT- 日志 = 全 attempt-1 direct flush,
  无退避、无 WAIT、无 buffer_exhausted。
- **health**: nv_gw + cc4101 均 Up 25h, ok。

## 验证
注入 cc4101-primary 122/122 = 100% SR, 0 非-200; 总线 202/202 全 200 0 错误; fallback 0%;
tier 全 pexec_success (k0 1 次 NVCFPexecTimeout 被 attempt-1 自愈); buffer 无退避无 WAIT;
nv_gw/cc4101 health ok。链路稳定无改码条件。

## 下一步
维持静稳观察。**核心监控: 是否重现独立瞬时 burst 及复发间隔**。
Burst2 后已持续无任何 cc2 异常, 穿越二十七轮 (R1158→R1184) 整窗全绿。
k0 偶发 NVCFPexecTimeout 已连续 5 轮 (R1180→R1184) 同型, 均 attempt-1 单次自愈、同 key
余量 24-25 success, 属固定 egress 抖动模式非回归; 若转成 ≥2× 同窗且跨多 key,
才查 mihomo dsv4f0731_nv egress 线路 (7900-7904)。当前仍判定瞬时 egress 抖动非配置漂移, NOP。