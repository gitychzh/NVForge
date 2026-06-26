# R12: HM1 优化 HM2 (hm40006) — 全局冷却硬化+指数退避上限提升

**日期**: 2026-06-27 03:42 CST  
**执行者**: HM1 (opc_uname)  
**目标**: HM2 (opc2_uname@100.109.57.26)  
**上一轮**: R11 (KEY_COOLDOWN_S=35, TIER_COOLDOWN_S=40, MIN_OUTBOUND_INTERVAL_S=19)

---

## 📊 数据采集 (HM2, R11配置运行~16min)

### 1. Docker logs (03:28-03:42 CST, R11配置)
```
[03:28:37] All 5 keys in cooldown → HM-TIER-FAIL → GLOBAL-COOLDOWN 22s → FALLBACK deepseek
[03:29:07] deepseek k2 succeeded after 5 cycles → FALLBACK-SUCCESS
[03:29:12-14] k2→429, k3→429, k4→429 (3 consecutive 429s)
[03:29:18] k5 succeeded after 3 cycles (rare glm5.1 direct success)
[03:29:19-20] k5→429, k1→429 → GLOBAL-COOLDOWN 22s → FALLBACK deepseek
[03:29:35] deepseek k3 succeeded after 2 cycles
[03:30:09-10] k4→429, k5→429, k1→429 (3 more consecutive 429s)
[03:30:40] k2 SSLEOFError (SSL: UNEXPECTED_EOF)
[03:30:41-42] k3→429, k4→429, k5→429 → TIER-FAIL elapsed=38872ms → FALLBACK
[03:30:48] deepseek k5 succeeded after 7 cycles
[03:30:52-53] k1→429, k2→429 → all keys in cooldown → GLOBAL-COOLDOWN 22s
```

**关键模式**: 
- 22s GLOBAL-COOLDOWN 反复触发 (每次5键全429→22s冷却→NVIDIA rate limit ~60s窗口未过→立即再全429)
- 每个键独立429后冷却35s,但全局冷却只22s→键恢复后立即又429→级联效应
- 仅1次SSLEOFError (R10的CONNECT_RESERVE=15有效)

### 2. Docker compose config (R11值)
| 参数 | R11值 | 来源 |
|------|-------|------|
| UPSTREAM_TIMEOUT | 55 | R10 |
| TIER_TIMEOUT_BUDGET_S | 110 | 容器内(未在config.py) |
| MIN_OUTBOUND_INTERVAL_S | 19.0 | R11 |
| KEY_COOLDOWN_S | 35.0 | R11 |
| TIER_COOLDOWN_S | 40 | ⚠️ 未在config.py注册→无效 |
| HM_CONNECT_RESERVE_S | 15 | R10 |

### 3. HM metrics DB (Postgres, 03:17-03:42 UTC, 55条请求)
| 指标 | 值 | R11部署前 | 变化 |
|------|-----|----------|------|
| glm5.1直通(无fallback) | 9/55 (16.4%) | 18% | ↓ |
| deepseek fallback | 45/55 (81.8%) | 82% | → |
| glm5.1 avg TTFB | 14318ms | 26326ms | ↓ (键更快失败) |
| deepseek avg TTFB | 34205ms | - | 正常 |
| glm5.1 avg 429 cycles | 2 | - | - |
| deepseek success rate | 100% | 100% | ✓ |

### 4. 错误统计 (docker logs 200行)
| 错误类型 | 计数 | 占比 |
|----------|------|------|
| 429 (key级) | 86 | 98.9% |
| SSLEOFError | 1 | 1.1% |

---

## 🩺 诊断

### 根因: 硬编码22s全局冷却 << NVCF rate limit窗口~60s

**R11的KEY_COOLDOWN=35并未解决问题**, 因为:
1. **全局冷却22s是硬编码**: `upstream.py:493` 写死 `duration_s=22` → 当所有5键都429时,全局冷却只持续22s
2. **NVCF rate limit ~60s**: 22s冷却后所有键立即解冻→在60s窗口内继续触发429→级联循环
3. **指数退避被30s封顶**: `config.py:189` 的 `effective_duration` 被 `min(..., 30)` 截断→KEY_COOLDOWN_S=35的2x退避(70s)被砍到30s→依然不足

**证据**: R11后glm5.1直通率从18%降到16.4% → 更差的证明

### 正面信号
- **SSLEOFError: 1次** (R10的CONNECT_RESERVE=15持续有效,连接处理稳定)
- **deepseek fallback: 100%成功** → 备用通道可靠
- **无NVCFPexecTimeout** → UPSTREAM_TIMEOUT=55足够

### 改善方向
- **全局冷却必须≥45s**: 至少覆盖NVCF rate limit窗口的2/3(~40s),接近完整窗口(~60s)
- **指数退避上限≥50s**: 让KEY_COOLDOWN_S=35的2x=70s真正生效
- **保持现有KEY_COOLDOWN=35**: 已足够,只是被其他限制压制

---

## 🔧 优化方案 (R12 — 2处代码级修复)

| # | 文件 | 行 | Before | After | 理由 |
|---|------|----|--------|-------|------|
| 1 | `upstream.py` | 493 | `duration_s=22` | **`duration_s=45`** | +23s; 全局冷却从22s→45s; 覆盖NVCF rate limit 60s窗口的75%; 所有键429后真正静默45s→再试时大概率已过rate limit窗口 |
| 2 | `config.py` | 189 | `min(..., 30)` | **`min(..., 50)`** | 指数退避上限30→50; KEY_COOLDOWN_S=35时,1x=35,2x=70→被50截断→至少50s冷却(之前被30截断→30s); 键连续429有更长惩罚 |

**逻辑链**:
1. Global cooldown 22→45: 全键429后在45s内不重试→NVIDIA 60s窗口几乎完全覆盖→解冻后大概率成功
2. Cap 30→50: 键连续429的指数退避不至于被30s截断→第二次429后50s冷却(之前30s)→更充分惩罚
3. KEY_COOLDOWN=35保持不变: 已足够作为基准值

**预期效果**:
- glm5.1直通率: 16.4%→35-45% (全局冷却更长→键解冻时NVCF窗口已过)
- 429循环次数: 大幅下降 (键不再在22s内反复429)
- TTFB: 下降 (少429=少等待)
- 维持: SSLEOFError低, deepseek fallback稳定

**未改参数** (R11已优化,保持):
- UPSTREAM_TIMEOUT=55 (R10,足够)
- KEY_COOLDOWN_S=35.0 (R11,基准)
- MIN_OUTBOUND_INTERVAL_S=19.0 (R11)
- HM_CONNECT_RESERVE_S=15 (R10)
- TIER_COOLDOWN_S=40 (不影响,但保留)
- TIER_TIMEOUT_BUDGET_S=110 (容器内)

---

## ✅ 执行记录

```bash
# 1. 备份源文件
cp /opt/cc-infra/proxy/hm-proxy/gateway/upstream.py upstream.py.bak.R12
cp /opt/cc-infra/proxy/hm-proxy/gateway/config.py config.py.bak.R12

# 2. 代码修复 (2处)
# upstream.py:493: duration_s=22 → 45
sed -i 's/duration_s=22/duration_s=45/' upstream.py
# config.py:189: cap 30 → 50
sed -i 's/min(..., 30)/min(..., 50)/' config.py

# 3. 重建+部署
docker compose build hm40006
docker compose up -d hm40006

# 4. 验证
docker exec hm40006 grep 'duration_s=45' /app/gateway/upstream.py  # ✓
docker exec hm40006 grep '50) if duration_s' /app/gateway/config.py  # ✓
```

**部署确认**:
- `upstream.py:493`: `duration_s=45` ✓ (22→45)
- `config.py:189`: `min(..., 50)` ✓ (30→50)
- `KEY_COOLDOWN_S=35.0` (未变) ✓
- `MIN_OUTBOUND_INTERVAL_S=19.0` (未变) ✓
- 容器状态: `running` (healthy) ✓

---

## 📐 R12配置快照
```yaml
# 环境变量 (docker-compose)
hm40006:
  environment:
    KEY_COOLDOWN_S: "35.0"
    MIN_OUTBOUND_INTERVAL_S: "19.0"
    UPSTREAM_TIMEOUT: "55"
    TIER_COOLDOWN_S: "40"
    HM_CONNECT_RESERVE_S: "15"
    TIER_TIMEOUT_BUDGET_S: "110"

# 代码级修复
# upstream.py:493: mark_key_cooling(..., duration_s=45)  ← 22→45
# config.py:189:  cap 30→50  ← 指数退避上限
```

---

## ⏳ 轮到HM2优化HM1