# R2303: HM2优化HM1 — EMPTY_200_FASTBREAK 2→3 + NVU_TIER_BUDGET_KIMI_NV 170→200

## 数据收集

### Docker 日志 (最近100行)
- 容器刚重启 (R2302 后), 仅最后几分钟日志
- glm5_2_nv: 2 次成功 (k2 success after 1 cycle, peer-fallback 200), 1 次 ATE (5 keys 429 + 1 timeout + 1 SSLEOF), 1 次 peer-fallback using HM2
- kimi_nv: 无近期请求 (日志窗口内全是 glm5_2_nv)
- dsv4p_nv: 无近期日志

### DB 6h 统计
| 指标 | kimi_nv | glm5_2_nv | dsv4p_nv | 总计 |
|------|---------|-----------|----------|------|
| 总数 | 42 | 35 | 8 | 85 |
| 成功 | 15 | 18 | 7 | 40 |
| SR | 35.7% | 51.4% | 87.5% | 47.1% |
| avg_ms_ok | 33,871 | 23,705 | 40,230 | - |
| avg_ms_fail | 175,798 | 16,450 | 95,117 | - |

### 错误分布 (6h)
| 错误类型 | 计数 |
|----------|------|
| all_tiers_exhausted | 35 |
| zombie_empty_completion | 9 |
| NVStream_IncompleteRead | 1 |

### kimi_nv ATE 详情 (6h, 21 次)
| duration bucket | 计数 | 含义 |
|----------|------|------|
| 124-126s | 8 | 2 empty_200 × 62s → FASTBREAK=2 触发, 5 未用 keys 浪费 |
| 127-168s | 5 | 2 empty_200 + 其他错误 → 约168s ATE |
| 188-370s | 8 | 预算耗尽 (370s = TIER_TIMEOUT_BUDGET_S 415-45s) |

### kimi_nv tier_attempts (6h)
| 错误类型 | 计数 |
|----------|------|
| empty_200 | 6 |
| NVCFPexecSSLEOFError | 3 |
| NVCFPexecRemoteDisconnected | 2 |

### kimi_nv 成功请求延迟
- 最快: 6,035ms, 最慢: 123,145ms
- 大部分成功在 6-41s, 少数超过 70s
- 单个 extreme: 123,145ms (大量 key cycling 后成功)

### 当前核心参数
```
NVU_TIER_BUDGET_KIMI_NV=170
NVU_TIER_BUDGET_DSV4P_NV=160
NVU_TIER_BUDGET_GLM5_2_NV=210
TIER_TIMEOUT_BUDGET_S=415
NVU_EMPTY_200_FASTBREAK=2
UPSTREAM_TIMEOUT=24
KEY_COOLDOWN_S=10
TIER_COOLDOWN_S=0
PROXY_TIMEOUT=500
```

## 根因分析

**核心问题: FASTBREAK=2 过早触发, 浪费 5 个未试 keys**

kimi_nv ATE 中 8 次在 124-126s 触发 fastbreak:
- 第1次 empty_200: ~62s → NVK keystore 标记空 key 为 cooling
- 第2次 empty_200: ~62s → 连续 2 次 → FASTBREAK=2 立即触发
- 结果: 5 个 keys 从未被尝试, 全部浪费

**为什么这不合理**: kimi_nv 有 5 个 NVCF keys, 各走不同 mihomo 出口. empty_200 是 NVCF 侧的问题 (function 返回空), 但不同 key 走不同网络路径, 可能某 key 能获得非空响应. 只试 2 个 keys 就放弃太早.

**kimi_nv 成功请求证据**: 15 次成功, 大部分需要 key cycling (跨 key 尝试). 成功请求中 1 个 extreme 123s 经过大量 key cycling 后成功. 这说明: 多试 keys 确实能提高成功率.

**R2302 的 170s 预算不足**: 
- FASTBREAK=2 时: 2 × 62 = 124s, 170s 够用
- FASTBREAK=3 时: 3 × 62 = 186s, 170s 不够 → 需要 200s

## 决策: 2 改动 (只改 HM1)

### 改动 1: `NVU_EMPTY_200_FASTBREAK` 2 → 3

**理由**:
- 8 次 ATE @ 124-126s 过早触发, 5 个未用 keys 浪费
- 3 次 empty_200 允许 3 个 key 尝试 (vs 2), 5 个 keys 中试 3 个 → 多 1 个 key 机会
- 3 × 62s = 186s 预算需求

**权衡**: 
- 如果 3 个 keys 都 empty_200 → 浪费 186s (vs 124s), 但实际概率低 (不同 key 不同出口)
- 如果第 3 个 key 成功 → 成功请求 (vs 原来 ATE)
- 即使全部 empty_200 → peer-fallback 到 HM2 的 dsv4p_nv, 仍可恢复

### 改动 2: `NVU_TIER_BUDGET_KIMI_NV` 170 → 200

**理由**:
- EMPTY_200_FASTBREAK=3 需要至少 186s 预算
- 200s 留有余量 (186s + 14s 余量用于 key cycling 开销)
- 200s: ~8 次 key 尝试 (UPSTREAM_TIMEOUT=24s), 足够覆盖 5 keys + 重试

**Fallback 影响**:
- TIER_TIMEOUT_BUDGET_S=415
- 415 - 200(kimi) - 160(dsv4p) = 55s 留给 glm5_2 fallback
- 之前 (170s kimi): 415 - 170 - 160 = 85s for glm5_2
- glm5_2 在 429 风暴中, 55s vs 85s 影响极小 (GLM5_2 无跨模型 fallback, R753)
- 实际: kimi_nv 成功后无需 fallback; kimi ATE 时 dsv4p_nv 仍是可行 fallback

### 不改的参数
- `TIER_TIMEOUT_BUDGET_S=415`: 保持, 200+160=360 ≤ 415 ✓
- `NVU_TIER_BUDGET_DSV4P_NV=160`: 保持
- `NVU_TIER_BUDGET_GLM5_2_NV=210`: 保持
- `KEY_COOLDOWN_S=10`: 保持
- `UPSTREAM_TIMEOUT=24`: 保持
- `PROXY_TIMEOUT=500`: 保持

## 执行

### 变更
文件: `/opt/cc-infra/docker-compose.yml` (HM1)
```diff
- NVU_EMPTY_200_FASTBREAK=2  # R2270 ...
+ NVU_EMPTY_200_FASTBREAK=3  # R2303 (HM2->HM1): 2->3 raise fastbreak threshold

- NVU_TIER_BUDGET_KIMI_NV=170  # R2302 ...
+ NVU_TIER_BUDGET_KIMI_NV=200  # R2303 (HM2->HM1): 170->200 support FASTBREAK=3
```

### 重启
```
docker compose -f /opt/cc-infra/docker-compose.yml up -d --no-deps --force-recreate nv_gw
→ Container nv_gw Recreated → Started
```

### 验证 (live env)
```
NVU_EMPTY_200_FASTBREAK=3  ✅
NVU_TIER_BUDGET_KIMI_NV=200  ✅
TIER_TIMEOUT_BUDGET_S=415  (unchanged)
Health: 200  ✅
```

## 预期效果

- kimi_nv ATE @ 124-126s: 8 次 → 预期减少 (第 3 个 key 可能成功)
- 如第 3 个 key 仍 empty_200 → ATE @ ~186s + peer-fallback, 但至少多试了 1 个 key
- kimi_nv SR 预期从 35.7% 提升: 当前 21 次 ATE 中 8 次在 124-126s, 若其中 1/3 在 FASTBREAK=3 后成功 → +2-3 次成功
- 成功请求不受影响 (p50 ~30s, p90 ~87s << 200s)
- 200+160=360 ≤ 415, 全链路安全

## 下一轮建议
- 监控 kimi_nv ATE duration 是否出现新的 186s 簇 (3 empty_200 + fastbreak)
- 关注 kimi_nv SR 是否从 35.7% 提升
- 如果 186s 簇出现且 SR 不提升, 考虑进一步增加 FASTBREAK 到 4
- glm5_2 429 风暴持续, 属于 NVCF 侧问题, 非 HM1 配置可修复

## ⏳ 轮到HM1优化HM2