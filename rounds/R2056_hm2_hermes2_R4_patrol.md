# R2056 — hermes2 R4: 巡检轮 (120s cooldown 验证 + 上游 502 问题诊断)

**时间**: 2026-07-20 16:30 CST (UTC+8)
**轮号**: R4 (hermes2 第 4 轮)
**模式**: 巡检轮 (不改代码, 数据验证 + 诊断)

## 数据 (30min 窗口, ≈16:00-16:30 CST)

### dsv4p_nv 成功率
| status | count |
|--------|-------|
| 200    | 36    |
| 502    | 6     |
| 429    | 1     |
| **SR** | **83.7%** (36/43) |

### 错误分类 (502 明细)
| error_type | count |
|------------|-------|
| NVStream_IncompleteRead | 3 |
| stream_first_byte_timeout | 3 |

### tier 层
| error_type | 30min | 10min |
|------------|-------|-------|
| 429_nv_rate_limit | 62 | 1 |
| 429_integrate_rate_limit | 1 | 0 |
| IntegrateRemoteDisconnected | 14 | — |
| empty_200 | 5 | — |
| **tier 429 合计** | **63** | **1** ✅ |

### breaker 状态
- 30min: 73 次 circuit OPEN, 0 次 CLOSED
- 30min fallback: 165 次 (全走 ms_gw)
- 5min PRIMARY-BREAKER-SKIP-STREAM: 20 次
- 2min PRIMARY-BREAKER-SKIP-STREAM: 10 次
- breaker 持续 OPEN, 未恢复

### nv_gw 健康
- health: OK
- 启动: 6 分钟前 (R3 重启后)
- env: KEY_COOLDOWN_S=120, TIER_COOLDOWN_S=120 ✅

## 分析

### ✅ 120s cooldown 有效
- 10min 窗口 tier 429 仅 1 次 (vs R3 的 30min 84 次)
- 429 浪涌已被根本性压制
- 不再需要进一步加大 cooldown

### ❌ breaker 未恢复 — 根因已变
- R3 时 breaker OPEN 是因为 429 浪涌 → all_tiers_exhausted → 502
- 现在 429 已压制，但 breaker 仍 OPEN
- **新根因**: NVCF 上游连接质量问题
  - IntegrateRemoteDisconnected ×14 (integrate 路径连接断开)
  - empty_200 ×5 (NVCF 返回空响应)
  - 500_nv_error ×1, 500_integrate_error ×1
  - NVStream_IncompleteRead ×3 (流式读取不完整)
  - stream_first_byte_timeout ×3 (首字节超时)

### 死循环机制
```
breaker HALF_OPEN → 探针请求 → NVCF 502/连接断开 → breaker 重新 OPEN → 等 60s → 循环
```

### 为何不改代码
1. 429 问题已解决 — cooldown 参数正确
2. 502/连接断开是 NVCF 上游问题，不是 nv_gw 参数能修的
3. 改 CIRCUIT_OPEN_S 或 CIRCUIT_FAILURE_THRESHOLD 只是掩盖上游问题，不会让 dsv4p_nv 真正变稳
4. 当前 breaker 正确履职：上游不可靠 → 甩给 ms_gw 兜底 → 不丢请求

## 下一步建议 (R5)

### 首要: 连通性诊断
1. 确认 dsv4p_nv 的 function_id `74f02205` 状态 (NVCF console 检查是否 ACTIVE/DEPLOYING/ERROR)
2. 检查 integrate 路径: `NV_INTEGRATE_MODELS=""` (空) — dsv4p_nv 走 pexec DIRECT 而非 integrate
   - 但 IntegrateRemoteDisconnected ×14 表明 integrate 路径仍在被尝试 (可能是 per-key lane R838B: dsv4p_nv:5, k5 先试 integrate)
   - 这可能是集成路径配置问题
3. 做一次直连测试: curl 直接测 NVCF API (非 nv_gw 代理) 看是否同样 502

### 若上游恢复
- breaker 会在 HALF_OPEN 探针成功后自动 CLOSED
- 做巡检轮记录即可

### 若上游持续 502
- 考虑禁用 integrate 路径对 dsv4p_nv 的尝试 (如果 k5 integrate 是 502 来源)
- 或联系 NVCF 支持排查 function_id 74f02205 健康状态

## 验证
- 无代码改动，无重启
- nv_gw health OK, env 确认 KEY_COOLDOWN_S=120, TIER_COOLDOWN_S=120
- ms_gw 兜底正常，请求无丢失