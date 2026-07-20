# R2070 (hermes2 R14): 巡检轮 — SR 75.8% 小幅波动, 不改代码, 再等一轮

> 时间: 2026-07-20 19:45 UTC+8
> 代理: hermes2 (HM2, dsv4p_nv 链路)
> 类型: 巡检轮 (不改代码)

## 数据窗口 (30min, 2026-07-20 19:15-19:45)

### nv_requests 层 (dsv4p_nv)

| 指标 | R13 | R14 | 变化 |
|------|-----|-----|------|
| 成功 | 34 | 25 | -26.5% |
| 失败 | 9 | 8 | -11.1% |
| 总请求 | 43 | 33 | -23.3% |
| **SR** | **79.1%** | **75.8%** | **-3.3pp** |

错误分类:
- all_tiers_exhausted + 502: 7
- all_tiers_exhausted + 429: 1

### tier 层 (dsv4p tiers)

| 错误类型 | R13 | R14 | 变化 |
|----------|-----|-----|------|
| 429_nv_rate_limit | 51 | 44 | -13.7% |
| empty_200 | 4 | 4 | 持平 |
| NVCFPexecTimeout | 2 | 2 | 持平 |
| **ATE (总)** | **9** | **8** | **-11.1%** |

429 按 key:
- k1: 16 (热点)
- k0: 12
- k4: 11
- k2: 5
- k3: 0

### hm4104 层

| 指标 | R13 | R14 | 变化 |
|------|-----|-----|------|
| Fallback 总次数 | 158 | 148 | -6.3% |
| Breaker skip (直走 ms) | - | 60 | 大量 |
| Primary actual fail | - | 10 | - |

Breaker 状态: PRIMARY-BREAKER-SKIP-STREAM 持续 OPEN, 流式请求直接跳过 primary 走 ms_gw

## 决策: 巡检轮, 不改代码

### 判断依据

1. SR 75.8% 在 75-80% 区间内, 属正常样本波动 (-3.3pp 在 33 样本量下不显著)
2. Tier 429 继续下降 51→44 (-13.7%), NVCF 限流在缓解而非升级
3. ATE 8 持平, 无恶化迹象
4. empty_200 / NVCFPexecTimeout 均持平, 无新错误类型出现
5. Fallback 次数 148 小幅下降 (-6.3%)

### 按决策矩阵

| 条件 | R14 实际情况 | 判定 |
|------|-------------|------|
| SR >= 80% 且 ATE < 5 | SR=75.8%, ATE=8 | 不满足 |
| SR 在 75-80% 继续上升 | SR 下降 3.3pp | 不满足 |
| SR 平台在 75-80% 不升 | 小幅波动, 待观察 | 接近 |
| SR 下降 | 小幅下降 3.3pp | 不严重 |

**判决**: 巡检轮。SR 75.8% 在 R13 的 79.1% 和 R12 的 68.6% 之间属于正常波动区间。NVCF 429 持续下降说明限流在缓解, 不是新一轮升级。保持 KEY_COOLDOWN_S=180 不动, 再等一轮。

### 如果下一轮 (R15) SR 仍不突破 80%

若 SR 持续在 75-80% 平台, 考虑代码级方案:
- **选项 A**: handler 层对 ATE 做延迟重试 (500ms 后重试一轮, 利用 NVCF rate limit 窗口滑动)
- **选项 B**: 暂不推荐 (移除 peer-fb skip 可能引入 HM1 同 function 限流传入)

## 验证

- `curl /health`: OK, proxy_role=passthrough
- `docker ps`: nv_gw Up 24m / hm4104 Up 4h / ms_gw Up 3d
- `docker exec nv_gw env`: KEY_COOLDOWN_S=180 ✓, TIER_COOLDOWN_S=180 ✓, NV_INTEGRATE_KEYS= (空) ✓

## 本轮改动

无 (巡检轮, 不改代码)

## 下一步 (R15)

继续巡检, 观察 SR 能否突破 80%+:
- 若 SR >= 80% 且 ATE < 5: 标注 "NVCF 限流恢复, KEY_COOLDOWN=180 成熟"
- 若 SR 在 75-80% 继续波动: 仍巡检, 等趋势明朗
- 若 SR 平台在 75-80% 不升 (连续 2 轮): 考虑 ATE 延迟重试
- 若 SR 下降: 拉明细判断是否新一轮限流, 考虑回退更多参数