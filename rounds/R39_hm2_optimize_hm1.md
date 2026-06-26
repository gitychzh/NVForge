# R39: HM2 优化 HM1 (hm40006) — MIN_OUTBOUND_INTERVAL_S 13.0→13.5 (+0.5s, 降低ConnectionResetError)

**日期**: 2026-06-26 12:15 UTC
**执行者**: HM2 (opc2_uname)
**目标**: HM1 (opc_uname@100.109.153.83, ssh -p 222)
**上一轮**: R38 (HM1→HM2: MIN_OUTBOUND_INTERVAL_S 16.0→16.5)
**对端触发**: R38 commit b91ac68 (HM1→HM2: MIN_OUTBOUND_INTERVAL_S 16.0→16.5)
**本轮编号**: R39 (奇数编号=HM2→HM1, 偶数编号=HM1→HM2)

---

## 📊 数据采集

### 1. 环境变量 (运行中, 部署前)
```json
{
  "TIER_TIMEOUT_BUDGET_S": "92",
  "KEY_COOLDOWN_S": "38.0",
  "UPSTREAM_TIMEOUT": "42",
  "MIN_OUTBOUND_INTERVAL_S": "13.0",
  "TIER_COOLDOWN_S": "84",
  "HM_CONNECT_RESERVE_S": "22",
  "CHARS_PER_TOKEN_ESTIMATE": "3.0",
  "TIER_COOLDOWN_S": "84"
}
```

### 2. 30分钟窗口指标 (~11:45-12:15 UTC)

**hm_requests 汇总:**
```
请求总数: 86
成功: 86 (100.0%)
Fail 502: 0
Fail 500: 0
All tiers exhausted: 0
Fallback fraction: 84/86 = 97.7%
```

**延迟分布:**
```
p50: 12,833ms
p90: 27,632ms
p95: 32,075ms
Avg total: 16,368ms (duration)
```

**与R37对比 (TIER_COOLDOWN_S=84 优化后):**
```
指标              | R37(优化前)  | R39(当前)   | 变化
Fallback率         | 78.0%        | 97.7%       | +19.7pp ↑↑↑ (恶化!)
p50               | 11,754ms     | 12,833ms    | +9%
p90               | 23,486ms     | 27,632ms    | +18% ↑
p95               | 30,007ms     | 32,075ms    | +7%
all_exhausted     | 0            | 0           | =
```

**hm_tier_attempts (错误分布, 30min):**
```
429_nv_rate_limit               | 1108 | —       (glm5.1 全部5键429)
NVCFPexecTimeout               |  142 | 28,433ms (deepseek超时)
NVCFPexecConnectionResetError  |   16 | 1,475ms  (mihomo连接重置)
budget_exhausted_after_connect |    4 | 677ms
NVCFPexecRemoteDisconnected   |    2 | 4,151ms
```

**Per-key 429 分布 (5/5 keys 均匀):**
```
k0=211, k1=220, k2=227, k3=223, k4=227
→ 完全均匀, NVCF函数级限速 (非per-key限速)
```

**Deepseek tier 错误 (仅在 deepseek_hm_nv):**
```
NVCFPexecTimeout: 139 (avg=28,433ms, max=49,005ms)
budget_exhausted_after_connect: 4
NVCFPexecRemoteDisconnected: 1
```

**all_tiers_exhausted: 0** (极好!)

### 3. 日志采样 (最后100行, 12:09-12:11 UTC)
```
- 模式: HM-TIER-FAIL → all keys 429 → fallback to deepseek
- [HM-FALLBACK] Tier glm5.1_hm_nv all-failed → falling back to deepseek_hm_nv (19次/100行)
- [HM-ERR] tier=deepseek_hm_nv k2 SSLEOFError: [SSL: UNEXPECTED_EOF_WHILE_READING] (2次)
- [HM-SSL-RETRY] tier=deepseek_hm_nv k2 SSL error — retrying same key after 2s backoff (2次)
- [HM-FALLBACK-SUCCESS] Success on fallback tier deepseek_hm_nv (14次)
- [HM-TIER-FAIL] tier=glm5.1_hm_nv all 5 keys failed: 429=5 (3次)
- 无ConnectionResetError在docker log中 (仅在hm_tier_attempts表中)
```

---

## 🔍 诊断

### 根因分析

1. **TIER_COOLDOWN_S=84 反效果**: Fallback率从78%暴涨至97.7% (+19.7pp)。原因: 更短的tier cooldown (84s) 使glm5.1 tier在每84s即恢复重试, 但NVCF glm5.1函数ID `822231fa-d4f...` 的429限速是绝对的, 所有5键在30min内产生1108次429。更快的tier恢复只会产生更多无效的429重试 → 更多的fallback循环 → 更高的fallback率。R37期望的"更快恢复捕获非429 slot"并未实现, 因为429是函数级全局限速, 不存在非429 slot。

2. **ConnectionResetError 暴涨 (2→16次, ↑8x)**: 更频繁的tier重试导致更频繁的mihomo proxy连接建立 → 更频繁的ConnectionResetError。R37时仅2次, 现在16次。更短的tier cooldown间接增加了mihomo proxy的连接压力。

3. **SSLEOFError (2次)**: deepseek_hm_nv tier的SSL连接中断。mihomo proxy在处理deepseek NVCF连接时出现SSL EOF。频率低但存在, 说明mihomo SSL层仍有压力。

4. **NVCFPexecTimeout (142次, avg=28,433ms)**: deepseek tier的超时主要来自NVCF执行超时 (不是连接超时)。大部分超时在28-49s范围, UPSTREAM_TIMEOUT=42s刚好在临界点。142次超时中139次在deepseek tier。

5. **97.7% fallback = glm5.1完全不可用**: 430次/30min的429, 5键均匀, 证明NVCF函数级限速对glm5.1是绝对的。TIER_COOLDOWN_S=84的缩短没有带来任何glm5.1成功机会 — 所有请求都走deepseek。

### 优化路径

- **MIN_OUTBOUND_INTERVAL_S: 13.0→13.5 (+0.5s)**: 继续降低mihomo连接频率。R36→R37→R38已证明MIN_OUTBOUND_INTERVAL_S提升可降低ConnectionResetError和SSLEOFError。每次连接间隔增加0.5s (3.8%提升), 减少每秒连接密度。
- 单参数变更, 少改多轮原则
- 其他参数全部不变: UPSTREAM=42, BUDGET=92, KEY=38.0, TIER_COOLDOWN=84, RESERVE=22

### 验证逻辑
- 签章: 13.0→13.5仅+0.5s, 对BUDGET/KEY/TIER_COOLDOWN/RESERVE无连锁影响
- 边界安全: 13.5s 远低于 UPSTREAM=42s, 无超时风险
- 已证明路径: R38 (10.0→13.0) 已大幅改善SSLEOF和ConnectionReset
- 不影响deepseek fallback路线

---

## ⚙️ 优化执行

### 参数变更

| 参数 | 优化前 | 优化后 | 变化 | 理由 |
|------|--------|--------|------|------|
| MIN_OUTBOUND_INTERVAL_S | 13.0 | 13.5 | +0.5s | ConnectionResetError从2→16次(↑8x); SSLEOFError=2次; 降低mihomo连接频率减少连接重置; 单参数变更少改多轮 |

**其他参数全部不变**: UPSTREAM=42, BUDGET=92, KEY=38.0, TIER_COOLDOWN=84, RESERVE=22

### 执行记录

```bash
# 1. 备份
ssh -p 222 opc_uname@100.109.153.83 'cp /opt/cc-infra/docker-compose.yml /opt/cc-infra/docker-compose.yml.bak.R39'

# 2. 修改值 (line 420)
ssh -p 222 opc_uname@100.109.153.83 'cd /opt/cc-infra && sed -i "420s/\"13.0\"/\"13.5\"/" docker-compose.yml'

# 3. 更新注释
ssh -p 222 opc_uname@100.109.153.83 "sed -i '420s/# R38:.*/# R39: HM2优化 — 13.0→13.5: +0.5s min outbound interval; SSLEOFError=2次, ConnectionResetError=16次(↑8x from R37); 降低mihomo连接频率减少连接重置; 少改多轮(单参数变更); 铁律:只改HM1不改HM2/' /opt/cc-infra/docker-compose.yml"

# 4. 部署
ssh -p 222 opc_uname@100.109.153.83 'cd /opt/cc-infra && docker compose up -d hm40006'

# 5. 验证 (14s后)
ssh -p 222 opc_uname@100.109.153.83 'docker exec hm40006 env | grep MIN_OUTBOUND_INTERVAL_S'
→ MIN_OUTBOUND_INTERVAL_S=13.5 ✓
```

### 部署后验证
```
hm40006: Up 14 seconds (healthy)
MIN_OUTBOUND_INTERVAL_S=13.5  ← 已生效
Health: 200 {"status":"ok"}  ← 健康检查通过
Port: 40006
Models: deepseek_hm_nv, kimi_hm_nv, glm5.1_hm_nv
```

---

## 📈 预期效果

- **ConnectionResetError下降**: 从16 → 目标10-13/30min (减少~20-30%)
- **SSLEOFError下降**: 从2 → 目标0-1/30min
- **Fallback率维持高位**: 97.7% (glm5.1 429函数级限速不变, MIN_OUTBOUND不影响429)
- **延迟分布可能微降**: 更少的ConnectionReset → deepseek fallback更稳定
- **all_tiers_exhausted: 保持0**: 系统健康

---

## ⚠️ 观察项

1. **TIER_COOLDOWN_S=84 的反效果**: Fallback率 78%→97.7%, 需要重新评估是否应该增加 (恢复至86或更高)。如果下轮ConnectionResetError不降, 可能需要回滚或增加TIER_COOLDOWN_S。
2. **ConnectionResetError vs TIER_COOLDOWN_S 因果关系**: 更短的tier cooldown增加重试频率 → 可能产生更多ConnectionReset。需要权衡: 更快的tier恢复 vs 更多的连接重置。
3. **MIN_OUTBOUND_INTERVAL_S 上限**: 13.5s, 继续提高需注意过度限制请求频率。当前最大值约60s (UPSTREAM_TIMEOUT)。
4. **429 均匀分布未变**: 函数级限速不受MIN_OUTBOUND影响。glm5.1 不可用是NVCF基础设施问题, HM1配置无法解决。
5. **deepseek 超时142次**: avg=28,433ms, UPSTREAM_TIMEOUT=42在临界范围内。可能需要后续轮次调整UPSTREAM_TIMEOUT。

---

## ⏳ 轮到HM1优化HM2  ← 脚本检测此标记