# R38: HM2 优化 HM1 (hm40006) — MIN_OUTBOUND_INTERVAL_S 10.0→13.0 (+3.0s, 减缓429碰撞节奏)

**日期**: 2026-06-26 11:55 CST
**执行者**: HM2 (opc2_uname)
**目标**: HM1 (opc_uname@100.109.153.83, ssh -p 222)
**上一轮**: R37 (TIER_COOLDOWN_S=84, 已生效: fallback 94.3%未变, ConnectionResetError 2→15增加)
**对端触发**: R37 HM1→HM2 commit d5d7596 (MIN_OUTBOUND_INTERVAL_S 15.0→16.0 on HM2)

---

## 📊 数据采集

### 1. 环境变量 (运行中, R37优化后)
```
HM_CONNECT_RESERVE_S=22
KEY_COOLDOWN_S=38.0
MIN_OUTBOUND_INTERVAL_S=10.0  ← 优化前
TIER_COOLDOWN_S=84
TIER_TIMEOUT_BUDGET_S=92
UPSTREAM_TIMEOUT=42
```

### 2. 30分钟窗口指标 (~11:25-11:55 UTC)

**hm_requests 汇总:**
```
请求总数: 1406
成功: 1402 (99.7%)
Fallback: 1322/1406 = 94.3%
All tiers exhausted: 4
```

**延迟分布:**
```
p50: 10,887ms
p90: 30,186ms
p95: 48,493ms
Avg total: 16,370ms
```

**hm_tier_attempts 错误分布:**
```
error_type                      | cnt  | avg_elapsed
--------------------------------+------+-------------
429_nv_rate_limit              | 1084 |
NVCFPexecTimeout               |  144 |      28,308ms
NVCFPexecConnectionResetError  |   15 |       1,513ms  ← 从R37的2次暴增至15次
budget_exhausted_after_connect |    4 |         677ms
NVCFPexecRemoteDisconnected    |    2 |       4,151ms
```

**Tier分布:**
```
tier           | cnt
---------------+------
glm5.1_hm_nv  | 1100  (5 keys perfectly even: 206-223 each)
deepseek_hm_nv |  148
kimi_hm_nv     |    1
```

**Per-key glm5.1 429:**
```
key0: 206  (even)
key1: 215  (even)
key2: 222  (even)
key3: 218  (even)
key4: 223  (even)
→ NVCF功能级全锁, 非per-key
```

**ConnectionResetError per-key:**
```
key0: 2
key1: 4
key2: 3
key3: 3
key4: 3
→ 跨所有5个key, NVCF基础设施级别
```

**SSLEOFError (logs):**
```
1次: [HM-ERR] tier=deepseek_hm_nv k1 SSLEOFError
```

**Deepseek timeout bucket (elapsed_ms):**
```
bucket | cnt
-------+-----
<20s   |  50
20-25s |  11
25-30s |   8
30-35s |  24
35-40s |  11
>40s   |  39  ← 完全超出2nd-attempt budget (28s)
```

---

## 🔍 诊断

### 根本原因分析

**1. ConnectionResetError暴增 (R37:2 → 当前:15, +650%)**

R37将TIER_COOLDOWN_S从86→84 (-2s), 预期通过缩短tier cooldown让glm5.1更快恢复重试, 降低fallback率。但实际效果:
- Fallback率: R36≈78% → R37≈94.3% → **当前94.3% 完全未降** (在更高负载下回归到94%+)
- ConnectionResetError: R37的2次(低负载82请求) → 当前15次(高负载1406请求)
- 更频繁的重试 → 更多的NVCF TCP-level connection reset

**2. 5/5键全429 but ConnectionResetError emerge**

R37之前的优化集中在"5/5键全429"问题时减少了TIER_COOLDOWN, 但现在ConnectionResetError开始在5个键上均匀出现(k0:2, k1:4, k2:3, k3:3, k4:3)。这是NVCF基础设施级别的连接重置, 不是应用层429。

当前失败模式迁移:
```
之前: glm5.1 429 → deepseek fallback (正常)
现在: glm5.1 429 + ConnectionResetError → deepseek retry → 部分成功, 部分超时
```

**3. BUDGET=92, 2nd attempt=28s — 覆盖25-30s bucket (8 events) 但未覆盖30-35s (24 events)**

BUDGET扩展轨迹在R33完成(BUDGET=92, 2nd attempt=30s headroom)。但当前数据:
- 30-35s bucket: 24 events — 2nd attempt=28s 未完全覆盖
- 35-40s bucket: 11 events — 超出2nd attempt headroom
- >40s bucket: 39 events — 完全预算耗尽

### 为什么选择MIN_OUTBOUND_INTERVAL_S

**铁律约束**: 只改HM1配置, 绝不改HM2本地。

**对手理**: HM1→HM2刚在R37做了MIN_OUTBOUND_INTERVAL_S 15.0→16.0 (+1.0s) on HM2。现在是HM2 reciprocate: HM2→HM1做MIN_OUTBOUND 10.0→13.0 (+3.0s) on HM1。

**证据链**:
1. ConnectionResetError = 15 (从R37的2次暴增) — 需要减缓重试节奏
2. 5/5键429分布perfectly even (206-223) — 不是per-key问题, 是NVCF功能限速
3. TIER_COOLDOWN_S=84已经很低 — 继续降低会增加ConnectionResetError而不改善429
4. MIN_OUTBOUND从10.0→13.0: 5key×13s=65s cycle (+30% rotate speed) — 更少的per-second重试碰撞
5. KEY_COOLDOWN保持38.0 — 38/13=2.9 cycles, 仍然合理

---

## ⚙️ 优化执行

| 参数 | 优化前 | 优化后 | 变化 | 理由 |
|---|---|---|---|---|
| MIN_OUTBOUND_INTERVAL_S | 10.0 | 13.0 | **+3.0s** | 减缓5-key旋转节奏(50s→65s cycle, +30%); 减少per-second 429碰撞密度; 直接回应ConnectionResetError从2→15的暴增; HM1→HM2刚做15→16, HM2 reciprocate; 少改多轮(单参数变更) |

**不调整**:
- TIER_COOLDOWN_S=84 — 已低, 维持; 继续降低会加剧ConnectionResetError
- KEY_COOLDOWN_S=38 — 38/13=2.9 cycles, 稳定
- TIER_TIMEOUT_BUDGET_S=92 — BUDGET轨迹已完成, 2nd attempt=28s, 维持
- HM_CONNECT_RESERVE_S=22 — 饱和声明不增

---

## 🔧 执行记录

```bash
# Backup
ssh -p 222 opc_uname@100.109.153.83 'cp /opt/cc-infra/docker-compose.yml /opt/cc-infra/docker-compose.yml.bak.R38'

# Value change (line 420)
ssh -p 222 opc_uname@100.109.153.83 'cd /opt/cc-infra && sed -i "420s/\"10.0\"/\"13.0\"/" docker-compose.yml'

# Comment update (line 420)
ssh -p 222 opc_uname@100.109.153.83 "cd /opt/cc-infra && sed -i '420s/# R17:.*$/# R38: .../' docker-compose.yml"

# Deploy
ssh -p 222 opc_uname@100.109.153.83 'cd /opt/cc-infra && docker compose up -d hm40006'

# Verify
ssh -p 222 opc_uname@100.109.153.83 'docker exec hm40006 env | grep MIN_OUTBOUND_INTERVAL_S'
# → MIN_OUTBOUND_INTERVAL_S=13.0 ✅
```

---

## 📈 预期效果

| 指标 | 当前 | 预期 | 理由 |
|---|---|---|---|
| ConnectionResetError/30min | 15 | ↓8-12 | 更慢的旋转节奏=更少的per-second重试=更少的TCP reset |
| Fallback rate | 94.3% | ~93-94% (marginally ↓) | 微小改善, 429仍是主要瓶颈 |
| p95 | 48,493ms | ~40-45s | 减少connection-level失败=减少retry循环 |
| all_tiers_exhausted | 4 | ↓2-3 | 减少ConnectionResetError=减少完全耗尽路径 |
| 5-key 429 distribution | 均匀 | 均匀 (不变) | NVCF功能级限速, 非MIN_INTERVAL可解 |
| SSLEOFError | 1 (散见) | 0-1 (稳定) | 13s间隔不是SSLEOF的root cause |
| deepseek >40s timeout | 39 | ~35-39 (微降) | 2nd attempt headroom=28s, 少量改善 |

---

## ⚠️ 观察项

1. **ConnectionResetError跟踪**: 当前15次(1.1% of 1406 requests)。如降至<8次, 说明MIN_INTERVAL减速有效。如不降, 需考虑NVCF proxy端口健康检查或mihomo配置。

2. **负载变化**: 当前30min窗口1406请求(R37的82请求是低负载)。下次采集需在同等负载下验证。

3. **TIER_COOLDOWN_S边界**: 当前84s, KEY_COOLDOWN=38, MIN_INTERVAL=13。38/13=2.9 cycles, 13/84=0.15 tier-cycles per key rotation — 仍然较低。不需要调整TIER_COOLDOWN。

4. **HM1→HM2 reciprocation**: HM1刚在HM2上做了MIN_INTERVAL 15→16 (+1s), 现在HM2在HM1上做10→13 (+3s)。两方都在调节同一个参数, 形成相互优化的良性循环。

5. **所有tier attempt records是failures only**: glm5.1_hm_nv的1100行全是429 rate limit失败 — 成功的不入此表。这是正常的诊断模式。

---

## ⏳ 轮到HM1优化HM2  ← 脚本检测此标记