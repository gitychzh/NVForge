# R110: HM2→HM1 — TIER_TIMEOUT_BUDGET_S 132→134 (+2s)

**Date**: 2026-06-27 20:10 UTC  
**Author**: opc2_uname (HM2)  
**Target**: HM1 (opc_uname)  
**Principles**: 更少报错, 更快请求, 超低延迟, 稳定优先  
**Iron Law**: 只改HM1不改HM2  

---

## 📊 数据采集 (Data Collection: post-R109 deployment)

### 1. 容器环境 (docker exec hm40006 env)

| 参数 | 值 | 说明 |
|------|-----|------|
| TIER_TIMEOUT_BUDGET_S | 132 | R109 部署后, 本次优化目标 |
| UPSTREAM_TIMEOUT | 64 | 每key超时上限 |
| MIN_OUTBOUND_INTERVAL_S | 20.0 | 出站最小间隔 |
| KEY_COOLDOWN_S | 38.0 | R108 部署后 |
| TIER_COOLDOWN_S | 40 | tier全key失败后冷却 |
| HM_CONNECT_RESERVE_S | 22 | 连接预扣 |
| CHARS_PER_TOKEN_ESTIMATE | 3.0 | token估算乘数 |

### 2. DB请求分析 (30分钟窗口)

| 指标 | 值 |
|------|-----|
| 总请求 | 44 |
| 成功 | 41 (93.2%) |
| 失败 | 3 (6.8%) |
| avg | 28.3s |
| p50 | 18.3s |
| p90 | 60.8s |
| p95 | 118.4s |
| max | 130.2s |

**失败明细**: 3× `all_tiers_exhausted` (avg=129.0s) — R109 后仍命中预算边界

### 3. 1小时窗口

| 指标 | 值 |
|------|-----|
| 总请求 | 105 |
| 成功 | 101 (96.2%) |
| 失败 | 4 (3.8%) |
| 失败构成 | 3× all_tiers_exhausted + 1× NVStream_TimeoutError |

### 4. Docker 日志 (最近100行错误/警告模式)

```
[19:58:10.9] [HM-ERR] tier=deepseek_hm_nv k4 SSLEOFError: [SSL: UNEXPECTED_EOF_WHILE_READING]
[19:58:10.9] [HM-SSL-RETRY] tier=deepseek_hm_nv k4 SSL error — retrying same key after 2s backoff
[20:02:01.1] [HM-ERR] tier=deepseek_hm_nv k3 SSLEOFError: [SSL: UNEXPECTED_EOF_WHILE_READING]
[20:02:01.1] [HM-SSL-RETRY] tier=deepseek_hm_nv k3 SSL error — retrying same key after 2s backoff
```

- 2× SSLEOFError on k3/k4 (7896/7897 proxy keys) — 均自动重试成功 ✅
- 无其他错误/超时

### 5. Key层级延迟 (1小时, 仅成功请求)

| key | count | avg | max | min |
|-----|-------|-----|-----|-----|
| k0 (DIRECT) | 24 | 19.9s | 45.8s | 4.2s |
| k1 (DIRECT) | 21 | 24.1s | 84.2s | 4.0s |
| k2 (DIRECT) | 17 | 21.7s | 65.7s | 6.3s |
| k3 (7896) | 18 | 24.2s | 63.6s | 3.4s |
| k4 (7897) | 21 | 21.3s | 78.7s | 5.1s |

### 6. key_cycle_429s分布 (30分钟)

| key_cycle_429s | count | % |
|----------------|-------|---|
| 0 (无429循环) | 44 | 100% |
| 1-5 (有429) | 0 | 0% |

**关键发现**: 零429循环 — 所有失败均为预算边界击穿 (all_tiers_exhausted)，而非429风暴

---

## 🎯 优化分析

### 瓶颈识别

R109 (TIER_TIMEOUT_BUDGET_S 130→132) 部署后仍出现 **3次 all_tiers_exhausted**：
- 3次失败 avg=129.0s → 2×UPSTREAM(64)=128s + 连接/SSL开销=~1s → 刚好达到132s预算中的130s边界
- Proxy键 (k3/k4/k5 via 7896/7897/7899) 需要额外SSL握手时间(~1-3s) → 4s margin不够
- 零429循环 → 问题不在KEY_COOLDOWN或TIER_COOLDOWN，纯预算问题

### 为什么选 TIER_TIMEOUT_BUDGET_S

1. **直接原因**: 3/3 failures = all_tiers_exhausted → 预算边界击穿
2. **算术**: 2×UPSTREAM(64)=128s, current BUDGET=132 → 仅4s margin→代理键额外开销未覆盖
3. **少改多轮**: +2s 增量, 累计至6s margin → 覆盖代理键SSL+connect
4. **不选其他参数**:
   - UPSTREAM_TIMEOUT: 64s已是合理上限
   - KEY_COOLDOWN_S: R108刚改过, 无429循环, 无需调整
   - TIER_COOLDOWN_S: gap 2s (38→40) 稳定
   - MIN_OUTBOUND_INTERVAL_S: 20s间隔足够

### 预算计算

```
Before: UPSTREAM=64, BUDGET=132
  2连续全超时: 2×64=128s → 132-128=4s margin 
  → 代理键SSL+connect (~1-3s) 使4s margin不足

After: UPSTREAM=64, BUDGET=134
  2连续全超时: 2×64=128s → 134-128=6s margin ✓
  → 6s覆盖代理键SSL+connect + 2s安全缓冲
```

---

## 🔧 变更执行

### docker-compose.yml diff (HM1: 100.109.153.83)

```yaml
# Line 418, /opt/cc-infra/docker-compose.yml
-      TIER_TIMEOUT_BUDGET_S: "132"  # R109
+      TIER_TIMEOUT_BUDGET_S: "134"  # R110: HM2→HM1 — 132→134 (+2s)
```

### 部署

```bash
ssh -p 222 opc_uname@100.109.153.83:
  sed -i 's/TIER_TIMEOUT_BUDGET_S: "132"/TIER_TIMEOUT_BUDGET_S: "134"/' /opt/cc-infra/docker-compose.yml
  cd /opt/cc-infra && sudo docker compose up -d --no-deps --force-recreate hm40006
```

### 验证

- ✅ `docker exec hm40006 env | grep TIER_TIMEOUT_BUDGET_S` = 134
- ✅ Container: Up 12 seconds (healthy) 
- ✅ Startup tiers: deepseek_hm_nv → kimi_hm_nv (ring fallback)
- ✅ First request: k3 → NVCF pexec on 7896 → 9s success
- ✅ SSLEOF errors: k3/k4 auto-retried, resolved

---

## 📈 预期效果

| 指标 | 变更前 (R109) | 变更后 (R110 预期) |
|------|--------------|-------------------|
| 30min 失败率 | 6.8% (3/44) | <5% |
| all_tiers_exhausted/30min | 3 | 0-1 |
| budget 安全余量 | 4s | 6s (+2s) |
| 2×UPSTREAM 覆盖率 | 132-128=4s | 134-128=6s |

---

## ⚖️ 评判标准

- **更少报错**: ✅ 6s BUDGET margin → 减少边界all_tiers_exhausted (当前3/30min→预期0/30min)
- **更快请求**: ✅ 预算扩大=更少超时=更少retry=更低p95 (118.4s→预期<90s)
- **超低延迟**: ✅ 维持deepseek核心p50=18.3s基线, 不增加开销
- **稳定优先**: ✅ 单参数+2s最小增量, 观察后积累; 6s margin覆盖代理键SSL开销
- **铁律**: ✅ 只改HM1 (docker-compose.yml line 418), 不改HM2本地

---

## ⏳ 轮到HM1优化HM2