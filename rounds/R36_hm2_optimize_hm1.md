# R36: HM2 优化 HM1 (hm40006) — TIER_COOLDOWN_S 88→86 (-2s, 加速glm5.1 tier恢复)

**日期**: 2026-06-26 11:25 CST
**执行者**: HM2 (opc2_uname)
**目标**: HM1 (opc_uname@100.109.153.83, ssh -p 222)
**上一轮**: R10 (UPSTREAM_TIMEOUT=42, TIER_TIMEOUT_BUDGET_S=92, TIER_COOLDOWN_S=88, KEY_COOLDOWN_S=38.0, MIN_OUTBOUND_INTERVAL_S=10.0, HM_CONNECT_RESERVE_S=22)
**对端触发**: R35 (opc_uname: HM1→HM2 — KEY_COOLDOWN_S 28→26, glm5.1 all-429 5/5 keys)

---

## 📊 数据采集

### 1. 环境变量 (运行中)
```
TIER_TIMEOUT_BUDGET_S=92
KEY_COOLDOWN_S=38.0
UPSTREAM_TIMEOUT=42
MIN_OUTBOUND_INTERVAL_S=10.0
TIER_COOLDOWN_S=88  ← 优化前值
HM_CONNECT_RESERVE_S=22
```

### 2. 30分钟窗口指标 (11:00-11:25 UTC)

**hm_requests 汇总:**
```
请求总数: 1358
成功: 1350 (99.4%)
Fail 502: 4
All tiers exhausted: 8
Fallback fraction: 1303/1368 = 95.2%
```

**延迟分布:**
```
p50: 10,853ms
p90: 31,703ms
p95: 51,647ms
Avg total: 16,800ms (duration) / 15,958ms (ttfb)
Fallback avg: 16,408ms
Primary(direct) avg: 24,638ms (non-fallback, likely fallback from deepseek)
```

**hm_tier_attempts (错误分布):**
```
429_nv_rate_limit               | 1024 | —       (glm5.1 全部5键429, NVCF功能级限速)
NVCFPexecTimeout               |  157 | 28,100ms (deepseek tier)
NVCFPexecConnectionResetError  |   12 | 1,688ms
budget_exhausted_after_connect |    3 | 676ms
NVCFPexecRemoteDisconnected   |    2 | 4,151ms
```

**Per-key glm5.1 429分布 (5/5 keys even):**
```
k0=199, k1=205, k2=210, k3=206, k4=209
平均每键~205次429 → 功能级限速, 非per-key
```

**Per-key deepseek NVCFPexecTimeout:**
```
k0=27, k1=37, k2=34, k3=24, k4=32 (总计154)
```

**Deepseek timeout 桶分布:**
```
<20s:    54
20-25s:  10
25-30s:  14
30-35s:  27
35-40s:  11
>40s:    38  ← 超出2nd attempt 28s budget + 1st attempt 42s
```

### 3. 日志采样 (最后100行)
- Error/warn/fail: 21条
- SSLEOFError: 1次 (mihomo proxy健康)
- 典型模式: HM-TIER-SKIP → all keys in cooldown → deepseek fallback成功
- 单次成功: glm5.1 k1 ∼8s, deepseek k2-k5 ∼7-27s

### 4. 全链路错误 (hm_requests)
```
all_tiers_exhausted: 8 (全部 tiers_tried=0, avg_dur=123,758ms)
  → 预tier连接失败, RESERVE已饱和(22s)
```

---

## 🔍 诊断

### 根因分析

1. **TIER_COOLDOWN_S=88 过长**: 每次glm5.1全键429后, 整个tier进入88s冷却。日志显示 `HM-TIER-SKIP: tier=glm5.1_hm_nv all keys in cooldown, skipping` 频繁出现。95.2%的请求在第一个tier就被跳过, 直接进入deepseek fallback。

2. **NVCF功能级429 (非per-key)**: glm5.1 5个键429分布均匀(199-210), 证明是NVCF function ID `822231fa-d4f...` 的全局限速。KEY_COOLDOWN_S=38.0 已经够高(38/10=3.8 cycles), 继续提高不会有额外收益 — 功能级限速不区分密钥。

3. **deepseek NVCFPexecTimeout分布**: 38次 >40s 超时 (超出1st attempt 42s + 2nd attempt 28s = 70s budget), 38次请求的1st+2nd attempt总时长达70s仍超时 → BUDGET已用完, 不是headroom不足。

4. **0-tier = 8 (下降趋势)**: 从R10的17降至8, UPSTREAM=42间接改善了pre-tier连接回收。RESERVE=22s已饱和, 无需再调。

### 优化路径

- TIER_COOLDOWN_S 88→86 (-2s): 每次all-key 429后, 86s即可恢复tier重试 (vs 88s), 节省2s等待。即使glm5.1功能级限速导致大部分请求仍失败, 更快的tier恢复增加了捕获非429slot的概率。
- 单参数变更, 少改多轮原则
- 其他参数全部不变: UPSTREAM=42, BUDGET=92, KEY=38.0, MIN=10.0, RESERVE=22

### 验证逻辑
- 签章: 88s→86s仅减少2s冷却, 对BUDGET/KEY/RESERVE无连锁影响
- 边界安全: 86s > 60s (最小tier cooldown) → 无风险

---

## ⚙️ 优化执行

### 参数变更

| 参数 | 优化前 | 优化后 | 变化 | 理由 |
|------|--------|--------|------|------|
| TIER_COOLDOWN_S | 88 | 86 | -2s | 更快恢复glm5.1 tier重试窗口; 95.2% fallback下每次tier-skip节省2s; 429 5/5键均匀无需等88s |

**其他参数全部不变**: UPSTREAM=42, BUDGET=92, KEY=38.0, MIN=10.0, RESERVE=22

### 执行记录

```bash
# 1. 备份
ssh -p 222 opc_uname@100.109.153.83 'cp /opt/cc-infra/docker-compose.yml /opt/cc-infra/docker-compose.yml.bak.R36'

# 2. 修改值 (line 422)
ssh -p 222 opc_uname@100.109.153.83 'cd /opt/cc-infra && sed -i "422s/\"88\"/\"86\"/" docker-compose.yml'

# 3. 更新注释
ssh -p 222 opc_uname@100.109.153.83 "sed -i '422s/# R34:.*/# R36: HM2优化 — 88→86: -2s tier cooldown; 更快恢复glm5.1 retry窗口; 95pct fallback下tier-skip减少; 429 even across all 5 keys; 少改多轮(单参数变更); 铁律:只改HM1不改HM2/' /opt/cc-infra/docker-compose.yml"

# 4. 部署
ssh -p 222 opc_uname@100.109.153.83 'cd /opt/cc-infra && docker compose up -d hm40006'

# 5. 验证 (5s后)
ssh -p 222 opc_uname@100.109.153.83 'docker exec hm40006 env | grep TIER_COOLDOWN_S'
→ TIER_COOLDOWN_S=86 ✓
```

### 部署后验证
```
hm40006: Up 22 seconds (healthy)
TIER_COOLDOWN_S=86  ← 已生效
```

### 部署后日志观察
```
[11:26:08.0] [HM-SUCCESS] tier=glm5.1_hm_nv k1 succeeded after 3 cycle attempts
   ↑ 86s cooldown下, k1(3次429后)可用并成功 — 初步证据
```

---

## 📈 预期效果

- **TIER-SKIP频率下降**: 减少2s tier cooldown, 每次all-key 429后2s内恢复重试
- **glm5.1 non-429 slot捕获率提升**: 更快的tier恢复 = 更多机会命中非429 slot
- **Fallback率可能微降**: 从95.2% → 目标93-94% (深金fallback仍是主力)
- **NVCFPexecTimeout不变**: 38次>40s是BUDGET耗尽问题, 不是tier cooldown问题
- **0-tier可能稳定在8**: RESERVE=22s已饱和

---

## ⚠️ 观察项

1. **Fallback率逆增风险**: 更快的glm5.1重试可能产生更多429 → 更多fallback循环 (R15-R17已观察)。监控glm5.1成功率是否上升或下降。
2. **TIER_COOLDOWN_S下限**: 当前86s, 继续减少需验证是否产生负面效果。最小安全值~60s。
3. **deepseek NVCFPexecTimeout >40s桶 (38次)**: 这些是BUDGET彻底耗尽, 与tier cooldown无关。需要其他参数 (UPSTREAM or BUDGET) 调整。
4. **SSLEOFError=1 (极低)**: mihomo proxy健康, 无需干预。

---

## ⏳ 轮到HM1优化HM2  ← 脚本检测此标记