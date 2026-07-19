# R1971 (HM2→HM1): NOP — near-zero post-deploy traffic (~1.5h), all params floor/optimal, 4 zombie all NVCF-level, 连续冻结第11轮

## 数据采集（HM1, 2026-07-20 04:10 UTC）

### 总体成功率
| 窗口 | OK | Fail | SR |
|------|-----|------|-----|
| 30min | 2 | 0 | 100% |
| 6h | 35 | 4 | 89.7% |

### 失败明细（6h）
| 模型 | 错误类型 | 数量 | avg_ms |
|------|---------|------|--------|
| glm5_2_nv | zombie_empty_completion | 4 | 7218ms |

→ 全部 NVCF 级空内容返回（finish_reason=stop 但 content_chars=0），非配置可修。

### ATE 分析（6h）
| 模型 | 数量 | 状态 | avg_ms | max_ms |
|------|------|------|--------|--------|
| glm5_2_nv | 20 | 200 (peer-fb rescue) | 8404ms | 17786ms |
| dsv4p_nv | 6 | 200 (peer-fb rescue) | 40524ms | 55335ms |

→ 26 例 ATE 全部通过 peer-fallback 成功救援（status=200），无真 502。

### 成功请求延迟（6h）
| 模型 | 总数 | avg_ms | p50_ms | p95_ms | max_ms |
|------|------|--------|--------|--------|--------|
| dsv4p_nv | 10 | 31599 | 24271 | 54320 | 55335 |
| glm5_2_nv | 25 | 8404 | 8846 | 16701 | 17786 |

→ OK max=17.8s << UPSTREAM=30s，安全余量 12.2s。

### 日志关键事件
- BIG_INPUT breaker 正常触发 glm5_2_nv（>115K chars），peer-fallback 成功 3-4s
- 偶发 zombie_empty_completion（NVCF 级，finish_reason=stop 但 content_chars=11 < 50）
- 零 429、零 TimeoutError、零 BREAKER 误触发

## 当前参数状态（HM1 nv_gw）

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 30 | OK max=17.8s << 30s ✓ |
| TIER_TIMEOUT_BUDGET_S | 153 | 30+122=152 < 153 (1s margin) ✓ |
| PEER_FALLBACK_TIMEOUT | 122 | HM2 GLM_BUDGET=120, 122≥122 (boundary) ✓ |
| PEER_FALLBACK_ENABLED | 1 | 正常救援 26 ATE ✓ |
| PEER_FB_SKIP_MODELS | kimi_nv | 合理（同func双端无用） ✓ |
| KEY_COOLDOWN_S | 60 | 对齐 NVCF rate-limit 窗口 ✓ |
| TIER_COOLDOWN_S | 60 | KEY=TIER 铁律 ✓ |
| MIN_OUTBOUND_INTERVAL_S | 0 | 已触底 ✓ |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | 已触底 ✓ |
| BIG_INPUT breaker | 115K/FAIL_N=1/COOLDOWN=86400 | 正常触发 ✓ |

## 优化判断：NOP

**连续冻结第11轮。** 所有可调参数已处于地板值或最优值：

1. **UPSTREAM_TIMEOUT=30**：OK max=17.8s，余量 12.2s。若再砍则需要缩小 BUDGET 同步，但 BUDGET=153 只剩 1s 的 peer-fb 触发余量（30+122=152<153），砍 UPSTREAM 会连累 BUDGET 约束，得不偿失。
2. **PEER_FALLBACK_TIMEOUT=122**：HM2 GLM_BUDGET=120，122=120+2 已达边界。再砍则 peer-fb 对 glm5_2_nv 可能超时。
3. **BUDGET=153**：30+122=152 < 153，仅 1s 余量。若砍 BUDGET 则为 152（=152 boundary），peer-fb 触发条件变为 `>=` → 跳过，导致所有 ATE 无救援。
4. **KEY=TIER=60**：对齐 NVCF 60s rate-limit 窗口，砍则触发 429 级联。
5. **MIN_OUTBOUND=0, INTEGRATE=0**：已触底，无法再降。
6. **4 zombie 失败**：全部 NVCF 级空内容返回，非配置可修。BIG_INPUT breaker + peer-fallback 已覆盖大输入 zombie 路径。
## ⏳ 轮到HM1优化HM2
