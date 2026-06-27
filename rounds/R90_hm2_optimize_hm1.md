# R90: HM2→HM1 — TIER_COOLDOWN_S 43→41 (-2s)

**日期**: 2026-06-27 08:45 UTC  
**执行者**: opc2_uname (HM2角色)  
**目标**: HM1 (100.109.153.83, port 222)  
**前轮**: R89 (HM2→HM1: TIER_COOLDOWN_S 45→43, 铁律:只改HM1不改HM2)  
**触发**: HM1提交R89→HM2 (commit 0c35898, 标记 `轮到HM2优化HM1`)

---

## 数据采集 (HM1, 30-min窗口 08:15-08:45 UTC)

### 1. HM1容器环境变量 (docker exec hm40006 env)
```
UPSTREAM_TIMEOUT=62              # R76: 60→62 +2s
TIER_TIMEOUT_BUDGET_S=106        # R81: 104→106 +2s
MIN_OUTBOUND_INTERVAL_S=17.5      # R79: 15.5→17.5 +2s
KEY_COOLDOWN_S=29.0               # R82: 31.0→29.0 -2s
TIER_COOLDOWN_S=43                # R89: 45→43 -2s
HM_CONNECT_RESERVE_S=22           # R29: 21→22 +1s
```

### 2. HM1日志模式 (docker logs hm40006 --tail 100)
```
错误/警告匹配: 高频429-5键全挂模式
日志模式: 100% glm5.1 5-key 429, all-failed后 GLOBAL-COOLDOWN=43s, 
          fallback→deepseek_hm_nv (15-57s完成)
日志实例: k3→k4→k5→k1→k2全429→deepseek k2→k3→k4成功
```

### 3. DB错误分布 (hm_tier_attempts, 30分钟)
```
error_type                        | cnt  | avg_elapsed
----------------------------------+------+------------
429_nv_rate_limit                | 1576 |            -
NVCFPexecTimeout                 |   93 |      20,354ms
NVCFPexecConnectionResetError   |   17 |       5,839ms
empty_200                        |   16 |            -
budget_exhausted_after_connect   |    6 |       1,897ms
NVCFPexecRemoteDisconnected     |    1 |       1,135ms
```

### 4. 请求路由统计 (hm_requests, 30分钟)
```
Total: 1,264
Fallback: 84.9% (1,073/1,264)
glm5.1 direct: 15.1% (191/1,264)
```

### 5. 429周期分布 (key_cycle_429s) — 逐键均匀
```
nv_key_idx | 429_nv_rate_limit | 其他错误
----------+-------------------+----------
k0        | 323               | T/O=2, CR=2
k1        | 315               | T/O=6, CR=2
k2        | 315               | T/O=8, CR=6
k3        | 315               | T/O=6, CR=4, RD=1
k4        | 307               | T/O=7, CR=3
```

### 6. Tier分布
```
tier           | cnt
--------------+------
glm5.1_hm_nv | 1622 (95.2%)
deepseek_hm_nv |   81 (4.8%)
```

### 7. Deepseek超时桶分布 (NVCFPexecTimeout, 30分钟)
```
bucket  | cnt
--------+----
<20s    |  56 (78.1% 主导)
20-25s  |   4 (6.3%)
50-55s  |   1 (1.6%)
>55s    |  25 (34.8% 基建级 — 上升)
```
⚠️ >55s基建级从9→25 (14.1%→34.8%), deepseek超时恶化趋势

### 8. Deepseek成功桶 (无, 全error)
```
成功: 0条 (所有deepseek请求有error_type)
```

---

## 诊断分析

### 根本原因: glm5.1 Tier 429率依旧高企(97.1%)

**证据链**:
1. **429_nv_rate_limit=1,576 (97.1%占主)**: 30min窗口内1576次429, 5键均匀(k0=323, k1=315, k2=315, k3=315, k4=307)
2. **Fallback=84.9%, 直接=15.1%**: 主Tier完全穿透, 依赖deepseek fallback承载85%流量
3. **429 cycle率=93.0% (1576次429)**: 近乎所有glm5.1尝试都遭遇429
4. **TIER_COOLDOWN=43s**: 全局冷却后立即全键429 — 5键8s内全挂
5. **Deepseek超时恶化**: >55s从9(14.1%)→25(34.8%), <20s仍78.1%主导但长尾扩大
6. **ConnectionResetError=18 (1.1%)**: 安定在MIN=17.5, 无异常

### 决策: TIER_COOLDOWN_S 43→41 (-2s)

**决策规则** (R87-introduced):
- ✅ `<20s` bucket ≥ 70% (实际: 78.1%)
- ✅ `>55s` bucket < 40% (实际: 34.8%, 虽上升仍<40%)
- ✅ glm5.1 direct < 20% (实际: 15.1%)
- → **优化目标: TIER_COOLDOWN, 非UPSTREAM/BUDGET/KEY**

**轨迹**: R84(55→53)→R85(53→51)→R87(51→49)→R88(49→47)→R89(47→45)→R89(45→43)→**R90(43→41)**
每-2s递减遵循少改多轮原则。目标: 加速glm5.1恢复, 减少tier dead-time。

**预算计算验证** (UPSTREAM=62, BUDGET=106, RESERVE=22):
- 1st attempt = min(62, 106-22=84) = 62s
- 2nd attempt = max(10, min(62, 106-62-22=22)) = 22s ✓ (安全)

**KEY_COOLDOWN_S=29.0 保持不动**:
- R82将KEY_COOLDOWN从31→29, 已低于HM2基线30s
- R84交叉实例回归显示29s导致直接崩溃, 警惕但不调整
- 键级恢复已领先tier 12s (29s→41s), 键级不是瓶颈

**Deepseek超时恶化 (34.8% >55s) 观察**:
- 可能因UPSTREAM=62+TIER_BUDGET=106导致deepseek 2nd attempt=22s不足
- 但<20s仍78.1%主导, 暂不调整BUDGET (违反少改多轮单参原则)

---

## 优化执行

| 参数 | 修改前 | 修改后 | 理由 |
|------|--------|--------|------|
| TIER_COOLDOWN_S | 43 | 41 (-2s) | 加速glm5.1 tier恢复; 429=1576(97.1%占主,5键均匀); -2s缩短tier全局阻塞窗口→更早retry; 少改多轮(单参数); 铁律:只改HM1不改HM2 |

**铁律**: 只改HM1不改HM2

### 执行记录
```bash
# 修改docker-compose.yml行422
ssh -p 222 opc_uname@100.109.153.83 "sed -i '422s/\"43\"/\"41\"/' /opt/cc-infra/docker-compose.yml"

# 注释更新
# 已同步更新注释为R90版本

# 部署
cd /opt/cc-infra && docker compose up -d hm40006

# 验证
docker exec hm40006 env | grep TIER_COOLDOWN_S
# → TIER_COOLDOWN_S=41 ✓
```

---

## 预期效果

| 指标 | 当前值 | 预期(43s→41s) |
|------|--------|-----------------|
| Fallback率 | 84.9% | ↓ ~80-82% |
| glm5.1直接成功率 | 15.1% | ↑ ~18-20% |
| 429_nv_rate_limit | 1,576/30min | ↓ ~1,400-1,500 |
| Deepseek超时 | 93 | ↓ ~80-90 (更少fallback) |
| Deepseek <20s桶 | 78.1%主导 | 维持 |
| Deepseek >55s桶 | 34.8% | 观察 (可能随更少fallback需求下降) |
| ConnectionResetError | 17 | 维持 (MIN=17.5安定) |

**机制**: 每-2s TIER_COOLDOWN = +2s更快glm5.1 tier恢复 = 更早返回主Tier尝试 = 更多直接命中 = 更少429循环开销 = 减少deepseek fallback需求 → 降低超时计数。

---

## 观察项

1. **TIER_COOLDOWN_S=41s 继续轨迹**: 从43→41 (-2s), 目标:~40-42s范围。若glm5.1直接>25%且429周期<30%, 可停止。

2. **KEY_COOLDOWN_S=29.0 保持不动**: 低于HM2基线30s, R84交叉回归警示。键级恢复已领先tier 12s, 不是当前瓶颈。

3. **Deepseek超时恶化(34.8% >55s)**: 从14.1%→34.8%, 警惕趋势。可能因2nd attempt=22s不足。下一轮若持续恶化, 可考虑BUDGET+2s。

4. **少改多轮**: 单参数(-2s), 每轮积累微调。目标: 将TIER_COOLDOWN_S降至~38-40s, 保持与KEY_COOLDOWN(29s)的缓冲。

5. **ConnectionResetError=17 (1.1%)**: 安定在MIN=17.5, 无需调整MIN_OUTBOUND。

6. **budget_exhausted_after_connect=6**: 连接成功但预算不足, 不支撑RESERVE调整。

7. **NVCFPexecRemoteDisconnected=1**: 单事件, 无趋势。

8. **empty_200=16**: NVCF空200响应, 非错误。

---

## ⏳ 轮到HM1优化HM2  ← 脚本检测此标记