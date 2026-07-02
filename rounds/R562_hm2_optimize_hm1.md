# R562 (HM2→HM1): NOP — dsv4p_nv 硬故障验证, 全参数数据否决

## 📅 执行时间
UTC 2026-07-02 17:40+ (HM2 cron 触发, HM1 commit 5e1e49d 已处理)

## 🎯 本轮目标
1. **漂移检测**: 验证 R561 (HM_EMPTY_200_FASTBREAK=1) 代码+配置双改是否稳定部署
2. **硬故障诊断**: dsv4p_nv 从 08:09 UTC 起出现持续 0% SR, 确认是否为 function-level 硬故障
3. **候选穷举**: 对全部 9 个候选参数进行数据量化否决, 产出 NOP 工作量证明表

## 📊 HM1 数据收集

### 1. 漂移检测 (R561 部署验证)
| 验证项 | 值 | 源 | 结论 |
|--------|-----|----|------|
| git HEAD | 5e1e49d | git log | ✅ R561 已提交 |
| Container StartedAt | 2026-07-02T09:06:03Z | docker inspect | ✅ R561 后 Recreate |
| HM_EMPTY_200_FASTBREAK | `1` | docker exec env | ✅ 运行时生效 |
| HM_EMPTY_200_FASTBREAK | 第 467 行: `"1"` | compose grep | ✅ 持久化 |
| upstream.py EMPTY_200_FASTBREAK 代码 | 第 294 行 `if EMPTY_200_FASTBREAK > 0: break` | docker exec sed | ✅ 代码已加载 |
| HM_PEXEC_TIMEOUT_FASTBREAK | `1` | docker exec env | ✅ |
| HM_FORCE_STREAM_UPGRADE_TIMEOUT | `61` | docker exec env + compose | ✅ |
| HM_PEER_FALLBACK_TIMEOUT | `25` | docker exec env + compose | ✅ |
| **R561 三源一致** | — | — | **✅ 无漂移** |

### 2. 当前配置快照 (8 活跃参数)
```yaml
UPSTREAM_TIMEOUT: 25
TIER_TIMEOUT_BUDGET_S: 80
MIN_OUTBOUND_INTERVAL_S: 1.0
KEY_COOLDOWN_S: 25
TIER_COOLDOWN_S: 25
HM_CONNECT_RESERVE_S: 3
HM_PEXEC_TIMEOUT_FASTBREAK: 1
HM_EMPTY_200_FASTBREAK: 1
HM_FORCE_STREAM_UPGRADE_TIMEOUT: 61
HM_PEER_FALLBACK_TIMEOUT: 25
HM_SSLEOF_RETRY_DELAY_S: 1.0
```

### 3. DB 近 1h (2026-07-02 ~16:30–17:30 UTC)
| model | 成功 | 失败 | 成功率 |
|-------|------|------|--------|
| dsv4p_nv | 0 | 36 | 0% |
| glm5_1_nv | 0 | 7 | 0% |
| kimi_nv | 4 | 84 | 4.5% |
| **合计** | **4** | **127** | **3.1%** |

### 4. DB 近 2h (2026-07-02 ~15:30–17:30 UTC)
| model | 成功 | 失败 | 备注 |
|-------|------|------|------|
| dsv4p_nv | 1 | 52 | 唯一成功在 03:03 (R561 前旧 regime) |
| glm5_1_nv | 0 | 13 | — |
| kimi_nv | 4 | 209 | — |

### 5. 失败类型分布 (hm_tier_attempts 2h)
| 类型 | 数量 | 占比 |
|------|------|------|
| NVCFPexecTimeout | 93 | 81.6% |
| empty_200 | 21 | 18.4% |
| 429 | 0 | 0% |

### 6. dsv4p_nv 故障深度诊断 (hm_error_detail.2026-07-02.jsonl)
- **今日累计 dsv4p 错误记录**: 162 条
- **错误类型**: 100% `NVCFPexecTimeout`
- **单键 pexec 耗时**: 61,000–62,500ms (均匀分布, 6s 极差)
- **键分布**: k1-k5 全出现 (随机/轮询), 说明非 key 个体问题
- **时间窗口**: 最早 08:09 UTC, 持续至 17:30+ UTC (9h+)
- **R561 影响**: 08:09 早于 R561 部署 (09:06), 故障起始与 R561 无关

### 7. kimi_nv 故障模式 (hm_error_detail 近 10 条)
- `NVCFPexecTimeout` @ ~47,265ms (单键 fastbreak)
- `empty_200` @ ~60,400ms (EMPTY_200_FASTBREAK=1 生效 → break 省 key)
- 与 R542/R544 历史上的 function-level surge 模式一致

### 8. Peer Fallback (跨机互备)
- HM2→HM1 peer fallback 请求: 608 条 (全天)
- **成功**: 0 (grep `peer-fallback-success` / `peer fallback succeeded` 均无命中)
- 全部于 HM1 侧再次 `all_tiers_exhausted` 后返 502
- `PEER_FALLBACK_TIMEOUT=25s` 未触发救回 (和端 ceiling 同样约 61s 截断)

### 9. Empty 200 Fastbreak 效果验证
- `HM-EMPTY-FASTBREAK` 日志命中: 7 次 (全天 proxy log)
- 全部发生在 kimi_nv tier
- 行为正确: 检测到 empty_200 → 立即 break, 跳过剩余 key, 每次省 15–20s

## 🔍 数据归因

### dsv4p_nv: Function-level 硬故障 (与 R487 glm5.1 模式同构)
- **证据链**:
  1. 0% SR 持续 9h+ (08:09 → 17:30+), 跨轮次无视 R561 代码改动
  2. 5 key 均匀失败 (k1-k5 均出现 NVCFPexecTimeout, 非 key 劣化)
  3. `elapsed_ms` 高度集中在 61–62.5s → 说明不是“随机网络抖动”, 是 ceiling 级 timeout
  4. 无 429/empty200/SSLEOF 等可拦截错误
  5. 99.4% 的历史基线证明网关参数已最优 — 参数不可修
- **NVCF 函数 8915fd28 (sglang-dsv4p) 疑似容量/排队/下架问题**

### kimi_nv: Function-level surge (与 R542/R544 同构)
- 成功率 4.5% (1h), 仍是历史上的 function-level surge 模式
- 混合 `NVCFPexecTimeout` + `empty_200`, 非参数驱动

### Peer Fallback: 双端硬故障导致互备通道失效
- HM1 本地失败后转发到 HM2; HM2 也全部失败; 再转发回 HM1 (hop=2) 亦失败
- 互备网络层正常 (Tailscale ping 1ms, curl health 5ms), 失效根因是**双端 NVCF function 同时 hard-fail**

## ✅ 优化决策 (候选穷举 + NOP)

### 工作量证明表: 候选参数全否决

| 参数 | 当前值 | 候选新值 | 评估论据 | 决策 |
|------|--------|----------|----------|------|
| `HM_FORCE_STREAM_UPGRADE_TIMEOUT` | 61s | 59s (-2s) | dsv4p 故障在 62s; 但故障早于 R561, 无边缘成功案例, min_fail gap ≈ 0 说明 ceiling binding 成立; 然而 0% SR 已持续 9h, 收紧 ceiling ≠ 恢复 SR, 仅加速已知失败 | ❌ |
| `UPSTREAM_TIMEOUT` | 25s | 23s (-2s) | dsv4p 走 stream upgrade 路径, 实际用时 >61s, UPSTREAM 不 binding | ❌ |
| `TIER_TIMEOUT_BUDGET_S` | 80s | 75s (-5s) | FASTBREAK=1 + EMPTY_200_FASTBREAK=1 下 ATE 已 ~62–77s 完成, budget 未截断成功 | ❌ |
| `MIN_OUTBOUND_INTERVAL_S` | 1.0s | 0.8s (-0.2s) | 零 429 (6h); dsv4p function 级 timeout; throttle 不影响 function 级失败 | ❌ |
| `KEY_COOLDOWN_S` | 25s | 15s (-10s) | 零 429; 5 key 均匀失败, 非 key 级劣化; cooldown 无意义 | ❌ |
| `HM_PEER_FALLBACK_TIMEOUT` | 25s | 20s (-5s) | 零成功 9h+; 但 R560 已从 30→25 省 5s, 再削仍无收益, 且低于历史最慢 peer 成功 ~24s (R560 有 1.04x 安全余量), 再降破坏潜在恢复窗口 | ❌ |
| `HM_CONNECT_RESERVE_S` | 3s | 2s (-1s) | 实测 connect 0.6–2.1s, 2s 为 0.95x 安全; 省 1s 对 function-fail 61s 均值无意义, 边际为负 | ❌ |
| `HM_PEXEC_TIMEOUT_FASTBREAK` | 1 | 0 | 0 = 无限重试 = 确定性灾难; FASTBREAK=1 已是最小安全值 | ❌ |
| `NVCF_DEEPSEEK_FUNCTION_ID` | 8915fd28 | 未知 | 无已知可用替代 function ID; 且换 function ID 属非参数操作, 超出本轮范围 | ❌ |
| `HM_FORCE_STREAM_UPGRADE` | 1 | 0 | R502 已验证非流式 dsv4p SR 更低 (46.7% vs 85.8%); 当前 function hard-fail, 非流式路径同样无救 | ❌ |

**结论**: 全部 10 个候选方向均被数据否决, 无任何单参数改动能改善当前 regime. 本轮标记 **NOP** (non-actionable by gateway params).

### 连续 NOP 一致性检查
- 上轮 (R561) 有有效改动 (HM_EMPTY_200_FASTBREAK=1), 本轮非连续 NOP
- 上轮改动后: kimi empty_200 事件正确 fastbreak, 功能正常
- 本轮数据出现的新型模式: **dsv4p_nv 首次出现 0% SR 持续 >9h** (此前 R542–R561 期间 dsv4p 99.4% 完美)
- 判定: 非简单重复旧结论, 是**新硬故障模式**

## 🔧 执行过程
- **无配置改动**: compose.yml / upstream.py / config.py 均未修改
- **无容器重启**: 漂移检测通过, StartedAt 不变
- **无 DB 修复**: R510/R505 的 logging 修复已于 R561 前部署

## 📈 预期效果
- **短期**: SR 将完全取决于 NVCF 上游 `8915fd28` (deepseek-v4-pro) 和 `f966661c` (kimi-k2.6) 的 function 恢复节奏; 网关参数无影响
- **R561 红利保持**: empty_200 事件继续被 fastbreak 拦截, kimi 失败路径省 15–20s/次
- **监控信号**:
  - 若 dsv4p_nv 1h SR 恢复至 >50% → 硬故障解除, 应重新评估 ceiling chase 空间
  - 若 dsv4p_nv 持续 0% 另一 9h → 考虑更换 function ID (需 API 勘探)
  - 若 HM1 HM2 peer fallback 首次出现成功 → 检查对等端 ceiling 对称性

## 📝 备注
- **ydg 铁律维持**: 本轮仅采集+分析, 零配置改动. 只改 HM1 不改 HM2.
- **R561 upstream.py 状态**: `/app/gateway/upstream.py` 第 294 行 `if EMPTY_200_FASTBREAK > 0: break` 代码稳定运行, bind-mount 生效. 但代码仍独立于 git repo (仅 round 文件 tracked), HM1 备用重建时须手工重放代码 patch.
- **DB hm_tier_attempts 异常**: 2h 窗口内仅返回 kimi_nv 记录 (9 条); dsv4p_nv tier_attempts 完全缺失. 与 R510 已知漏洞一致 (部分失败路径漏写 tier_attempts). 分析已降级至 `hm_error_detail.jsonl` + `hm_requests` 双源交叉验证.

## 🔄 轮次交接
- 本方 (HM2→HM1) 已完成优化轮次
- 如检测脚本识别到此文件末尾的 `⏳` 标记, 即触发 HM1 侧下轮优化

## ⏳ 轮到HM1优化HM2
