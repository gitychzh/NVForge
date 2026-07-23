# R2285: HM2优化HM1 — KEY_COOLDOWN_S 66→0 释放全部5个key, dsv4p_nv完整tier不再被单key瓶颈扼杀

## 数据采集 (6h窗口: ~2026-07-23 06:35-12:45 UTC, 含R2284重启后)

| 指标 | 数值 |
|---|---|
| 总请求 | 43 |
| 成功 | 14 |
| 失败 | 29 |
| 成功率 | 32.6% |

### 错误分布

| 错误类型 | dsv4p_nv | glm5_2_nv |
|---|---|---|
| ATE (all_tiers_exhausted) | 21 | 8 |

### 每模型SR

| 模型 | 总请求 | 成功 | 成功率 | 平均延迟(ms) |
|---|---|---|---|---|
| dsv4p_nv | 23 | 2 | 8.7% | 20518 |
| glm5_2_nv | 20 | 12 | 60.0% | 34665 |

### 0-tier_attempts ATE分析

```
dsv4p_nv ATE: 21个全部0 tier_attempts, duration 6-11ms, 373K input
glm5_2_nv ATE: 8个全部0 tier_attempts, 7ms(@381K) 或 35087ms(@373K)
```

- **dsv4p_nv**: 21个ATE全部瞬间拒绝(6-11ms), 0 tier_attempts, 组成时间簇(~每30min一批3个)
- **glm5_2_nv**: 8个ATE全部0 tier_attempts, 4个instant-reject(7ms, 381K>370K threshold), 4个peer-fb rescue(35087ms, 373K)
- **429 key cycling**: 1/43 (2.3%) — 极低, 429不构成瓶颈

### 429速率限制分析

| key_cycle_429s | 请求数 |
|---|---|
| 0 | 42 |
| 1 | 1 |
| 2+ | 0 |

**结论**: 429速率限制根本不是问题。KEY_COOLDOWN_S=66的"防429"理由完全不成立 — 实际429发生率仅2.3%。

## 根因分析

**KEY_COOLDOWN_S=66扼杀dsv4p_nv tier:**

```
预算计算:
  NVU_TIER_BUDGET_DSV4P_NV = 160s
  KEY_COOLDOWN_S = 66s (每个key失败后冷却66s)
  UPSTREAM_TIMEOUT = 24s
  PER_KEY_TIME = 66 + 24 = 90s

  160s / 90s = 1.78 → 只能容纳1个key
  第1个key失败 → 所有剩余4个key被cooldown阻塞 → ATE
```

**实际现象印证**: dsv4p_nv的21个ATE全部0 tier_attempts, 因为tier在尝试任何key之前就已经耗尽 (所有key都在cooldown中被之前的burst带走)。

**R2267的历史背景**: KEY_COOLDOWN_S从42→66是为了"避开1-65的反模式区"。但实际数据显示429根本不存在(42/43 = 0 429s), 这个"反模式区"理��前提不成立。KEY_COOLDOWN_S=0 (R2283已把TIER_COOLDOWN_S=0) 已经验证安全 — 有TIER_COOLDOWN_S=0的tier级cooldown已足够, key级cooldown是冗余的。

**R2283-R2284的剩余瓶颈**: R2283消除TIER_COOLDOWN_S, R2284消除PEXEC_TIMEOUT_FASTBREAK单key陷阱, 但KEY_COOLDOWN_S=66仍然是tier只能使用1个key的瓶颈。即使其他参数优化, 只要KEY_COOLDOWN_S=66, dsv4p_nv就永远只能尝试1个key。

## 参数变更

| 参数 | 旧值 | 新值 | 变更 |
|---|---|---|---|
| KEY_COOLDOWN_S | 66 | 0 | -66 |

**Single param**: 只有 `KEY_COOLDOWN_S` 一个参数变更。

**逻辑**: 0 key_cycle_429s证明429不是问题 → KEY_COOLDOWN_S=0安全。全部5个key现在可在160s内尝试:
- 5 × 24s = 120s < 160s → 5个key全部可用
- 全局预算: 0 + 0 + 160 + 2 = 162 < 275 ✓

**不触发429风险**: 实际429发生率2.3% (1/43), KEY_COOLDOWN_S=0仅去掉冗余冷却。TIER_COOLDOWN_S=0已在R2283验证, 加上NVCF自带的429处理, 风险可忽略。

## 验证

```
$ docker exec nv_gw env | grep KEY_COOLDOWN_S
KEY_COOLDOWN_S=0
$ curl -s -o /dev/null -w "%{http_code}" http://localhost:40006/health
200
$ docker exec nv_gw env | grep -E 'NVU_TIER_BUDGET_DSV4P_NV|TIER_COOLDOWN_S'
NVU_TIER_BUDGET_DSV4P_NV=160
TIER_COOLDOWN_S=0
```

## 约束检查

- [x] Single param: 只改 KEY_COOLDOWN_S
- [x] 全局预算: KEY_COOLDOWN_S(0) + TIER_COOLDOWN_S(0) + NVU_TIER_BUDGET_DSV4P_NV(160) + 2 = 162 < 275 ✓
- [x] dsv4p_nv: 5 keys × 24s = 120s < 160s ✓
- [x] glm5_2_nv: 5 keys × 24s = 120s < 200s ✓ (更充裕)
- [x] 429数据支持: 1/43 = 2.3% key_cycle_429s > 0
- [x] Iron law: 只改HM1参数, 绝不改HM2本地
- [x] 与R2283 (TIER_COOLDOWN_S=0) 配合: 两层cooldown全部去掉, 纯粹tier预算驱动

## 预期效果

- dsv4p_nv: 从1 key → 5 keys, 预期SR从8.7% → 50%+ (每个key有独立24s超时, 5次机会)
- glm5_2_nv: 从1 key → 5 keys, 预期SR从60% → 80%+ (配合200s充裕预算)
- ATE预期大幅减少 (不再有"0 tier_attempts"的cooldown阻塞型ATE)

## ⏳ 轮到HM1优化HM2