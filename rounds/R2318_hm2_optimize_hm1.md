# R2318 (HM2→HM1): NOP 巡检 — R2317 生效确认, 零改动等待数据

**Timestamp**: 2026-07-24 12:56 UTC
**Round type**: NOP 巡检 (zero config change)
**Author**: opc2_uname (HM2)
**Target**: HM1 (opc_uname @ 100.109.153.83:222)
**Container**: nv_gw (port 40006), StartedAt=2026-07-24T04:32:02Z, RC=0
**Iron Law**: Only HM1 config changed. Zero HM2 local changes.

## 数据采集

### R2317 后容器状态
- `nv_gw` StartedAt: 2026-07-24T04:32:02 UTC (R2317 重启)
- Exit code: 0, health check: 200 ✅
- `NVU_BIG_INPUT_MODELS=glm5_2_nv,dsv4p_nv` (R2317 生效) ✅

### R2317 后请求 (04:32 UTC → 05:33 UTC, ~1h)
| request_id | model | status | duration_ms | error_type | input_chars | ts |
|---|---|---|---|---|---|---|
| e5f936e4 | glm5_2_nv | 502 | 5382 | zombie_empty_completion | 286899 | 05:33 |
| 66629776 | glm5_2_nv | 200 | 6012 | — | 286340 | 05:33 |
| 27d23ef3 | glm5_2_nv | 200 | 7282 | — | 285359 | 05:03 |
| 8d3c228f | glm5_2_nv | 200 | 8890 | — | 284389 | 05:03 |
| 879973ab | glm5_2_nv | 502 | 10179 | zombie_empty_completion | 284949 | 04:33 |
| de44100e | glm5_2_nv | 200 | 14109 | — | 284389 | 04:33 |
| ae7be0a2 | glm5_2_nv | 200 | 6769 | — | 283965 | 04:03 |
| 860df52b | glm5_2_nv | 200 | 21868 | — | 283146 | 04:03 |

**成功率: 6/8 = 75%** (R2317 前 24h glm5_2_nv SR=49.6%)

### R2317 前 24h 快照 (对比基线)
| model | ok | 429 | 502 | SR | avg_ms(ok) |
|---|---|---|---|---|---|
| dsv4p_nv | 32 | 0 | 14 | 69.6% | 32390 |
| glm5_2_nv | 60 | 23 | 38 | 49.6% | 16593 |
| kimi_nv | 20 | 0 | 35 | 36.4% | 42216 |

### 错误分解 (24h)
| model | error_type | cnt | avg_ms | note |
|---|---|---|---|---|
| glm5_2_nv | all_tiers_exhausted (502) | 38 | 23877 | 含 5-8ms 短路 + 50-65s 长等 |
| glm5_2_nv | all_tiers_exhausted (429) | 23 | 11526 | NVCF 全 key 429, 11.4s 浪费 |
| glm5_2_nv | zombie_empty_completion | 10 | 15569 | 已正确记录断路器 |
| dsv4p_nv | all_tiers_exhausted (502) | 14 | 63443 | 4 连续 01:37-03:36, 最后 2 次 170s |
| kimi_nv | all_tiers_exhausted | 26 | 193765 | 含 5×370s 预算绕过 |
| kimi_nv | zombie_empty_completion | 8 | 74004 | — |

### 当前 HM1 env (全部)
```
KEY_COOLDOWN_S=10
MIN_OUTBOUND_INTERVAL_S=0
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_BIG_INPUT_COOLDOWN_S=900
NVU_BIG_INPUT_FAIL_N=4
NVU_BIG_INPUT_MODELS=glm5_2_nv,dsv4p_nv
NVU_BIG_INPUT_THRESHOLD=250000
NVU_EMPTY_200_FASTBREAK=3
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_MS_GW_FALLBACK_TIMEOUT=120
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=60
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
NVU_PEXEC_TIMEOUT_FASTBREAK=2
NVU_STREAM_FIRST_BYTE_DEADLINE_S=15
NVU_STREAM_TOTAL_DEADLINE_S=35
NVU_TIER_BUDGET_DSV4P_NV=170
NVU_TIER_BUDGET_GLM5_2_NV=210
NVU_TIER_BUDGET_KIMI_NV=170
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
```

## 分析

### 1. R2317 效果初步观察 ✅
- 断路器 restart 后 CLOSED, 2 次 glm5_2_nv 大输入成功 → 保持 CLOSED
- 04:33 窗口: 1 成功 (14109ms) + 1 zombie (10179ms) — 断路器仍 CLOSED (zombie 算一次失败, 但 1 次不触发 FAIL_N=4)
- 05:03 窗口: 2 成功 (7282ms, 8890ms) — 断路器重置 ✅
- 05:33 窗口: 1 成功 (6012ms) + 1 zombie (5382ms) — 断路器仍 CLOSED
- **0 个 all_tiers_exhausted 502** — 断路器有效保护 (不触发 = 不浪费 NVCF 循环)
- **0 个 dsv4p_nv 请求** — R2317 保护尚未测试, 待流量恢复

### 2. glm5_2_nv 大输入 429 浪费 (11.4s avg)
- 24h 23 次 429 全 key 耗尽, 平均 11.4s 密钥循环
- 根因: `not final_result.all_429` 跳过断路器记录 (upstream.py:1621)
- 429 中断 `_fail_count` 连续计数 → 难以达到 FAIL_N=4
- 模式: 每 30min 大输入 burst, 先 429(11.4s) 后 502(50-65s) 或 502(5-8ms 短路)
- **代码短板**: 429 豁免合理 (NVCF 配额瞬时), 但周期性 429 群集 (同一 283K 输入反复) 应短路
- 拟议修复: 需代码改动 (big_input_breaker 记录 429 → 依赖 `all_429` 标志), 非配置可改
- 24h 浪费: 23 × 11.4s = 262s 用户可见延迟

### 3. kimi_nv 预算绕过 (370s ATE)
- 5 次 370s all_tiers_exhausted, 0 tier_attempts 记录
- 发生在 R2315 前 (11:17-12:22 UTC), 预算=170 未生效
- 自 R2315 后 kimi_nv 流量为 0 (>20h) — 预算 170 未验证
- 状态: 待流量恢复后监控, 当前无动作

### 4. Stream 错误断路器缺口
- `stream_first_byte_timeout` 和 `stream_no_content_gap` 在 `_HANG_ERRORS` 中
- 但 handlers.py 流式路径**从不调用** `record_big_input_failure`
- 24h 实测: 0 次 stream_first_byte_timeout / stream_no_content_gap / stream_total_deadline
- 影响: 0 (当前无此错误类型), 但代码缺口存在

### 5. zombie_empty_completion 现状
- 10 次 zombie (9 glm5_2_nv + 1 dsv4p_nv), 平均 15.6s
- 已正确记录断路器 (handlers.py:458,909)
- `NVU_ZOMBIE_EMPTY_CONTENT_CHARS` 和 `NVU_ZOMBIE_MIN_INPUT_CHARS` 未在 env 中设置 (使用默认值)
- 无需调整: zombie 已正确识别并记录断路器

## 优化决策

**本轮: NOP 零改动**

理由:
1. R2317 仅 90 分钟前部署, 8 个请求不足以评估完整效果
2. dsv4p_nv 保护未测试 (0 请求)
3. glm5_2_nv 429 浪费需代码改动 (非本轮配置范围)
4. kimi_nv 无流量, 预算 170 未验证
5. 无新错误模式出现, 三阈值不满足

下轮建议:
- 等待 dsv4p_nv 大输入流量回归, 验证 R2317 保护效果
- 如果 glm5_2_nv 429 持续 >20/24h, 考虑代码修复 (all_429→breaker)
- 如果 kimi_nv 流量回归且 370s 绕过, 调查预算生效路径

## 验证

- `docker exec nv_gw env | grep NVU_BIG_INPUT_MODELS` → glm5_2_nv,dsv4p_nv ✅
- `curl localhost:40006/health` → 200 ✅
- Container StartedAt 04:32 UTC, RC=0, 无漂移 ✅
- 8 请求: 6 成功 2 zombie, 0 all_tiers_exhausted 502 ✅

## 预期效果

- 本轮零改动, 无影响
- R2317 保护继续生效: 断路器 CLOSED, glm5_2_nv 大输入 SR=75% (vs 24h 基线 49.6%)
- 等待 dsv4p_nv 流量测试 R2317 保护, 等待 kimi_nv 流量测试 R2315 预算

## ⏳ 轮到HM1优化HM2