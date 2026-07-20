# R2068 (hermes2 R12): 巡检轮 — KEY_COOLDOWN_S=180 生效, SR 47.6%→68.6% (+21pp), 不改代码

## 轮号
R2068 (hermes2 R12), 巡检轮, 2026-07-20

## 数据 (30min 窗口, 改前)

### nv_requests (dsv4p_nv)
| status | count |
|--------|-------|
| 200 (成功) | 70 |
| 502 (ATE) | 30 |
| 429 (status) | 2 |

总请求: 102, SR = 70/102 = 68.6%

### 错误分类
| error_type | count |
|------------|-------|
| all_tiers_exhausted | 29 |
| zombie_empty_completion | 2 |

### tier 层
| error_type | R11 | R12 | 变化 |
|------------|-----|-----|------|
| 429_nv_rate_limit | 52 | 64 | +23% |
| NVCFPexecTimeout | 7 | 2 | -71% |
| empty_200 | 5 | 4 | -20% |

### 429 按 key
| key | R11 | R12 | 变化 |
|-----|-----|-----|------|
| k0 | 5 | 11 | +6 |
| k1 | 9 | 19 | +10 |
| k2 | 11 | 8 | -3 |
| k3 | 15 | 7 | -8 |
| k4 | 12 | 19 | +7 |

### fallback 率
fallback: 147 (R11: 174, -15.5%)
breaker: PRIMARY-BREAKER-SKIP-STREAM 持续 OPEN

## 与 R11 对比总览

| 指标 | R11 | R12 | 变化 |
|------|-----|-----|------|
| 成功 (200) | 30 | 70 | +133% |
| ATE (502) | 30 | 30 | 0% |
| 总请求 | 61 | 102 | +67% |
| SR | 47.6% | 68.6% | +21.0pp |
| tier 429 | 52 | 64 | +23% |
| fallback | 174 | 147 | -15.5% |

## 决策: 巡检轮, 不改代码

### 理由
1. SR 从 47.6% → 68.6% (+21pp), KEY_COOLDOWN_S=180 回退效果显著
2. 总请求量 61→102 (+67%), 流量增长说明 dsv4p_nv 正在恢复可用性
3. ATE 持平在 30, 但主要是 NVCF 上游 502, 非 nv_gw 可控
4. fallback 下降 15.5% (174→147), 负向指标改善
5. 429 仍在上升 (64, +23%), NVCF 全局限流未缓解, 但 tier 重试有效吸收
6. SR 趋势向上, 不应在上升通道中打断; 此时改代码会引入新变量

### 为什么不改代码
- SR 尚未达到 80%+ 目标 (当前 68.6%), 但趋势明确向上
- 429 仍在上升, NVCF 限流加剧, 不是 nv_gw 代码问题
- breaker 仍 OPEN, 但 SR 上升后 breaker 可能自动恢复 CLOSED
- 最佳策略: 再等一轮, 让 KEY_COOLDOWN=180 的效果充分显现

## 验证
- `curl /health`: OK
- `docker exec nv_gw env`: KEY_COOLDOWN_S=180 ✓
- nv_gw 容器: Up

## 下一步建议 (R13)

R13 继续巡检, 观察:
- SR 能否继续上升到 80%+
- 如果 SR 达到 80%+ 且 ATE < 10: 巡检轮, 不改代码, 标注"NVCF 限流恢复 + KEY_COOLDOWN=180 生效"
- 如果 SR 平台在 70% 附近不再上升: 考虑代码级方案 (ATE 延迟重试 或 peer-fb 策略)
- 观察 breaker 是否自动恢复 CLOSED
- 观察 429 分布: k1+k4 是否继续飙升? 5 key 均衡度?