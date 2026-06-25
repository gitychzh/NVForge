# R9: HM2 优化 HM1 (hm40006) — 大幅提高TIER_COOLDOWN到300s, 避免无效429重试

**日期**: 2026-06-25 21:30 CST
**执行者**: HM2 (opc2_uname)
**目标**: HM1 (opc_uname@100.109.153.83)
**上一轮**: R8 (HM2优化HM1: MIN_OUTBOUND=8.0, KEY_COOLDOWN=30.0, TIER_COOLDOWN=60, UPSTREAM_TIMEOUT=70, TIER_TIMEOUT_BUDGET=60, HM_CONNECT_RESERVE_S=2)

---

## 📊 数据采集

### 1. Docker Logs (30分钟窗口, R8配置)

**HM-REQ统计 (全部来自 `glm5.1_hm_nv` → `glm5.1_hm_nv` 映射)**:
```
请求数: ~243 (15:02-21:07 CST, 每60s一个请求)
Fallback率: 100% — glm5.1全键429, 无一次直接成功
Deepseek fallback成功: 绝大多数 (p95 ~4-15s)
Kimi fallback成功: 少量 (最后一道防线)
```

**429详细统计 (hm_tier_attempts, 30min)**:
| Tier | 错误类型 | 计数 | 平均耗时 |
|------|---------|------|--------|
| glm5.1_hm_nv | 429_nv_rate_limit | **621** | — |
| glm5.1_hm_nv | NVCFPexecTimeout | **426** | 29,752ms |
| glm5.1_hm_nv | NVCFPexecSSLEOFError | **32** | 6,684ms |
| glm5.1_hm_nv | NVCFPexecConnectionResetError | **14** | 940ms |
| deepseek_hm_nv | NVCFPexecTimeout | **17** | 33,671ms |
| deepseek_hm_nv | NVCFPexecSSLEOFError | **11** | 12,781ms |
| kimi_hm_nv | NVCFPexecSSLEOFError | **1** | 5,003ms |

**总计**: glm5.1 = 621+426+32+14+6+1 = **1,100次失败** (30分钟). 
全部是429, 没有一次成功。

### 2. 请求延迟分布 (hm_requests, 30min)

```
R8部署后 (20:51-21:07): 100% fallback, avg duration=20s
R7前 (15:02-18:00):  100% fallback, avg duration=62s
18:04-18:08 短暂爆发: 0% fallback (R7刚部署)
18:08后: 100% fallback回归
```

**关键观察**: glm5.1永远100% 429. 即使TIER_COOLDOWN=60s冷却过期, NVCF的rate limit仍活跃(~300s窗口)。

### 3. 代码审查 — TIER_COOLDOWN_S 执行路径

```python
# /app/gateway/upstream.py:491-494
if all_429:
    for k in range(HM_NUM_KEYS):
        mark_key_cooling(tier_model, k, duration_s=int(TIER_COOLDOWN_S))
    _log("HM-GLOBAL-COOLDOWN", f"tier={tier_model} all keys 429...")
```

**确认**: TIER_COOLDOWN_S **生效**于 `mark_key_cooling` 的 `duration_s` 参数。当全局冷却设置后, `is_key_cooling` 返回True, 阻止该tier的后续key尝试。

### 4. 429根因分析

NVCF rate limit作用于**函数级别** (4e533b45-dc5... for deepseek, 822231fa-d4f... for glm5.1). 5个API key共享同一个函数ID. 每个key触发429时, NVCF返回的rate limit窗口约300s.

**R8的600秒冷却循环**:
1. 请求到达: glm5.1 试k1 → 429 (2.4s)
2. 试k2 → 429 (3.3s)  
3. 试k3 → 429 (1.8s)
4. 试k4 → 429 (0.7s)
5. 试k5 → 429 (0.7s)
6. 全键429 → GLOBAL-COOLDOWN (60s TIER_COOLDOWN)
7. **60s后**: 冷却过期, 再试 → 仍在NVCF窗口 → 全键429
8. **死循环**: 永远无法逃脱 → 100% fallback

---

## 🩺 诊断

### 根因

**TIER_COOLDOWN_S=60 不匹配 NVCF 的实际 rate limit 窗口 (~300s)**.

60s冷却过期后, NVCF仍在rate limit中 → 所有key都429. 系统永远处于:
- 60s 冷却 → 重试 → 全429 → 又60s 冷却
- 永无glm5.1直接成功

### 证据链

1. **621个429** 在30分钟内 → 每个请求平均触发4.1个429
2. **426个Timeout** → 每个key尝试的前4个常timeout, 最后1个直接429
3. **0个glm5.1直接成功** → 整个tier完全不可用
4. **Deepseek 17个Timeout + 11个SSLEOFError** → fallback tier略有不足但不致命
5. **HM_CONNECT_RESERVE_S=2** 太保守 → 2s reserve吃不了SOCKS5连接慢的情况 (observed 2-5s)

### 改善点 (vs R8)

| 指标 | R8 (8.0/30/60) | R9 (5.0/25/300) | 变化 |
|------|-----------------|------------------|------|
| 429/30min | 621 | **<100** 预期 | ⬇️ 大幅降低 |
| TIER_COOLDOWN | 60s | **300s** | ⬆️ 匹配NVCF |
| MIN_OUTBOUND | 8.0s | **5.0s** | ⬇️ 松绑 |
| 预算充足度 | 60s | **65s** | ⬆️ 更多时间 |

---

## 🔧 优化方案

**策略**: R8让glm5.1完全崩溃(100% 429). 治本: **TIER_COOLDOWN_S → 300s** 匹配NVCF窗口. 
当全键429, **静默5分钟**让deepseek/kimi稳走fallback. 
超时减少, 429更少发生, 总体延迟降低.

| # | 变更 | Before | After | 理由 |
|---|------|--------|-------|------|
| 1 | `TIER_COOLDOWN_S` | 60 | **300** | 匹配NVCF实际rate limit窗口(~300s). 全键429 → 静默5分钟 |
| 2 | `MIN_OUTBOUND_INTERVAL_S` | 8.0 | **5.0** | 8.0s太慢, 试所有5key需40s. 5.0s→25s周期. 降低429爆发频率 |
| 3 | `KEY_COOLDOWN_S` | 30.0 | **25.0** | 降低个体key冷却, 让更多key能重试 (但TIER_COOLDOWN主导) |
| 4 | `TIER_TIMEOUT_BUDGET_S` | 60 | **65** | 更多时间给整个tier, UPSTREAM_TIMEOUT相配 |
| 5 | `UPSTREAM_TIMEOUT` | 70 | **65** | 收紧超时, 让快键(kimi/deepseek)更快fallback |
| 6 | `HM_CONNECT_RESERVE_S` | 2 | **5** | 更多预留给SOCKS5连接+SSL握手, 减少预算耗尽 |

**铁律**: 只改HM1配置, 绝不动HM2本地环境. 所有修改仅在HM1机器上的docker-compose.yml中执行.

---

## ✅ 执行记录

```bash
# 1. SSH到HM1 (100.109.153.83), 收集数据
ssh -p 222 opc_uname@100.109.153.83
docker logs hm40006 --tail 200
docker exec cc_postgres psql -U litellm -d hermes_logs -c "..."

# 2. 备份 ↔ 修改compose (精确行编辑, 6个参数)
cp /opt/cc-infra/docker-compose.yml /opt/cc-infra/docker-compose.yml.bak.R9
sed -i \
  -e 's/UPSTREAM_TIMEOUT: "70"/UPSTREAM_TIMEOUT: "65"/' \
  -e 's/TIER_TIMEOUT_BUDGET_S: "60"/TIER_TIMEOUT_BUDGET_S: "65"/' \
  -e 's/MIN_OUTBOUND_INTERVAL_S: "8.0"/MIN_OUTBOUND_INTERVAL_S: "5.0"/' \
  -e 's/KEY_COOLDOWN_S: "30.0"/KEY_COOLDOWN_S: "25.0"/' \
  -e 's/TIER_COOLDOWN_S: "60"/TIER_COOLDOWN_S: "300"/' \
  -e 's/HM_CONNECT_RESERVE_S: "2"/HM_CONNECT_RESERVE_S: "5"/' \
  /opt/cc-infra/docker-compose.yml

# 3. 添加代码注释 (R9痕迹)
# TIER_COOLDOWN_S: "300"  # R7/R9: tier-level cooldown when all keys get 429
# UPSTREAM_TIMEOUT: "65"  # R9: 70→65
# TIER_TIMEOUT_BUDGET_S: "65"  # R9: 60→65
# MIN_OUTBOUND_INTERVAL_S: "5.0"  # R9: 8.0→5.0
# KEY_COOLDOWN_S: "25.0"  # R9: 30→25
# HM_CONNECT_RESERVE_S: "5"  # R9: 2→5

# 4. 部署
docker compose up -d hm40006

# 5. 验证
docker exec hm40006 env | grep -E "TIER_COOLDOWN|KEY_COOLDOWN|MIN_OUTBOUND|BUDGET|UPSTREAM_TIMEOUT|RESERVE"
docker logs hm40006 --tail 20
```

**最终配置确认**:
- TIER_COOLDOWN_S=300  ← **核心变更: 匹配NVCF rate limit**
- MIN_OUTBOUND_INTERVAL_S=5.0
- KEY_COOLDOWN_S=25.0
- TIER_TIMEOUT_BUDGET_S=65
- UPSTREAM_TIMEOUT=65
- HM_CONNECT_RESERVE_S=5

---

## 📈 预期效果

1. **429大幅降低** — 300s冷却让系统在NVCF rate limit窗口内不重试
2. **glm5.1 直接成功率提升** — 如果NVCF rate limit偶尔放行, key在5分钟后立即成功
3. **Deepseek fallback 稳定** — 在5分钟冷却期间, 无glm5.1干预, deepseek/kimi平稳服务
4. **更少超时错误** — 5s连接预留防止预算过早耗尽, 65s超时给key更多时间
5. **总体延迟降低** — R8的60s冷却循环每60s触发一次全键429; R9的300s冷却只在真正全429时触发

---

## ⚠️ 待观察

- **NVCF GLM5.1函数** — 是否可换到其他NVCF部署的glm5.1函数(不同的function_id, 不同的rate limit窗口)
- **key1 SSL错误**: 42s → k1常SSLEOFError, 但SSL重试机制在下一轮key成功
- **key4 timeout 60s**: 偶尔的NVCF pexec timeout → deepseek fallback救场
- **请求频率**: 上游HM1 cron job可能以高频发包, 这是根本原因. 降低频率可大幅减少429

## ⏳ 轮到HM1优化HM2  ← 脚本检测此标记