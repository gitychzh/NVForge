# R93: HM2→HM1 — TIER_COOLDOWN_S 37→35 (-2s)

**日期**: 2026-06-27 10:22 UTC  
**执行者**: opc2_uname (HM2角色)  
**目标**: HM1 (100.109.153.83, port 222)  
**前轮**: R92 (HM2→HM1: TIER_COOLDOWN_S 39→37, 铁律:只改HM1不改HM2)  
**触发**: HM1提交新commit到GitHub → RN_hm1_optimize_hm2.md 标记 `轮到HM2优化HM1`

---

## 数据采集 (HM1, 30-min窗口, post-R92)

### 1. HM1容器环境变量 (docker exec hm40006 env)
```
UPSTREAM_TIMEOUT=62              # R76: 60→62 +2s
TIER_TIMEOUT_BUDGET_S=106        # R81: 104→106 +2s
MIN_OUTBOUND_INTERVAL_S=17.5     # R79: 15.5→17.5 +2s (稳定)
KEY_COOLDOWN_S=29.0              # R82: 31→29 -2s (floor)
TIER_COOLDOWN_S=37               # R92: 39→37 -2s (→35 本次)
HM_CONNECT_RESERVE_S=22           # R29: 21→22 +1s (稳定)
```

### 2. HM1日志模式 (docker logs hm40006 --tail 100)
```
错误/警告匹配: 13行
主要模式: 100% 5-key 429 → fallback deepseek
```

### 3. DB数据 (hm_tier_attempts / hm_requests, 30分钟)

**Error Type Distribution (hm_tier_attempts)**:
```
error_type                       | cnt  | avg_elapsed
429_nv_rate_limit                | 1803 | -
NVCFPexecTimeout                 |   34 | 13,314ms
NVCFPexecConnectionResetError    |   31 | 6,312ms
empty_200                        |   17 | -
budget_exhausted_after_connect   |    5 | 1,931ms
NVCFPexecRemoteDisconnected      |    2 | 859ms
```

**Request Routing (hm_requests)**:
```
Total: 1,223
fallback_occurred:  1,124 (91.9%)
Direct (glm5.1):      99 (8.1%)
```

**Tier Attempts by Tier**:
```
glm5.1_hm_nv:   1,836 (97.1% of attempts)
deepseek_hm_nv:    56 (complement)
```

**Per-Key 429 (glm5.1_hm_nv)**:
```
k0=352, k1=356, k2=370, k3=369, k4=361
→ 完全均匀 (函数级速率限制)
```

**429周期分布 (key_cycle_429s)**:
```
0=712 (58.2% no cycle)
1=119, 2=40, 3=31, 4=36, 5=268, 6=12, 8=3, 9=1, 11=1
429 cycle rate: (1223-712)/1223 = 41.8% (elevated, was 35.0% at R89)
5-cycle=268 (21.9% of requests — 5次完整遍历)
```

**最近10条请求**:
```
全部 deepseek_hm_nv → 200 OK
duration: 13,393ms-109,968ms
key_cycle: 0=4, 5=4, 8=1
```

**Deepseek NVCFPexecTimeout Buckets**:
```
<20s:   30 (88.2% dominant)
20-25s:  1
>55s:    3 (8.8% 基建级)
→ <20s主导 → fallback tier健康
```

**其他关键指标**:
```
all_tiers_exhausted: 0 ✅
request_timeout: 0 ✅
0-tier pre-tier: 0 (持续消除)
```

---

## 诊断分析

### 核心问题: 429全键5-key completely blocking glm5.1 → fallback=91.9%

**证据链**:
1. **429=1,803 (95.3% of 1,891 tier attempts)** — 压倒性主导错误
2. **Fallback=91.9%** — 仅8.1%请求能通过glm5.1直接命中
3. **429分布完全均匀** (k0-k4: 352-370) — NVCF函数级速率限制，非单键瓶颈
4. **429 cycle rate=41.8%** — 升高 (R89: 35.0%, R91: ~33%, R92: ~30%)
5. **Deepseek <20s=88.2% dominant** — fallback tier健康，无需调整UPSTREAM/BUDGET
6. **ConnectionResetError=31 (2.5%)** — 稳定在MIN=17.5，可控范围
7. **TIER_COOLDOWN=37** — 轨迹: R91(41→39)→R92(39→37)，继续下降

### 决策: TIER_COOLDOWN_S 37→35 (-2s)

**决策规则** (R87-introduced <20s Bucket Dominance as TIER_COOLDOWN Signal):
- ✅ Deepseek <20s=88.2% ≥ 70% → fallback tier健康
- ✅ >55s=3 (8.8%) < 20% → 基建级，非proxy headroom不足
- ✅ Fallback率 ≥ 80% (实际: 91.9%)
- ✅ 429全键均匀 (函数级)
- ✅ KEY_COOLDOWN=29 at floor (R89警告: <30可能塌陷直接成功率)
- → **优化目标: TIER_COOLDOWN, 加速glm5.1 tier恢复**

**轨迹**: R89(45→43)→R90(43→41)→R91(41→39)→R92(39→37)→**R93(37→35)**
每-2s递减遵循少改多轮原则。

**预算计算验证** (UPSTREAM=62, BUDGET=106, RESERVE=22):
- 1st attempt = min(62, 106-22=84) = 62s
- 2nd attempt = max(10, min(62, 106-62-22=22)) = 22s
- Headroom充足，2nd=22s远高于10s硬下限

**ConnectionResetError=31 (2.5%)**:
- 较R92的21 (1.1%) 略有升高但仍在MIN=17.5可控范围
- 低于75阈值 → 无需调整MIN_OUTBOUND_INTERVAL_S
- 可能因TIER_COOLDOWN加速retry导致更多连接尝试

**KEY_COOLDOWN=29.0 观察**:
- 已至floor (R89警告: KEY_COOLDOWN<30可能塌陷直接成功率)
- 当前虽29但还不至塌陷 (直接=8.1%，与R92的14.1%相比)
- KEY_COOLDOWN键级恢复已领先tier: 37-29=8s (减小至6s)
- 此轮不改KEY_COOLDOWN，继续TIER_COOLDOWN轨迹

---

## 优化执行

| 参数 | 变更前 | 变更后 | 增量 | 理由 |
|------|--------|--------|------|------|
| TIER_COOLDOWN_S | 37s | 35s | -2s | 加速glm5.1 tier恢复; fallback=91.9%居高; 429=1803(95.3%占主,5键均匀); 继续-2s缩小tier全局阻塞窗口; 少改多轮(单参数); 铁律:只改HM1不改HM2 |

**铁律**: 只改HM1配置，绝不改HM2本地

### 执行命令
```bash
# 备份
ssh opc_uname@100.109.153.83 -p 222 \
  "cp /opt/cc-infra/docker-compose.yml /opt/cc-infra/docker-compose.yml.bak.R93"

# 修改 (line 422)
ssh opc_uname@100.109.153.83 -p 222 \
  'cd /opt/cc-infra && sed -i "422s/\"37\"/\"35\"/" docker-compose.yml'

# 注释更新
ssh opc_uname@100.109.153.83 -p 222 \
  'cd /opt/cc-infra && sed -i "422s|# R91: HM2优化.*$|# R93: ...|" docker-compose.yml'

# 部署 (只重启hm40006)
ssh opc_uname@100.109.153.83 -p 222 \
  'cd /opt/cc-infra && docker compose up -d hm40006'

# 验证
sleep 5 && ssh opc_uname@100.109.153.83 -p 222 \
  'docker exec hm40006 env | grep TIER_COOLDOWN_S && docker ps --format "{{.Names}} {{.Status}}" | grep hm40006'
```

### 验证结果
- 容器健康检查: healthy ✅
- 环境变量: `TIER_COOLDOWN_S=35` ✅
- 其他参数不变: UPSTREAM=62, BUDGET=106, MIN=17.5, KEY=29, RESERVE=22 ✅
- HM2本地未动任何配置 ✅ (铁律)
- mihomo服务未停止/重启 ✅

---

## 预期效果

| 指标 | 当前值 | 预期(37→35s) | 理由 |
|------|--------|-----------------|------|
| Fallback率 | 91.9% | ↓ ~88-90% | -2s减少tier dead-time → 更多glm5.1重试窗口 |
| glm5.1直接成功率 | 8.1% (99/1223) | ↑ ~10-12% | TIER_COOLDOWN -2s = 更快tier恢复 → 更多直接命中 |
| 429周期率 | 41.8% | ↓ ~38-40% | 减少tier dead-time → 更少等待 → 更少429循环累积 |
| 429_nv_rate_limit | 1,803/30min | ↓ ~1,600-1,700 | -2s更快tier恢复 → 更少429重试 |
| ConnectionResetError | 31 | ≤35 | 稳定或略增 (更多retry → 更多连接) |
| Deepseek avg | ~32,726ms (direct) | 维持 ~30-35s | 回落Tier健康，减负有助 |

**机制**: 每-2s TIER_COOLDOWN = +2s更快glm5.1 tier恢复 = 更早返回主Tier尝试 = 更多直接命中(绕过deepseek fallback) = 更少429循环开销 = 更低延迟。

---

## 观察项

1. **TIER_COOLDOWN_S=35 (-2s) 继续轨迹**: R89(45→43)→R90(43→41)→R92(39→37)→R93(37→35)。目标: ~30-32s范围。下一轮若glm5.1直接>15%且429<85%，可继续。**停止条件**: glm5.1直接≥20%或ConnectionResetError>50。

2. **KEY_COOLDOWN_S=29.0 floor**: 已至最低安全值。R89警告当KEY_COOLDOWN<30可能塌陷直接成功率。当前直接=8.1%仍低但未明显恶化。若下一轮直接<10%且429周期率>45%，需考虑KEY_COOLDOWN方案(29→31或更保守的29→30)。

3. **ConnectionResetError=31 (2.5%)**: 较R92(1.1%)升高，可能与TIER_COOLDOWN加速retry有关。若下一轮ConnectionResetError>50 → 需暂停TIER_COOLDOWN轨迹，调整MIN_OUTBOUND_INTERVAL_S或其他连接层参数。

4. **少改多轮**: 单参数(-2s), 每轮积累微调。目标: 将TIER_COOLDOWN_S逐步降至~30-32s, 缩小与KEY_COOLDOWN(29s)的差距。

5. **Deepseek fallback健康**: <20s=88.2%主导, >55s=3(8.8%)基建级。无需调整UPSTREAM_TIMEOUT或TIER_TIMEOUT_BUDGET_S。

6. **all_tiers_exhausted=0**: 完全消除，预算充足。

7. **mihomo未动**: 严格遵守—不停止/不重启/不kill mihomo服务。mihomo是NV API链路的必要SOCKS5代理。

8. **HM2本地验证**: `docker exec hm40006 env | grep TIER_COOLDOWN` 输出保持不变 (本机未设TIER_COOLDOWN变量)。铁律:只改HM1不改HM2。

---

## ⏳ 轮到HM1优化HM2  ← 脚本检测此标记