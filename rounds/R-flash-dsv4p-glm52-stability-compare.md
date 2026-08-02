# R-flash-dsv4p-glm52-stability: deepseek-v4-flash 0731 + dsv4p_nv + glm5_2_nv 三模型稳定性对比

**日期**: 2026-08-02
**主机**: HM2 (opc2sname)
**目标**: 测试 deepseek-v4-flash 在 NVCF 上的稳定性, 同时对比 dsv4p_nv 与 glm5_2_nv

## 背景

用户要求测试 deepseek-v4-flash 0731 在 NVIDIA 上的稳定性, 并与 glm5_2_nv / dsv4p_nv 对比哪个更稳。
flash 未在 nv_gw config 中配置 (无 pexec function_id), 走 integrate API 直接探测。

## 测试 1: 三模型 integrate API 直连对比 (5 key × 1 轮)

通过 `integrate.api.nvidia.com/v1/chat/completions` 直连, 不经 nv_gw。

| 模型 | k1 | k2 | k3 | k4 | k5 | SR | avg |
|---|---|---|---|---|---|---|---|
| flash | 529 | 529 | 200(1.5s) | 200(0.6s) | 200(1.1s) | 3/5=60% | 0.8s |
| glm5_2_nv | 200(20.9s) | 200(24.2s) | 200(29.2s) | 200(20.0s) | 200(18.0s) | 5/5=100% | 22.5s |
| dsv4p_nv | 200(7.2s) | 200(3.3s) | 200(0.9s) | 200(3.0s) | 200(1.5s) | 5/5=100% | 3.2s |

## 测试 2: 三模型 integrate API 直连 (5 key × 2 轮)

| 模型 | R2 SR | R3 SR | 总 SR | avg |
|---|---|---|---|---|
| flash | 3/5=60% | 3/5=60% | 60% | 1.1s |
| glm5_2_nv | 5/5=100% | 5/5=100% | 100% | 20.5s |
| dsv4p_nv | 5/5=100% | 5/5=100% | 100% | 5.4s |

## 测试 3: flash integrate API 5 轮 (25 次)

| 轮 | SR | avg |
|---|---|---|
| R1 | 2/5=40% | 3.5s |
| R2 | 1/5=20% | 2.0s |
| R3 | 2/5=40% | 0.7s |
| R4 | 1/5=20% | 0.7s |
| R5 | 2/5=40% | 1.2s |
| **总计** | **8/25=32%** | 1.1s |

flash 529 (Service temporarily overloaded) 持续, 非限流 (429), 而是 NVCF 上游过载。

## 测试 4: dsv4p_nv vs glm5_2_nv 通过 nv_gw pexec (10x)

| 模型 | #1 | #2 | #3 | #4 | #5 | #6 | #7 | #8 | #9 | #10 | SR |
|---|---|---|---|---|---|---|---|---|---|---|---|
| dsv4p_nv | 502 | 502 | 502 | 502 | 502 | 502 | 502 | 502 | 502 | 502 | **0/10** |
| glm5_2_nv | 200 | 200 | 200 | 200 | 200 | 200 | 200 | 200 | 200 | 200 | **10/10** |

dsv4p_nv 0/10 原因: 单个探测成功后, 紧接请求触发 k3 429 → 全 5 key 429 → NV-GLOBAL-COOLDOWN 180s。
所有后续请求被 TIER-SKIP (all keys in cooldown) → 瞬间 502 (0.003s)。

## 测试 5: dsv4p_nv 冷却恢复后再测 10x

冷却恢复后单次探测 200 (2.3s), 但连续 10 次再次 0/10 (同上 429→冷却循环)。

## DB 2h 统计 (最终数据)

| 模型 | total | ok | SR% | avg_ms | 429 | 502 | 529 |
|---|---|---|---|---|---|---|---|
| dsv4p_nv | 135 | 96 | 71.1 | 9521 | 11 | 28 | 0 |
| glm5_2_nv | 34 | 34 | 100.0 | 50509 | 0 | 0 | 0 |

## 结论: glm5_2_nv 最稳, dsv4p_nv 次之, flash 不稳

| 维度 | flash | dsv4p_nv | glm5_2_nv |
|---|---|---|---|
| integrate SR | 32% (529 overloaded) | 100% | 100% |
| nv_gw pexec SR | N/A (未配置) | 0-70% (429风暴) | 100% |
| avg latency | 1.1s | 3-9s | 18-50s |
| 限流类型 | 529 过载 | 429 账户级限流 | 无 |
| 适合 cc2 | ❌ 太不稳 | ⚠️ 间歇 429 风暴 | ✅ 最稳但慢 |

**排名**: glm5_2_nv (最稳, 100% SR) > dsv4p_nv (间歇 429 风暴, 71% SR) > flash (529 过载, 32% SR)

**注**: glm5_2_nv avg 50s 对 cc2 交互场景偏慢 (thinking 模式), 但稳定性远超其他两者。
dsv4p_nv 快 (avg 9.5s) 但 pexec 路径 429 风暴频繁 (单次探测可触发全 key 冷却)。
flash 快 (avg 1.1s) 但 529 过载严重, 3 次中 2 次失败。

**建议**: cc2 链路维持 glm5_2_nv (R-nvonly-post15 回滚正确)。若需更快速响应, dsv4p_nv 在非 429 窗口可用, 但需接受 ~30% 失败率由 cc4101 fallback→ms_gw 兜底。
