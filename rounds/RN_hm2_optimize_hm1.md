# RN: HM2→HM1 — TIER_COOLDOWN_S 35→36 (+1s)

**日期**: 2026-06-27 14:20 UTC
**执行者**: opc2_uname (HM2角色)
**目标**: HM1 (100.109.153.83, port 222)
**前轮**: RN_hm1_optimize_hm2 (HM1→HM2: UPSTREAM_TIMEOUT 59→61, 铁律:只改HM2不改HM1)
**触发**: HM1提交RN_hm1_optimize_hm2→GitHub (commit bf22c8b, 标记 `轮到HM2优化HM1`)

---

## 数据采集 (HM1, ~14:00-14:20 UTC 窗口)

### 1. HM1容器环境变量 (docker exec hm40006 env)
```
UPSTREAM_TIMEOUT=62              # R76: 60→62
TIER_TIMEOUT_BUDGET_S=106        # R81: 104→106
MIN_OUTBOUND_INTERVAL_S=17.5      # R79: 15.5→17.5
KEY_COOLDOWN_S=31.0              # R97: 29.0→31.0
TIER_COOLDOWN_S=35               # R95: 33→35
HM_CONNECT_RESERVE_S=22           # R29
PROXY_TIMEOUT=300                # 固定
```

### 2. HM1日志模式 (docker logs hm40006 --since 1h)
```
核心模式: deepseek 5-key 循环 → 无429, 无ConnectionResetError
错误分布:
  - k5 SSLEOFError × 2 (14:01:43, 14:16:00)
  - 两次错误间隔: ~14.5min
  - 每次SSL错误后: 2s backoff → 重试 → 成功

key使用: k1-k5 均匀轮转 (DIRECT, 代理URLs)
```

### 3. 错误统计 (1h 窗口)
| Error Type | Count | Model/Key |
|------------|-------|-----------|
| SSLEOFError | 2 | k5专属 |
| HM-ERR (total) | 2 | k5 |
| ConnectionResetError | 0 | — |
| 429 | 0 | — |
| ALL-TIERS-FAIL | 0 | — |

请求总数: 88次tier启动, 87次成功, 错误率 2.3%

### 4. 请求延迟 (litellm_nv_hm DB, 最近32条)
```
所有32条: 全部成功 (kimi-k2.6, glm-5.1)
deepseek: 日志中直接成功 (无DB记录, 直连NVCF)
延迟: ~5-18s per request (kimi: 5-8s, glm5.1: 4-5s)
deepseek: 13-20s per key attempt
```

### 5. k5 SSL错误时序
```
14:01:43 - k5 SSLEOFError → 2s backoff → k1重试成功
14:16:00 - k5 SSLEOFError → 2s backoff → k1重试成功
间隔: ~14.5分钟｜k5在5键轮转中出现2次SSL EOF
```

---

## 分析

### 瓶颈定位
1. **k5 SSLEOFError**: HM1的唯一错误源。k5是5键中的最后键(经过多次轮转后触发)。TIER_COOLDOWN=35, KEY_COOLDOWN=31, gap=4s。
2. **SSL EOF机制**: NVCF的SSL连接在多次轮转后(k5位置)被EOF截断。当前gap=4s(键冷却31, tier冷却35)不足以给k5完整冷却窗口。
3. **无429**: deepseek 5键均匀, 没有NVAPI速率限制→配置优化良好。
4. **无ConnectionResetError**: 网络层稳定→之前的cooldown策略生效。

### 决策: TIER_COOLDOWN_S 35→36 (+1s)

**决策逻辑**:
- ✅ k5是唯一错误键(SSL EOF专用)→需要更多tier冷却时间保护它
- ✅ +1s TIER_COOLDOWN = gap从4s(35-31)变为5s(36-31)→给k5额外1s冷却窗口
- ✅ KEY_COOLDOWN=31已经领先tier 4s→+1s进一步扩大差距(5s领先)
- ✅ 无429, 无ConnectionResetError→tier cooldown不需要大改，小幅调整即可
- ✅ 少改多轮(单参数): 只改TIER_COOLDOWN_S一个参数
- ✅ 铁律: 只改HM1不改HM2

**为什么不选其他参数**:
- UPSTREAM_TIMEOUT=62: 对端刚调至61，已是保守值→不动
- KEY_COOLDOWN_S=31.0: R97刚+2s→观察效果
- MIN_OUTBOUND=17.5: 已足够高
- HM_CONNECT_RESERVE=22: 死参数(代码未使用)→不动
- TIER_TIMEOUT_BUDGET=106: 预算充足→不动

### 预算验证 (BUDGET=106, UPSTREAM=62, MIN=17.5, RESERVE=22)
```
1st key attempt = 62s
2nd key attempt = max(10, min(62, 106-62-22-17.5)) = max(10, 4.5) = 10s (floor)
Total: 62+10=72s ≤ 106s ✓ (2nd key被10s floor截断)
```

2nd key在RESERVE=22下只有4.5s可分配，被10s floor保护。

---

## 优化执行

| 参数 | 修改前 | 修改后 | 理由 |
|------|--------|--------|------|
| TIER_COOLDOWN_S | 35 | 36 (+1s) | k5 SSLEOFError=2/1h; SSL UNEXPECTED_EOF k5专用; 4s gap(KEY_COOLDOWN=31→TIER_COOLDOWN=35)不够→+1s推至5s gap→给k5额外冷却; 少改多轮(单参数); 铁律:只改HM1不改HM2 |

**铁律**: 只改HM1配置，绝不改HM2本地

### 执行记录
```bash
# 备份
cp /opt/cc-infra/docker-compose.yml /opt/cc-infra/docker-compose.yml.bak.RN_hm2

# 修改 (line 422)
sed -i '422s|TIER_COOLDOWN_S: "35"|TIER_COOLDOWN_S: "36"|' /opt/cc-infra/docker-compose.yml
# 注释同步为RN描述

# 部署 (只重启hm40006, 不碰mihomo)
cd /opt/cc-infra && docker compose up -d --force-recreate hm40006

# 验证
TIER_COOLDOWN_S=36 ✓
KEY_COOLDOWN_S=31.0 (unchanged) ✓
UPSTREAM_TIMEOUT=62 (unchanged) ✓
Container healthy ✓
mihomo 2 processes running (未碰) ✓
```

### 修改文件清单
- `/opt/cc-infra/docker-compose.yml` line 422:
  - `TIER_COOLDOWN_S: "35"` → `"36"`
  - 注释: `# R95: HM2优化 — ...` → `# RN: HM2优化 — ...`

---

## 预测 (30min后)

| 指标 | 当前 | 预测 | 理由 |
|------|------|------|------|
| SSLEOFError | ~2/h | ↓ 1-2 | +1s tier cooldown→k5在tier冷却中获额外1s→减少SSL EOF |
| 429 | 0 | 0 | deepseek无429→保持 |
| ConnectionResetError | 0 | 0 | 网络层稳定→保持 |
| ALL-TIERS-FAIL | 0 | 0 | deepseek全部成功→保持 |
| 请求延迟 | ~13-20s | ~13-20s | UPSTREAM未改→延迟不变 |

**机制**: +1s TIER_COOLDOWN = k5获得更多tier冷却 = 减少SSL连接被EOF中断 = 更少SSLEOFError = 更快请求完成 = 更低延迟 = 更稳定。

---

## 观察项

1. **k5是唯一错误键**: SSL UNEXPECTED_EOF只在k5上发生。可能是键位顺序(经过4个键后连接耗尽)或NVCF特定端点问题。
2. **KEY_COOLDOWN=31 vs TIER_COOLDOWN=36**: gap=5s，KEY_COOLDOWN领先tier。键级更快恢复→减少429后立即再触发。
3. **mihomo 2进程未动**: 严格遵守—不停止/不重启/不kill。
4. **少改多轮**: 单参数(+1s), 每轮积累。
5. **deepseek无429**: 5键均匀，NVCF pexec成功率高→无需大幅调参。

---

## ⏳ 轮到HM1优化HM2 ← 脚本检测此标记