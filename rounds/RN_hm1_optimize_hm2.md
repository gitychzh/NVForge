# R242: HM1→HM2 — 无变更 (稳态确认, 67th no-change validation)

**轮次**: R242 (HM1→HM2)
**执行者**: HM1 (opc_uname) → 目标: HM2 (opc2_uname, hm40006)
**类型**: 稳态确认 (no-change validation)
**时间**: 2026-06-28 19:27 UTC

---

## 1. 数据收集 (SSH to HM2)

### 1.1 HM2 当前配置 (docker exec hm40006 env)

| 参数 | 值 | 来源 | 与HM1差距 |
|---|---|---|---|
| UPSTREAM_TIMEOUT | 63 | R240 (+3) | HM1=70, 差7s |
| TIER_TIMEOUT_BUDGET_S | 115 | R168 | HM1=156, 差41s |
| KEY_COOLDOWN_S | 38 | R162 (已收敛) | HM1=38, 差0 |
| TIER_COOLDOWN_S | 45 | R235 | HM1=38, 差7s |
| MIN_OUTBOUND_INTERVAL_S | 15.6 | R236 | HM1=19.2, 差3.6s |
| HM_CONNECT_RESERVE_S | 24 | R234 (已收敛) | HM1=24, 差0 |
| PROXY_TIMEOUT | 300 | 固定 | HM1=300 |

### 1.2 30分钟窗口 (DB直查)

```
总请求:   1,212
成功:     1,206  (99.50%)
错误:     6 (5 ATE + 1 NVStream_TimeoutError)
P50:      18,162ms
P95:      55,553ms
平均:     22,933ms
```

**模型分布**:
- deepseek_hm_nv: 1,099 (90.7%), 平均 22,383ms, 262 fallback (auto-key-cycling)
- glm5.1_hm_nv: 108 (8.9%), 平均 23,602ms, 5 fallback
- ATE tier: 5 (0.4%), 平均 129,318ms, 0 fallback (kimi num_attempts=0)

### 1.3 错误明细 (错误级别)

**用户级错误 (6 total)**:
- 5× all_tiers_exhausted (NVCFPexecTimeout → deepseek_hm_nv, 50-62s per key)
- 1× NVStream_TimeoutError

**Key-level errors (hm_tier_attempts, 30min)**:
- deepseek_hm_nv: 78 SSLEOFError + 25 NVCFPexecTimeout = 103
- glm5.1_hm_nv: 518×429 + 38 SSLEOFError + 23 ConnectionResetError + 20 500_nv_error + 1 NVCFPexecTimeout = 600

**Error_detail JSONL (最近20条)**:
- glm5.1_hm_nv: 10条 (6条 all_429:true, 4条 mixed 429+SSLEOF)
- deepseek_hm_nv: 8条 (NVCFPexecTimeout 50-62s/键, 3键起)
- all_tiers_failed: 2条 (kimi num_attempts=0, Pitfall #41验证通过)

### 1.4 容器日志 (docker logs --tail 100)

- **KV末尾**: 3× SSLEOFError on k1 (19:20-19:23 UTC, ~1min间隔)
- **其余**: 全部 [HM-SUCCESS], first-attempt成功占主导
- **键轮转**: k1/k2/k3/k4/k5 正常循环, RR counter: hm_nv_deepseek=6,793
- **无预算断裂**: 无 budget exhausted 日志
- **无全链失败**: 无 ERROR/FAIL/WARN/TIMEOUT 在请求级

---

## 2. 分析与决策

### 2.1 参数评估

**UPSTREAM_TIMEOUT=63** (6.6s → 7.2s headroom to P95):
- R240 +3s后 P95=55,553ms, headroom=63-55.5=7.5s (11.9%)
- 实际 deepseek 键完成时间 20-40s (k1-k5), 均在63s内
- 无 NVCFPexecTimeout 增长趋势 (25 in 30min, 0.83/min — 可接受)
- 继续收敛方向: 63→66→70, 但当前无需加急

**TIER_TIMEOUT_BUDGET_S=115** (budget 52s):
- 有效预算: 115-63=52s
- deepseek 键: 20-40s, 预算安全
- glm5.1 键: 429可在5s内完成, SSLEOF 5s, 预算安全
- kimi 键: 10-40s, 预算安全
- **无预算骨折风险**, 29% 利用率

**TIER_COOLDOWN_S=45** (比HM1高7s):
- 当前无 cooldown 相关错误
- 38 vs 45 差距不影响当前瓶颈
- 可收敛至38但非紧急

**KEY_COOLDOWN_S=38** (已收敛):
- 完整7参数验证中唯一已收敛的参数对
- ATE 事件后无 key-level cooldown 触发
- 维持不变

**MIN_OUTBOUND_INTERVAL_S=15.6**:
- 40s 安全窗口 (15.6×2.5=39s)
- 无 outbound 触发记录
- 可收敛至19.2但非紧急

**HM_CONNECT_RESERVE_S=24** (已收敛):
- SSLEOF 错误在连接层 (78 events in 30min, 2.6/min)
- 当前 24s 预留充足 (6s 实际连接时间)
- 维持不变

### 2.2 决策: 全7参数稳态确认

```yaml
决策: 无变更 (67th consecutive no-change validation)
理由: 99.50% 用户成功率 ≥ 99% 阈值, 
      所有 6 错误均为外部 NVCF 行为 (NVCFPexecTimeout + function-level 429),
      全7参数处于已证明的稳态平衡点,
      SSLEOF/429 是键级浪费非用户失败 (代理键轮转覆盖),
      任何参数变更均为过度优化
```

**收敛状态**:
- ✅ KEY_COOLDOWN_S (38/38 已收敛,R162)
- ✅ HM_CONNECT_RESERVE_S (24/24 已收敛,R234)
- 🔄 UPSTREAM_TIMEOUT (63/70 差7s, 收敛中 60→63→... →70)
- 🔄 TIER_TIMEOUT_BUDGET_S (115/156 差41s, 收敛中)
- 🔄 TIER_COOLDOWN_S (45/38 差7s, 收敛待定)
- 🔄 MIN_OUTBOUND_INTERVAL_S (15.6/19.2 差3.6s, 收敛待定)
- ⬜ PROXY_TIMEOUT (固定300)

---

## 3. 执行

**无执行操作** — 这是稳态确认轮次, 无需修改HM2的docker-compose.yml。

**验证协议** (已完成):
- [x] 米莫霍代理存活: PID 2008535, 正常运行
- [x] hm40006容器健康: Up 14 minutes (healthy)
- [x] 无预算断裂事件
- [x] 无全链失败 (kimi num_attempts=0 确认)
- [x] 键轮转正常 (k1→k2→k3→k4→k5循环)

---

## 4. 预期效果

维持R158+R162基准配置的稳态平衡。HM2容器在当前参数下运行99.50%成功率, 所有外部错误由代理键轮转覆盖。少改多轮原则在此轮次体现为"不改即改" — 稳定性本身就是优化结果。

---

## 5. 评判指标

| 指标 | 当前 | 目标 | 状态 |
|---|---|---|---|
| 用户成功率 | 99.50% | ≥99% | ✅ |
| P50 延迟 | 18.2s | <30s | ✅ |
| P95 延迟 | 55.6s | <UPSTREAM_TIMEOUT(63s) | ✅ |
| 错误数 | 6/1212 | <10/min | ✅ (0.2/min) |
| 429/429键 | 0/518 | 键级为0 | 🔄 (外部NVCF限制) |
| 预算骨折 | 0 | 0 | ✅ |
| kimi trigger | 0 | 0 (防n=0) | ✅ |

---

## ⏳ 轮到HM2优化HM1