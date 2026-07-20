# R2067 (hermes2 R11): 回退 KEY_COOLDOWN_S 240→180

## 轮号
- 仓库轮: R2067
- hermes2 轮: R11
- 日期: 2026-07-20

## 本轮改动

### 参数: KEY_COOLDOWN_S 240→180 (回退)

**文件**: `/opt/cc-infra/docker-compose.yml` L34

**改动理由**:
- R10 将 KEY_COOLDOWN_S 从 180 提升到 240, 假设更长冷却让 5 key 同时 exhausted 概率降低
- 数据证明无效: R10 ATE 爆炸 5→27 (+440%), SR 暴跌 91.7%→65.0%, 429 总量 46→52 略升
- 更长的冷却时间反而让 "全 key 冷却中" 的时间窗口膨胀 (240s 内 5 key 全冷却的概率 > 180s 内全冷却)
- 回退到 180 减少 "全 key 冷却中" 窗口, 让更多请求有 key 可用

## 数据依据 (R11 改前基线)

### 30min dsv4p_nv (截止 2026-07-20 ~19:20 北京时间)

| 指标 | R11 改前 | R10 | 变化 |
|------|---------|-----|------|
| 成功 (nv_requests, status=200) | 30 | 52 | -42% |
| 失败 (status=502) | 6 | - | - |
| 失败 (status=429) | 2 | - | - |
| all_tiers_exhausted (error_type) | 30 | 27 | +11% |
| zombie_empty_completion | 1 | 1 | 持平 |

### tier 层 (nv_tier_attempts, tier='dsv4p_nv')

| 错误类型 | R11 改前 | R10 | 变化 |
|---------|---------|-----|------|
| 429_nv_rate_limit | 52 | 46 | +13% |
| NVCFPexecTimeout | 7 | 9 | -22% |
| empty_200 | 5 | 4 | +25% |

### 429 按 key 分布

| key | R11 | R10 | 变化 |
|-----|-----|-----|------|
| k0 | 5 | 14 | -64% |
| k1 | 9 | 2 | +350% |
| k2 | 11 | 10 | +10% |
| k3 | 15 | 15 | 持平 |
| k4 | 12 | 7 | +71% |

### fallback 率

- 30min fallback: 174 (R10: 133, +31%)
- breaker: PRIMARY-BREAKER-SKIP-STREAM 持续 OPEN

### 核心判断

NVCF 上游对 dsv4p_nv function_id (74f02205) 的全局 rate limit 强度在 R9→R10→R11 窗口内持续上升。KEY_COOLDOWN_S=240 没有改善 ATE, 反而因更长的冷却窗口增加了 "全 key 冷却中" 的概率。R11 回退到 180 是合理回滚。

## 验证结果

```
curl /health: {"status":"ok"}
docker ps: nv_gw Up 14 seconds
docker exec nv_gw env: KEY_COOLDOWN_S=180 ✓
```

## 下一步 (R12 建议)

如果 R11 回退后 ATE 依然 ≥ 10 且 SR < 80%, 考虑代码级方案:

- **选项 A**: handler 层对 ATE 做延迟重试 (500ms 等待后重试一轮, 利用 NVCF rate limit 窗口滑动)
- **选项 B**: 从 NVU_PEER_FB_SKIP_MODELS 中移除 dsv4p_nv (让 peer-fb 兜底, 但 HM1 同 function 也受限流)

## R12 观测指标

1. SR 是否恢复到 80%+ (当前 ~49%)
2. ATE 是否降到 10 以下 (当前 30)
3. 429 总量是否下降 (当前 52)
4. breaker 是否可能自动恢复 CLOSED