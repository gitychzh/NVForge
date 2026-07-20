# R2073 — hermes2 R17 巡检轮

> 日期: 2026-07-20 20:08 CST
> 轮号: R17 (hermes2, dsv4p_nv 链路)
> 类型: 巡检轮 (不改代码)

## 数据 (30min 窗口, dsv4p_nv)

### nv_requests
| request_model | status | count |
|---------------|--------|-------|
| dsv4p_nv      | 200    | 17    |
| dsv4p_nv      | 502    | 8     |
| dsv4p_nv      | 429    | 1     |

- 总请求: 26 (R16: 28, -2)
- 成功: 17 (R16: 17, 持平)
- SR: 65.4% (R16: 60.7%, **+4.7pp** ✅)
- ATE: 9 (R16: 11, -2)

### 错误分类
- all_tiers_exhausted: 9 (R16: 11, -2)

### Tier 层 (nv_tier_attempts)
| error_type | R16 | R17 | 变化 |
|------------|-----|-----|------|
| 429_nv_rate_limit | 24 | 23 | **-1 (-4.2%)** |
| pexec_success | 28 | 28 | 持平 |
| RemoteDisconnected | 4 | 4 | 持平 |

429 按 key: k0:5, k1:5, k2:6, k3:6, k4:1 — 均匀分布, 无单 key 热点

### fallback
- 30min fallback 计数: 150 (R16: 152, -1.3%)
- PRIMARY-BREAKER-SKIP-STREAM: 持续 OPEN

### 健康检查
- `curl /health`: OK
- `docker ps`: nv_gw Up 45m / hm4104 Up 4h / ms_gw Up 3d
- KEY_COOLDOWN_S=180 ✓

## 趋势分析

```
指标         R12   R13    R14    R15    R16    R17    趋势
SR          68.6%  79.1%  75.8%  76.2%  60.7%  65.4%  ↑ 小幅回升
Tier 429     64     51     44     56     24     23    ↓ 微降, 已近底部
fallback    147     —      —     156    152    150    → 持平
breaker     —      —      —      —     OPEN   OPEN    → 持续 OPEN
```

SR 回升 +4.7pp 是正向信号，但样本量小(26)且 breaker OPEN 下虚低。Tier 429 从 24→23 几乎持平，下降趋势已放缓至接近底部。NVCF 限流基本稳定在 23 左右，不再大幅波动。

## 决策: 巡检轮, 不改代码

按 R17 判断矩阵: Tier 429=23 在 20-30 区间, SR=65.4% 在 60-75% 区间 → **巡检轮, 等趋势明朗**。

不改代码理由:
1. Tier 429 未跌破 20, 也未反弹 >40 — 在稳定区间
2. SR 回升但未突破 70% — breaker OPEN 下虚低, 需等 breaker 恢复
3. 所有指标变化幅度 <5%, 不足以判断趋势转向
4. breaker 持续 OPEN 是核心制约 — 需等其自动恢复后样本量扩大

## 验证

- `curl /health` → OK
- `docker ps` → nv_gw Up 45m, hm4104 Up 4h, ms_gw Up 3d
- `docker exec nv_gw env` → KEY_COOLDOWN_S=180 ✓

## 下一步 (R18)

继续巡检, 观察:
- Tier 429 能否跌破 20 (NVCF 限流基本恢复的信号)
- SR 能否突破 70% (breaker 恢复后自然回升)
- breaker 是否可能自动恢复 CLOSED (CIRCUIT_OPEN_S=60s → HALF_OPEN → 探测请求成功 → CLOSED)

如果 R18 的数据与 R17 几乎持平 (429 仍在 20-25, SR 仍在 60-70%), 连续 3 轮不变 → 考虑主动干预: 手动重启 nv_gw 触发 breaker 重新评估, 或缩短 KEY_COOLDOWN_S 180→150 轻推一下。