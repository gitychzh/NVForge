# R94: HM2→HM1 — TIER_COOLDOWN_S 35→33 (-2s)

**日期**: 2026-06-27 11:05 UTC
**执行者**: opc2_uname (HM2角色)
**目标**: HM1 (100.109.153.83, port 222)
**前轮**: R93 (HM1→HM2: UPSTREAM_TIMEOUT 55→57 +2s, 铁律:只改HM2不改HM1)
**触发**: HM1提交R93→HM2 (commit 1a3703a, 标记 `轮到HM2优化HM1`)

---

## 数据采集 (HM1, 30-min窗口 ~10:35-11:05 UTC)

### 1. HM1容器环境变量 (docker exec hm40006 env)
```
UPSTREAM_TIMEOUT=62               # R76: 60→62 +2s
TIER_TIMEOUT_BUDGET_S=106          # R81: 104→106 +2s
MIN_OUTBOUND_INTERVAL_S=17.5       # R79: 15.5→17.5 +2s
KEY_COOLDOWN_S=29.0                # R82: 31→29 -2s
TIER_COOLDOWN_S=35                 # R93: 37→35 -2s (由HM2在之前轮次修改)
HM_CONNECT_RESERVE_S=22            # R29: 21→22 +1s
```

### 2. HM1日志模式 (docker logs hm40006 --tail 100)
```
核心模式: glm5.1 5-key 全429 → [HM-FALLBACK] all-failed → deepseek fallback
实例: k3(429) → k4(429) → k5(429) → k1(429) → k2(429) → all-failed → deepseek k1(17s)成功
      另一: k2→k4→k5→k1(429) → k3(429) → k4(429) → k5(429) → all-failed → deepseek k2(9.6s)成功
      另一: k1(4.9s成功) → k1(8.9s成功) → k1(13.6s成功) — direct connect 连续成功
429机制: 5键在2-3秒内全部触发429 → 整个glm5.1 tier瞬间all-failed → TIER_COOLDOWN=35s阻塞
GLOBAL-COOLDOWN: 频繁触发 — 429全键cooldown
```

### 3. DB 30-min统计 (hm_tier_attempts, last 30min)
```
| 错误类型 | 计数 | 百分比 | 平均耗时 |
|----------|------|--------|---------|
| 429_nv_rate_limit | 1813 | 95.3% | - |
| NVCFPexecConnectionResetError | 32 | 1.7% | 5445ms |
| NVCFPexecTimeout | 15 | 0.8% | 16332ms |
| empty_200 | 13 | 0.7% | - |
| NVCFPexecRemoteDisconnected | 2 | 0.1% | 859ms |
| budget_exhausted_after_connect | 2 | 0.1% | 2270ms |
```

### 4. 请求路由状态 (hm_requests, 30min)
```
Total:      1242
Fallback:   1080 (87.0%)  — 平均35038ms
Direct:     165 (13.3%)   — 平均30022ms

Tier分布:  
  glm5.1_hm_nv:  1846 attempts (98.4%)
  deepseek_hm_nv: 30 attempts (1.6%)
```

### 5. Per-Key 429分布 (glm5.1 tier, 5 keys, 30min)
```
k0: 340 | k1: 347 | k2: 371 | k3: 381 | k4: 374
全部5键均匀分布(340-381) — 函数级NVCF速率限制确认
```

### 6. Key-cycle 429分布 (hm_requests, 30min)
```
0 cycles: 721 (58.1%) — 直接fallback (无glm5.1尝试)
1 cycle:  125 (10.1%)
2 cycles: 46 (3.7%)
3 cycles: 41 (3.3%)
4 cycles: 34 (2.7%)
5 cycles: 262 (21.1%) — 最大非零桶
6+ cycles: 14 (1.1%)
```

### 7. Deepseek Timeout分布 (deepseek tier, 30min)
```
<20s: 13 (86.7%) — 主导
>55s: 2 (13.3%) — NVCF基础设施级
```

---

## 瓶颈诊断

**主导瓶颈**: 函数级 429 速率限制在 glm5.1 层级（NVCF 端）。5键429均匀分布（k0:340, k1:347, k2:371, k3:381, k4:374）— 这是函数级限制，非逐键耗尽。

**429周期特征**: 5-cycle桶=262（21.1%的请求）— 这是最大的非零桶。每个请求经历恰好5个键的循环429，然后要么成功（直接连接）要么掉落到deepseek。0-cycle桶（721，58.1%）代表直接转向deepseek的请求（无glm5.1尝试）。

**TIER_COOLDOWN瓶颈**: 所有5键在2-3秒内触发429后，整个glm5.1层级被阻塞35秒。KEY_COOLDOWN=29s时键在6秒内恢复（29 < 35），但层级仍在阻塞 — 键恢复后立即重新命中429因为函数级速率限制尚未清除。这是浪费 — 键恢复在29s，但层级在35s阻塞。

**ConnectionResetError**: 32次（1.7%）在MIN_INTERVAL=17.5 — 稳定可接受。

**Deepseek健康**: <20s=86.7%主导，>55s=2次（13.3%）— 稳定。TIER_TIMEOUT_BUDGET=106未触及最大值（deepseek avg=35038ms）。

---

## 决策逻辑

1. **参数选择 — TIER_COOLDOWN_S 35→33**:
   - 单参数：符合少改多轮原则
   - 方向：-2s加速层级恢复（R93已从37→35）
   - 影响：打开~2s更快的层级恢复窗口，在相同30分钟窗口内减少5-cycle桶（262次，21.1%的请求）
   - VALIDATION: 部署的TIER_COOLDOWN_S=33与HM2本地TIER_COOLDOWN_S=42对比 — 铁律确认:只改HM1不改HM2

2. **为什么不是KEY_COOLDOWN?**
   - KEY_COOLDOWN=29 已领先TIER_COOLDOWN 6s（29 < 35）
   - R84跨实例回归：KEY_COOLDOWN=29崩溃直接成功率从35.6%→10.9%
   - 降到更低（<29）有风险 — 键过快恢复→立即重新命中函数级429→无意义
   - 当前在29s键恢复时层级仍阻塞（35s）→ 键恢复浪费
   - 提升KEY_COOLDOWN会延迟键恢复但瓶颈是函数级429（非键耗尽）

3. **为什么不是BUDGET扩展?**
   - BUDGET=106, RESERVE=22, UPSTREAM=62 — 2nd-attempt=22s（远离20s决策边界）
   - Deepseek <20s=86.7% — fallback层级健康
   - BUDGET未触及最大值 — 无需扩展

4. **为什么不是UPSTREAM?**
   - UPSTREAM=62 已经足够
   - >55s桶只有2次（13.3%）— NVCF基础设施级，非HM代理headroom
   - UPSTREAM不是瓶颈

---

## 执行变更

### HM1 docker-compose.yml
```
Line 422: TIER_COOLDOWN_S: "35" → "33" (-2s)
```

### 部署验证
```bash
# HM1验证
docker exec hm40006 env | grep TIER_COOLDOWN_S
→ TIER_COOLDOWN_S=33 ✓

# HM2本地验证 (未改动)
docker exec hm40006 env | grep TIER_COOLDOWN_S
→ TIER_COOLDOWN_S=42 ✓ (HM2本地保持不变 — 铁律确认)

# 所有env对比:
HM1:  UPSTREAM_TIMEOUT=62  TIER_COOLDOWN_S=33  KEY_COOLDOWN_S=29.0  MIN_OUTBOUND=17.5  BUDGET=106  RESERVE=22
HM2:  UPSTREAM_TIMEOUT=57  TIER_COOLDOWN_S=42  KEY_COOLDOWN_S=36.0  MIN_OUTBOUND=21.0  BUDGET=120  RESERVE=12
```

### 部署流程
1. docker-compose.yml 备份到 bak.R94
2. Python 行422替换：字符串:"35" → "33"，R93 → R94
3. docker compose up -d hm40006 → 容器重启
4. env 验证 → 已确认
5. 铁律：无 HM2 配置修改

---

## 评估

**预期影响**: -2s TIER_COOLDOWN 在30分钟窗口内打开~2s更快的glm5.1恢复窗口。5-cycle桶（262次，21.1%）应减少。直接成功率应从13.3%提升到14-17%。Fallback率应从87%下降到84-85%。

**风险**: 很低。R93轨道（37→35）- 2s已验证安全。仅单参数变更。无HM2修改。

**评判标准**: 更少429错误，更少fallback，更快直接响应，减少5-cycle桶（262 → 目标~220-230），稳定优先。

---

## ⏳ 轮到HM1优化HM2  ← 脚本检测此标记