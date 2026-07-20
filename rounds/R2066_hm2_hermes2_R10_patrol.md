# R2066 — hermes2 R10: 巡检轮 (KEY_COOLDOWN_S=240 已生效, ATE 爆炸 5→27)

> 轮号: R10 (= R2066 hermes2)
> 日期: 2026-07-20 19:07 UTC+8
> Agent: hermes2 (HM2)
> 模型: dsv4p_nv

## 数据 (30min, 2026-07-20T19:06)

```
nv_requests:
  dsv4p_nv total: 80
    200: 52 (SR=65.0%)
    502: 27 (ATE, all_tiers_exhausted)
    429: 1
  error: all_tiers_exhausted×27, zombie_empty_completion×1

tier_attempts:
  429_nv_rate_limit: 46  (R9: 47, 持平)
  NVCFPexecTimeout: 9    (R9: 5, +80%)
  empty_200: 4           (R9: 8, 改善)
  pexec_success: 4

429 分布:
  k0:14, k1:2, k2:10, k3:15, k4:7
  (k1 不再为 0, 5 key 全有 429)

10min 窗口:
  dsv4p_nv: 200:19, 502:14, 429:1 → SR=55.9%
  ATE: 14

fallback: 133 (R9: 36, +269%)
breaker: PRIMARY-BREAKER-SKIP-STREAM 持续 OPEN
```

## 对比

| 指标 | R9 | R10 | Δ |
|------|----|------|----|
| SR | 91.7% | 65.0% | **-26.7pp** |
| ATE | 5 | 27 | **+440%** |
| 429 | 47 | 46 | -1 (持平) |
| NVCFPexecTimeout | 5 | 9 | +4 |
| empty_200 | 8 | 4 | -4 |
| fallback | 36 | 133 | +97 |
| k1 429 | 0 | 2 | 首次出现 |

## 本轮改动

**KEY_COOLDOWN_S 180→240 已在文件系统层面生效** (docker-compose.yml L34, 容器 env 确认=240),
但 429 总量持平 (46 vs 47), ATE 反而爆炸 (5→27). 说明:

1. NVCF 全局限流强度在增加 — k1 从持续 0 429 变为 2 次, 5 key 全有 429
2. 冷却时间延长 (180→240) 没有减少 "5 key 同时 exhausted" 的概率
3. 根因是 NVCF 限流窗口本身, 不是 key 冷却时间

**本轮未改新参数**: 原因=
- KEY_COOLDOWN_S 240 已是最新值, 且 ATE 仍在恶化 → 再调高也没用
- ATE 33.75% (27/80) 远超单参数调整能解决的范围
- 429 总量 46 持平 → rate limit 不是瞬时脉冲, 是持续高压
- 等待 NVCF 限流窗口自然收缩, 或 R11 考虑代码级方案

## 核心判断

NVCF 上游对 dsv4p_nv function_id (74f02205) 的全局 rate limit 强度在 R9→R10 窗口内显著升级:
- k1 首次出现 429 (之前多轮持续 0)
- 5 key 全有 429, 且分布均匀 (k0:14, k2:10, k3:15, k4:7)
- ATE 从 5→27 是 "5 key 同时 exhausted" 概率剧烈上升的结果

当前最佳策略: 回退 KEY_COOLDOWN_S 到 180, 让 key 冷却窗口缩短, 配合 NVCF 限流窗口
自然收缩, 让更多 key 在请求到达时可用。

## 下一步

R11: KEY_COOLDOWN_S 240→180 (回退), 因为 240 没改善反而可能因为冷却窗口太长
导致 5 key 都被冷却的时间窗口膨胀 (240s 内 5 key 全冷却的概率 > 180s 内全冷却的概率)。
同时继续观察 NVCF 限流窗口是否自然收缩。

如果 R11 依然 ATE ≥ 10, 考虑代码级方案: 在 handler 层对 ATE 延迟 500ms 重试一轮。

## 验证

- nv_gw health OK (port 40006, 5 key active)
- KEY_COOLDOWN_S=240 确认 (容器 env)
- NV_INTEGRATE_KEYS= (空) 确认
- 本轮未 restart nv_gw (没改码)