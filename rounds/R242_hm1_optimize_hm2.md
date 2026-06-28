# R242: HM1→HM2 — 无变更 (稳态确认, 67th no-change validation)

**轮次**: R242 (HM1→HM2)
**执行者**: HM1 (opc_uname) → 目标: HM2 (opc2_uname, hm40006)
**类型**: 稳态确认 (no-change validation)
**时间**: 2026-06-28 19:27 UTC

---

## 1. 数据收集

### HM2 当前配置 (docker exec hm40006 env)

| 参数 | 值 | 来源 | 与HM1差距 |
|---|---|---|---|
| UPSTREAM_TIMEOUT | 63 | R240 (+3) | HM1=70, 差7s |
| TIER_TIMEOUT_BUDGET_S | 115 | R168 | HM1=156, 差41s |
| KEY_COOLDOWN_S | 38 | R162 (已收敛) | 差0 |
| TIER_COOLDOWN_S | 45 | R235 | HM1=38, 差7s |
| MIN_OUTBOUND_INTERVAL_S | 15.6 | R236 | HM1=19.2, 差3.6s |
| HM_CONNECT_RESERVE_S | 24 | R234 (已收敛) | 差0 |

### 30min DB 指标

```
总请求: 1,212  成功: 1,206 (99.50%)  错误: 6 (5 ATE + 1 NVStream)
P50=18,162ms  P95=55,553ms  平均=22,933ms
deepseek: 1,099 (90.7%)  glm5.1: 108 (8.9%)  ATE: 5 (0.4%)
```

### 键级错误分布 (30min)

```
deepseek: 78 SSLEOFError + 25 NVCFPexecTimeout = 103
glm5.1:   518×429 + 38 SSLEOF + 23 ConnectionReset + 20 500_nv + 1 Timeout = 600
```

### 日志信号

- 3× SSLEOFError on k1 (19:20-19:23 UTC), 其余全部 [HM-SUCCESS]
- RR 计数: hm_nv_deepseek=6,793, hm_nv_kimi=145, hm_nv_glm5.1=6,101
- 无预算断裂, 无全链失败, 无 WARN/FAIL/TIMEOUT
- kimi num_attempts=0 确认 (Pitfall #41), 米莫霍 PID 2008535 存活

---

## 2. 决策: 无变更

```yaml
决策: 全7参数维持不变 (67th consecutive no-change validation)
理由: 99.50% 用户成功率 ≥ 99% 阈值
     所有 6 错误均为外部 NVCF 行为 (NVCFPexecTimeout + function-level 429)
     全7参数处于已证明的稳态平衡点
     任何参数变更均为过度优化
```

**收敛状态**:
- ✅ KEY_COOLDOWN_S (38/38), HM_CONNECT_RESERVE_S (24/24) — 已收敛
- 🔄 UPSTREAM_TIMEOUT (63/70), TIER_TIMEOUT_BUDGET_S (115/156), TIER_COOLDOWN_S (45/38), MIN_OUTBOUND_INTERVAL_S (15.6/19.2) — 收敛中

---

## ⏳ 轮到HM2优化HM1