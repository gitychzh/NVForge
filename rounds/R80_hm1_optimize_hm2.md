# R80: HM1→HM2 — TIER_TIMEOUT_BUDGET_S 115→120 (+5s)

**时间**: 2026-06-27 04:50 UTC  
**执行者**: HM1 (opc_uname)  
**方向**: HM1优化HM2  
**上一轮**: R79 (HM2→HM1, MIN_OUTBOUND_INTERVAL_S 15.5→17.5, TIER_COOLDOWN_S 68→55)

## 📊 采集数据 (HM2 hm40006, 实时窗口 04:35-04:43 UTC)

### 实时日志模式 (docker logs --tail 200)
```
模式1: glm5.1全部429循环 (90%+ 请求)
[HM-COOLDOWN] tier=glm5.1_hm_nv k* marked cooling after 429
[HM-CYCLE] tier=glm5.1_hm_nv k* → 429 (429_nv_rate_limit), cycling
[HM-TIER-FAIL] all 5 keys failed: 429=5, elapsed=4160-25925ms
[HM-GLOBAL-COOLDOWN] all keys 429 → Marking all cooling 45s
[HM-FALLBACK] → deepseek_hm_nv

模式2: deepseek fallback成功 (唯一可用tier)
[HM-FALLBACK-SUCCESS] Success on fallback tier deepseek_hm_nv
[HM-TIER] Starting tier=deepseek_hm_nv model=deepseek-ai/deepseek-v4-pro func=4e533b45-dc5...

模式3: 偶发glm5.1直通 (10% 窗口)
[HM-SUCCESS] tier=glm5.1_hm_nv k* succeeded (1次/10req, 20,397ms, 1次429重试)
```

### 关键发现
| 指标 | 值 |
|------|-----|
| glm5.1直通率 | **~10%** (1/10 直接hit, 20,397ms) |
| deepseek fallback率 | **~90%** (9/10 请求fallback) |
| glm5.1每轮耗时 | 4-26s (5 key全429) |
| deepseek avg延迟 | ~25.4s (range 14s-68s) |
| 68s极端延迟 | 1次 (04:39:23, 2nd key budget耗尽) |

## 🔧 诊断分析

### 核心问题
1. **glm5.1仍是主入口但90% 429** — 仅1/10直通成功, NVCF函数级429持续
2. **deepseek是实际工作tier** — 90%请求最终走deepseek fallback
3. **2nd key budget不足** — 当前预算: 115-(55+15+15)=30s, deepseek avg=25.4s但max=68s
4. **68s极端延迟来自budget截断** — 2nd key在30s时被截断导致3rd key(低保10s)

### 预算计算
- UPSTREAM=55, BUDGET=115, RESERVE=15
- 1st key: min(55, 115-15=100)=55s → 剩余=115-55=60
- 2nd key: max(10, min(55, 60-15-15=30))=30s — 之前25s
- 如果2nd key也超时: 剩余=60-30=30 → 3rd key: max(10, min(55, 30-15-15=0))=10s

### 优化选择
**TIER_TIMEOUT_BUDGET_S: 115 → 120 (+5s)**

**机制**:
- 总预算从115s增至120s, 2nd key budget从30s→35s (+5s)
- 1st key (glm5.1/55s) 行为不变
- 2nd key deepseek更加接近avg 25.4s, 减少max 68s截断
- 不影响主tier (glm5.1) — 主tier仍是函数级429, 无法修复
- +5s预算直接改善deepseek层2nd key的完成窗口

**预算计算 (R80后)**:
- UPSTREAM=55, BUDGET=120, RESERVE=15
- 1st key: min(55, 120-15=105)=55s → 剩余=120-55=65
- 2nd key: max(10, min(55, 65-15-15=35))=35s — 比之前的30s +5s
- 如果2nd key也超时: 剩余=65-35=30 → 3rd key: max(10, min(55, 30-15-15=0))=10s

## ✅ 执行记录

### SSH操作 (HM2)
```bash
# 备份
cp /opt/cc-infra/docker-compose.yml docker-compose.yml.bak.R80

# 改值: 477行 TIER_TIMEOUT_BUDGET_S 115→120
sed -i '477s/"115"/"120"/' /opt/cc-infra/docker-compose.yml

# 重建+部署
cd /opt/cc-infra && docker compose up -d hm40006
```

### 部署验证
- ✅ `docker compose up -d hm40006` — Container recreated + started
- ✅ `docker ps` → hm40006 Up 27s (healthy)
- ✅ `docker exec hm40006 env` → **TIER_TIMEOUT_BUDGET_S=120**
- ✅ mihomo未触碰 (铁律)
- ✅ 所有其他参数未变

### 配置确认
| 参数 | Before | After | Verified |
|------|--------|-------|----------|
| TIER_TIMEOUT_BUDGET_S | 115 | **120** | ✅ |
| KEY_COOLDOWN_S | 33.0 | 33.0 | ✅ |
| TIER_COOLDOWN_S | 40 | 40 | ✅ |
| UPSTREAM_TIMEOUT | 55 | 55 | ✅ |
| MIN_OUTBOUND_INTERVAL_S | 19.0 | 19.0 | ✅ |
| HM_CONNECT_RESERVE_S | 15 | 15 | ✅ |

## 📈 预期影响

| 指标 | 当前 | 预期 | 评级 |
|------|------|------|------|
| glm5.1直通率 | ~10% | 不变 (NV函数级429) | ⚠️ |
| deepseek fallback率 | ~90% | ~90% (稳定) | ✅ |
| deepseek avg TTFB | ~25.4s | ↓ → ~23s (2nd key +5s) | ✅ |
| deepseek max延迟 | 68s | ↓ → ~55s (减少截断) | ✅ |
| 0-tier failures | 0 | 0 (保持) | ✅ |
| 429_nv_rate_limit | 持续 | 稳定 (函数级) | ✅ |

## 🔒 铁律确认
- ✅ 只改HM2配置 (docker-compose.yml, TIER_TIMEOUT_BUDGET_S), 不触HM1本地
- ✅ mihomo服务未停/未重启/未kill
- ✅ 少改多轮 (单参数 +5s)
- ✅ 基于实时数据: 90% fallback, deepseek avg 25.4s, max 68s, 2nd key budget 30s→35s
- ✅ 容器健康验证通过

## ⏳ 轮到HM2优化HM1