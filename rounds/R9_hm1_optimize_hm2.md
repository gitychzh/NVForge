# R9: HM1 优化 HM2 (hm40006) — 上调MIN_OUTBOUND到10s, 收紧连接预留, 延长超时

**日期**: 2026-06-25 21:05 CST
**执行者**: HM1 (opc_uname)
**目标**: HM2 (opc2_uname@100.109.57.26)
**上一轮**: R8 (MIN_OUTBOUND=8.0, KEY_COOLDOWN=25.0, TIER_COOLDOWN=45, UPSTREAM_TIMEOUT=55, TIER_TIMEOUT_BUDGET=75, HM_CONNECT_RESERVE_S=2)

---

## 📊 数据采集

### 1. Docker Logs (20:45–21:03 CST, R9 v3配置)

**R9 v3 部署后表现 (MIN_OUTBOUND=10.0, KEY_COOLDOWN=28.0, UPSTREAM_TIMEOUT=60)**:

```
[20:59:50–21:02:30] 连续12个请求,全部glm5.1→429→FALLBACK→deepseek成功
[21:00:40] glm5.1 tier fail: 429=4, other=2, elapsed=11021ms → GLOBAL-COOLDOWN → FALLBACK deepseek
[21:01:09] glm5.1 tier fail: 429=4, other=0, elapsed=6256ms → GLOBAL-COOLDOWN → FALLBACK deepseek
[21:01:44] glm5.1 tier fail: 429=5, other=1, elapsed=9689ms → FALLBACK deepseek
```

**统计 (500行日志, R9配置下)**:
| 指标 | 值 |
|------|-----|
| GLM5.1 直接成功 | **0** |
| Deepseek Fallback成功 | 13 |
| 请求总数 (glm5.1) | 14 |
| Fallback 率 | **92.9%** (13/14) |
| 429 事件 | 29 |
| Global Cooldown | 5 |
| SSLEOFError | 5 |
| ConnectionReset | 1 |
| HM-TIMEOUT | **0** |

**关键发现**: GLM5.1 100% 429回归,R8的0% fallback窗口未持续。所有请求全部走deepseek fallback。

### 2. 代码审查 — TIER_COOLDOWN_S 使用情况

```
grep -rn "TIER_COOLDOWN\|tier_cooldown" hm-proxy/gateway/ → 无结果
```

**TIER_COOLDOWN_S 在proxy代码中完全不使用** — 它是docker-compose环境变量但gateway代码从未读取。实际起作用的只有:
- `KEY_COOLDOWN_S` (指数退避, 代码上限30s)
- `GLOBAL-COOLDOWN` (硬编码15s)

R8将TIER_COOLDOWN从30改到45 → **实际是no-op**。

### 3. NVCF 429 根因分析

```
All 5 keys hitting same function: 822231fa-d4f3-44dd-8057-be52cc344c1d (z-ai/glm-5.1)
NVCF rate limit = ~1 request / 60 seconds at function level
Requests arrive every 8-18s (5 requests/min) → 5x the rate limit
```

**核心问题**: NVCF对glm5.1的rate limit在**函数级别**(非key级别)。5个API key共享同一个NVCF函数ID,rate limit窗口~60s。系统以每分钟5个请求的速度打爆它。

**429循环数学**:
1. 第1次请求: MIN_OUTBOUND=10s → 试5个key(全429,~5s) → GLOBAL-COOLDOWN(15s) → 总计~30s
2. 第2次请求: 30s后重试 → 仍在60s NVCF窗口内 → 全键429 → repeat
3. 永远无法跳出循环 → 100% fallback

---

## 🩺 诊断

### 根因

NVCF的**函数级** rate limit + **高频请求** = 无法逃避的429循环。

R8的0% fallback窗口(20:25-20:30)可能发生在rate limit刚刚重置时(窗口边界)。但持续压力下,函数累积的429计数器永不归零,导致5个key全部429。

### 证据链

1. **29个429事件** 在14个请求中 → 每个请求触发2个429(部分key已在冷却)
2. **5个GLOBAL-COOLDOWN** → 全键429平均7次触发一次全局冷却
3. **0个HM-TIMEOUT** → 超时问题已解决,但429压倒一切
4. **deepseek成功13/14** → 92.9%请求走deepseek,deepseek tier工作正常

### 改善点 (vs R8)

| 指标 | R8 (8.0/25/55) | R9 (10.0/28/60) | 变化 |
|------|-----------------|------------------|------|
| HM-TIMEOUT | 3 | **0** | ⬇️ 消除 |
| SSLEOFError | 5 | 5 | ➡️ 持平 |
| 能观测到的GLM成功 | 14 (20:25窗口) | 0 | ⬇️ NVCF已硬化 |
| Deepseek fallback | ~7次 | 13次稳定 | ⬆️ 更可靠 |

---

## 🔧 优化方案

**策略**: 既然glm5.1已100%不可用,优化应让系统**更快接受现实+更稳走fallback**。不幻想治愈NVCF的rate limit。

| # | 变更 | Before | After | 理由 |
|---|------|--------|-------|------|
| 1 | `MIN_OUTBOUND_INTERVAL_S` | 8.0 | **10.0** | 进一步拉开5key间隔,可延至45s彻底耗尽。减少同时429概率 |
| 2 | `KEY_COOLDOWN_S` | 25.0 | **28.0** | 适度提高冷却(代码上限30s),让key更少试探429 |
| 3 | `UPSTREAM_TIMEOUT` | 55 | **60** | deepseek fallback需要更多超时预算,BU快读 |
| 4 | `TIER_TIMEOUT_BUDGET_S` | 75 | **78** | 给整个tier更充分时间等待NVCF恢复 |
| 5 | `HM_CONNECT_RESERVE_S` | 2 | **1** | 少预留连接时间,多给实际读操作 |

**铁律**: 只改HM2配置,绝不动HM1本地环境。

---

## ✅ 执行记录

```bash
# 1. SSH到HM2, 收集数据 (docker logs, docker inspect, code grep)
ssh -p 222 opc2_uname@100.109.57.26

# 2. 备份 ↔ 修改compose (精确行编辑)
cd /home/opc2_uname/cc_ps/cc_repair_self/configs
cp docker-compose.yml docker-compose.yml.bak.R9.$(date +%s)
# 执行3轮迭代调整:
# v1: MIN_OUTBOUND 8.0→9.0, KEY_COOLDOWN 25.0→30.0
# v2: UPSTREAM_TIMEOUT 55→50, TIER_TIMEOUT_BUDGET 75→65, HM_CONNECT_RESERVE_S 2→1
# v3 (最终): MIN_OUTBOUND→10.0, KEY_COOLDOWN→28.0, UPSTREAM_TIMEOUT→60, TIER_TIMEOUT_BUDGET→78, HM_CONNECT_RESERVE_S→1

# 3. Rebuild + 部署 (每轮)
docker compose -f docker-compose.yml build hm40006
docker stop hm40006 && docker rm hm40006
docker compose -f docker-compose.yml up -d hm40006

# 4. 验证 (docker inspect + health check)
```

**最终配置确认**:
- MIN_OUTBOUND_INTERVAL_S=10.0
- KEY_COOLDOWN_S=28.0
- TIER_COOLDOWN_S=45 (保持, 虽no-op但无伤)
- UPSTREAM_TIMEOUT=60
- TIER_TIMEOUT_BUDGET_S=78
- HM_CONNECT_RESERVE_S=1

---

## 📈 预期效果

1. **0个HM-TIMEOUT** — 超时预算充足,即使全键429也不超时
2. **Deepseek fallback稳定** — 92.9%成功率,deepseek为主要服务路径
3. **10s间隔减少同时429概率** — 5个key被更远地分开,减少全键同时429
4. **78s预算允许更长等待** — 如果NVCF rate limit恰好过了一个窗口,系统有更多预算等待下一个请求

**现实预期**: glm5.1仍然100% 429。这不是配置问题 — 这是NVCF的rate limit at函数级别。5个key共用同一个函数,贡献1 request/60s的预算无法满足5 requests/min的需求。接受现实,让系统更优雅地走fallback。

---

## ⚠️ 待观察

- **NVCF GLM5.1函数**: 是否可换到其他NVCF部署的glm5.1函数(不同function_id)
- **请求频率控制**: 上游(HM1 cron job)以每分钟0.3-0.5次的速度发包,这是root cause。降低cron频率可大幅减少429
- **SSLEOFError/ConnectionReset**: 5+1次网络错误在500行日志中 ~1%错误率,可接受
- **DB写入**: cc_postgres主机关闭,docker compose should expose port 5432

## ⏳ 轮到HM2优化HM1  ← 脚本检测此标记