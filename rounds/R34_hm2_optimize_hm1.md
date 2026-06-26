# R34: HM2优化HM1

**日期**: 2026-06-26
**Actor**: HM2 (opc2_uname)
**Target**: HM1 (100.109.153.83:222)
**前一轮**: R33 (HM2提交, TIER_TIMEOUT_BUDGET_S 90→92, BUDGET轨迹完成)
**策略**: 少改多轮, 降低TIER_COOLDOWN加速deepseek重试恢复

---

## 1. 数据采集

### 1a. 日志模式 (最近50行, error/warn/fail)
- 匹配数: 27 (30分钟窗口)
- 主要流程: glm5.1 TIER-SKIP → deepseek FALLBACK-SUCCESS (典型fallback路径)
- SSLEOFError: 0 (30分钟窗口干净)
- 错误模式: 429_nv_rate_limit均匀分布在glm5.1所有5个key, deepseek NVCFPexecTimeout在30-40s区间

### 1b. 容器环境变量 (运行中值, R33部署后)
| 参数 | 值 | 来源 |
|------|-----|------|
| TIER_TIMEOUT_BUDGET_S | 92 | R33 |
| UPSTREAM_TIMEOUT | 40 | R18 |
| HM_CONNECT_RESERVE_S | 22 | R29 |
| KEY_COOLDOWN_S | 38.0 | R19 |
| MIN_OUTBOUND_INTERVAL_S | 10.0 | R17 |
| TIER_COOLDOWN_S | 90 | R17 |

### 1c. 错误分布 (30分钟窗口, hm_tier_attempts)
| error_type | cnt | avg_elapsed |
|------------|-----|-------------|
| 429_nv_rate_limit | 895 | — |
| NVCFPexecTimeout | 175 | 26,961ms |
| NVCFPexecConnectionResetError | 4 | 903ms |
| NVCFPexecRemoteDisconnected | 1 | 7,577ms |

### 1d. 请求路由统计 (hm_requests, 30分钟)
| 指标 | 值 |
|------|-----|
| 总请求 | 1,318 |
| fallback数 | 1,246 |
| fallback率 | 94.5% |
| 直接成功 | 72 (5.5%) |
| 错误请求 (all_tiers_exhausted) | 18 |
| 非错误fallback平均延迟 | 16,212ms |
| 非fallback平均延迟 | 35,302ms |

### 1e. 层级分布 (hm_tier_attempts)
| tier | cnt |
|------|-----|
| glm5.1_hm_nv | 915 |
| deepseek_hm_nv | 161 |
| kimi_hm_nv | 4 |

### 1f. 0-tier pre-tier连接失败
- **0-tier = 19** (avg duration 113,199ms, 比R32的17增加2)
- RESERVE=22饱和: 连续7轮(R27-R33) 0-tier=17平台 → R34首次突破到19
- 所有0-tier失败均为 key_cycle_429s=0 (预层连接失败, 非key级429)

### 1g. glm5.1 429按key分布 (功能级429, 非per-key)
| key_idx | 429_count | timeout_count |
|---------|-----------|---------------|
| k0 | 181 | 0 |
| k1 | 178 | 1 |
| k2 | 182 | 5 |
| k3 | 178 | 3 |
| k4 | 180 | 2 |

→ 429均匀分布(178-182), 功能级429特性不变

### 1h. Deepseek NVCFPexecTimeout按key分布
| key_idx | timeout_count | 端口 |
|---------|---------------|------|
| k0 | 28 | 7894 |
| k1 | 40 | 7895 |
| k2 | 36 | 7896 |
| k3 | 27 | 7897 |
| k4 | 29 | 7899 |

→ k1(port 7895)最差(40次), 自R24以来稳定模式

### 1i. Deepseek NVCFPexecTimeout elapsed_ms分布 (R33 BUDGET=92)
| bucket | cnt | pct |
|--------|-----|-----|
| <20s | 50 | 31.3% |
| 20-25s | 9 | 5.6% |
| 25-30s | 34 | 21.3% |
| 30-35s | 28 | 17.5% |
| 35-40s | 11 | 6.9% |
| >40s | 28 | 17.5% |

→ 25-30s区间(34次): BUDGET=92 2nd attempt=30s完全覆盖此区间, 但超时数未下降(与R32的34次相同)
→ 30-35s区间(28次): 超出2nd attempt headroom(30s), 是下一优化目标
→ >40s(28次): NVCF基础设施级超时, budget耗尽边界

---

## 2. 诊断

### 根因分析

1. **BUDGET轨迹完成且无效**: R33 BUDGET=92(2nd attempt=30s)未产生deepseek timeout下降(160 vs R32的156, 实际上升4次). 25-30s桶(34次, R32同值)完全被2nd attempt覆盖但超时数不变 — 说明30s headroom已触及有效上限, 继续扩展无意义.

2. **TIER_COOLDOWN=90是当前唯一可调的非饱和参数**: 所有其他参数均已达到饱和/天花板:
   - RESERVE=22完全饱和(7轮0-tier=17保持不变)
   - KEY_COOLDOWN=38接近UPSTREAM_TIMEOUT=40边界
   - MIN_INTERVAL=10已优化
   - BUDGET=92完成扩展路径
   
3. **TIER_COOLDOWN_S降低的直接效果**: 90→88(-2s)减少2s的all-key cooldown. 当glm5.1 5-key全429时, 所有请求在90s内跳过到deepseek. -2s意味着deepseek重试窗口提前2s打开, 增加2s的有效重试时间. 对于deepseek tier hit all-key timeout的情况, 恢复速度提升2.3%.

4. **glm5.1功能级429**: 895次429均匀分布5个key, NVCF函数ID级速率限制, 非key配置可解决.

5. **0-tier从17→19**: 首次突破17平台(±2波动在正常范围内), 但需关注是否持续上升趋势.

### 证据链
- R33 BUDGET=92 → 2nd attempt=30s → 25-30s桶34次(未下降 vs R32)
- R32→R33 deepseek timeout 156→160 (+2.6%, 反向趋势)
- BUDGET=92轨迹完成 → 需转向新优化目标
- 所有参数除TIER_COOLDOWN外均已饱和/天花板

---

## 3. 优化变更

| 参数 | 变更前 | 变更后 | 理由 |
|------|--------|--------|------|
| TIER_COOLDOWN_S | 90 | 88 | -2s tier cooldown: 加速deepseek tier all-key timeout后的重试恢复; BUDGET=92轨迹完成(2nd attempt=30s饱和); 少改多轮(单参数变更); 2.3%更快tier恢复窗口; 让deepseek在30-35s timeout区间有更多retry机会 |

**不变参数**: UPSTREAM_TIMEOUT=40, HM_CONNECT_RESERVE_S=22, KEY_COOLDOWN_S=38, MIN_OUTBOUND_INTERVAL_S=10, TIER_TIMEOUT_BUDGET_S=92

**变更策略转变说明**: R29-R33连续5轮TIER_BUDGET扩展(82→84→86→88→90→92)完成2nd attempt headroom从22s到30s的完整轨迹. 现在BUDGET轨迹完成且未产生deepseek timeout下降, 转向TIER_COOLDOWN的微调路径. 这是HM优化周期的自然切换点 — 从单一参数线性扩展到多参数并行微调.

---

## 4. 执行记录

### 4a. 备份
```bash
ssh opc_uname@100.109.153.83 'cp /opt/cc-infra/docker-compose.yml /opt/cc-infra/docker-compose.yml.bak.R34'
```

### 4b. 配置变更 (compose line 422)
```bash
# Value change: 90→88
ssh opc_uname@100.109.153.83 'cd /opt/cc-infra && sed -i "422s/\"90\"/\"88\"/" docker-compose.yml'

# Comment update: R17→R34
ssh opc_uname@100.109.153.83 "cd /opt/cc-infra && sed -i '422s/# R17: HM2优化.*$/# R34: HM2优化 — 90→88: -2s tier cooldown; 更快恢复deepseek tier重试窗口; BUDGET=92轨迹完成(2nd attempt=30s饱和); 少改多轮(单参数变更); 铁律:只改HM1不改HM2/' docker-compose.yml"
```

### 4c. 部署
```bash
cd /opt/cc-infra && docker compose up -d hm40006
```
→ Container hm40006 Recreated, Started

### 4d. 验证
```
TIER_COOLDOWN_S=88          ✓
TIER_TIMEOUT_BUDGET_S=92    ✓ (不变)
HM_CONNECT_RESERVE_S=22      ✓ (不变)
KEY_COOLDOWN_S=38.0         ✓ (不变)
MIN_OUTBOUND_INTERVAL_S=10.0 ✓ (不变)
UPSTREAM_TIMEOUT=40         ✓ (不变)
hm40006 Up (healthy)        ✓
```

---

## 5. 预期效果

| 指标 | R33值 | R34预期 | 依据 |
|------|-------|---------|------|
| TIER_COOLDOWN | 90s | 88s | -2.2% cooldown → +2.3%更快恢复 |
| deepseek 25-30s超时 | 34 | 32-34 | TIER_COOLDOWN不直接影响per-attempt timeout, 但faster recovery可能减少all-key cooldown期间的pending requests |
| 0-tier pre-tier | 17→19 | 17-19 | TIER_COOLDOWN不改变pre-tier连接, 预计稳定在17-19 |
| fallback率 | 94.5% | 93-95% | 微调影响小, fallback率稳定 |
| >40s budget耗尽 | 28 | 28 | NVCF基础设施级, 不受TIER_COOLDOWN影响 |

**效能评估**: 这是一个保守的-2s微调. 预期效果微弱(可能不影响任何DB-level指标), 但这是从BUDGET扩展到TIER_COOLDOWN的自然过渡. 后续几轮需持续评估是否为正确方向, 若3轮内无改善则切换到其他参数.

---

## 6. 观察项与风险

1. **0-tier 17→19首次突破**: 虽然±2在统计波动内, 但需关注R35是否继续上升. 若连续2轮0-tier>17则需REVISIT RESERVE决策(当前饱和假设可能需修正).

2. **BUDGET扩展完成后的TIER_COOLDOWN路径**: 这是新的优化方向. 若TIER_COOLDOWN 88在3轮内无改善, 考虑以下替代方案:
   - 降低到86-84(更激进的cooldown缩减)
   - 或转而调整MIN_OUTBOUND_INTERVAL_S(10.0→10.5, 更慢key rotation减少429碰撞)
   - 或调查mihomo proxy port 7895的健康状态(k1持续40次timeout)

3. **k1(port 7895)持续最差**: 40次vs平均30次(33%偏高), 自R24稳定. 若k1偏差>50%则需调查mihomo proxy端口配置

4. **TIER_COOLDOWN_S=88的下界**: 当前无明确下界, 但TIER_COOLDOWN不能无限降低. 每次-2s需评估是否带来实际改进

5. **R34是BUDGET轨迹后的第1个非BUDGET轮次**: 预期需3-5轮才能在TIER_COOLDOWN路径上看到显著改进. 这是从单参数线性优化到多参数并行微调的自然过渡点

6. **铁律确认**: 只改HM1 docker-compose.yml(TIER_COOLDOWN_S), 不改HM2本地任何配置

---

## ⏳ 轮到HM1优化HM2  ← 脚本检测此标记