# R48: HM2 → HM1 — UPSTREAM_TIMEOUT 44→46 (+2s): capture continued >40s deepseek timeout bucket; single-parameter change

## 📊 数据收集 (HM1)

**HM1 当前配置 (docker exec hm40006 env):**
| 变量 | 值 | 来源 |
|---|---|---|
| `UPSTREAM_TIMEOUT` | 44 | R46: HM2优化 42→44 |
| `TIER_TIMEOUT_BUDGET_S` | 96 | R44: HM2优化 94→96 |
| `MIN_OUTBOUND_INTERVAL_S` | 14.0 | R42: HM2优化 13.5→14.0 |
| `KEY_COOLDOWN_S` | 38.0 | R19: HM2优化 35→38 |
| `TIER_COOLDOWN_S` | 82 | R45: HM2优化 84→82 |
| `HM_CONNECT_RESERVE_S` | 22 | R29: HM2优化 21→22 |

**Docker 日志 (最近100行):** 23 error/warn/fail 匹配  
- HM-FALLBACK: glm5.1→deepseek 标准降级路径
- HM-ERR: `deepseek k1 SSLEOFError` (1次)  
- HM-ERR: `glm5.1 k5/k2 ConnectionResetError` (多次)
- HM-TIER-FAIL: `glm5.1 5 keys failed: 429=3`, `deepseek 5 keys failed: timeout=2`
- HM-FALLBACK-SUCCESS: deepseek 成功，kimi 后备成功

**全量日志 (500行 HM 标签分布):**
- 119× HM-KEY, 50× HM-TIER, 43× HM-CYCLE, 43× HM-COOLDOWN
- 34× HM-FALLBACK, 32× HM-SUCCESS, 32× HM-FALLBACK-SUCCESS
- 21× HM-TIER-SKIP, 18× HM-TIMEOUT, 13× HM-TIER-FAIL, 13× HM-ERR
- 9× HM-SSL-RETRY, 8× HM-GLOBAL-COOLDOWN, 3× HM-TIER-BUDGET

### DB 数据 (30分钟窗口)

**错误分布 (hm_tier_attempts):**
| error_type | cnt | avg_elapsed_ms |
|---|---|---|
| 429_nv_rate_limit | 1,129 | — |
| NVCFPexecTimeout | 98 | 29,293 |
| NVCFPexecConnectionResetError | 43 | 1,994 |
| budget_exhausted_after_connect | 5 | 797 |
| NVCFPexecRemoteDisconnected | 4 | 1,210 |

**Fallback:**
- 总请求数: 1,251
- 降级: 1,126 (90.0%) — 较 R46 的 90.3% 微降 0.3pp
- 直接: 125 (10.0%) — avg 16,020ms
- 降级: avg 20,233ms

**Tier 分布:**
| tier | attempts |
|---|---|
| glm5.1_hm_nv | 1,177 |
| deepseek_hm_nv | 100 |
| kimi_hm_nv | 2 |

### Deepseek 超时桶分析 (整体)
| bucket | count |
|---|---|
| <20s | 36 (37.9%) |
| 20-25s | 9 (9.5%) |
| 25-30s | 6 (6.3%) |
| 30-35s | 5 (5.3%) |
| >40s | **39 (41.1%)** |

### Deepseek 超时按键
| 键 | <20s | 20-25s | 25-30s | 30-35s | >40s |
|---|---|---|---|---|---|
| k0 | 6 | 1 | 3 | 0 | 6 |
| k1 | 10 | 2 | 1 | 1 | 8 |
| k2 | 6 | 2 | 1 | 1 | 10 |
| k3 | 7 | 4 | 0 | 0 | 6 |
| k4 | 7 | 0 | 1 | 3 | 9 |

### ConnectionResetError (glm5.1 层, 按键)
| 键 | cnt |
|---|---|
| k0 | 9 |
| k1 | 10 |
| k2 | 7 |
| k3 | 8 |
| k4 | 9 |

### 0-Tier 失败
| 类型 | cnt |
|---|---|
| budget_exhausted_after_connect | 5 |

### 最近请求延迟 (最后 10 条)
```
4004e087  deepseek_hm_nv  16834ms  fallback=t  key_cycle_429s=5  status=200
646129f8  deepseek_hm_nv  20520ms  fallback=t  key_cycle_429s=0  status=200
ea3add41  deepseek_hm_nv  14783ms  fallback=t  key_cycle_429s=0  status=200
8a2e5240  deepseek_hm_nv  10660ms  fallback=t  key_cycle_429s=0  status=200
6e7e1f35  deepseek_hm_nv  18743ms  fallback=t  key_cycle_429s=5  status=200
d3cac724  deepseek_hm_nv  56625ms  fallback=t  key_cycle_429s=6  status=200
6a057f85  kimi_hm_nv      129758ms fallback=t  key_cycle_429s=2  status=200
4f354d4b  deepseek_hm_nv  12945ms  fallback=t  key_cycle_429s=0  status=200
6a8cf991  deepseek_hm_nv   6149ms  fallback=t  key_cycle_429s=0  status=200
ced41c1b  deepseek_hm_nv  36881ms  fallback=t  key_cycle_429s=3  status=200
```

## 🔍 分析诊断

### 根因: >40s 桶在 UPSTREAM=44 下仍占主导

R46 将 UPSTREAM_TIMEOUT 从 42→44 (+2s)，预期捕获 >40s 桶中的 NVCF 完成请求。R46 部署后，>40s 桶有 37 事件（40.7%），是最高的单桶。

**R48 数据确认:** 在 UPSTREAM=44 下，>40s 桶 **39 事件（41.1%）** — 基本上与 R46 的 37 事件持平。这表示：
1. deepseek NVCF 基础设施持续需要 >44s 完成
2. 42→44 的 +2s 增量并未完全捕获边界完成
3. >40s 桶仍在主导且未减弱

**预算计算 (UPSTREAM=44, BUDGET=96, RESERVE=22):**
- 第 1 次尝试: min(44, 96-22=74) = 44s → 超出 44s 的请求超时
- 剩余: 96-44=52
- 第 2 次尝试: max(10, min(44, 52-22=30)) = 30s → 覆盖 25-30s + 30-35s 桶

### ConnectionResetError 增长: 38→43 (+13.2%)
R45 将 TIER_COOLDOWN 从 84→82 (-2s)。这加速了 glm5.1 重试，但也增加了连接重置。ConnectionResetError 在 30 分钟窗口中从 38→43。

### 决策: UPSTREAM_TIMEOUT 44→46
- **理由:** >40s 桶持续 39 事件（41.1%），是最高的超时桶。+2s 增量（44→46）直接扩展第 1 次尝试窗口，捕获更多 deepseek NVCF 完成。
- **少改多轮:** 仅 1 个参数，+2s
- **预算计算 (UPSTREAM=46, BUDGET=96, RESERVE=22):**
  - 第 1 次: min(46, 96-22=74) = 46s
  - 剩余: 96-46=50
  - 第 2 次: max(10, min(46, 50-22=28)) = 28s → 丢失 2s 头空间 (30s→28s)，但仍覆盖 25-30s 桶

## 🎯 优化计划

### 变更: 单参数 — UPSTREAM_TIMEOUT

| 参数 | 之前 | 之后 | 增量 | 理由 |
|---|---|---|---|---|
| `UPSTREAM_TIMEOUT` | 44 | **46** | +2s | 捕获 >40s 桶的 NVCF 完成；第 1 次尝试扩展窗口 |

**不改变:**
- `TIER_TIMEOUT_BUDGET_S=96` — 保持稳定，下轮评估是否需要 96→98 补偿
- `KEY_COOLDOWN_S=38.0` — R19 稳定，无需改动
- `MIN_OUTBOUND_INTERVAL_S=14.0` — R42 验证，SSLEOF 可控
- `TIER_COOLDOWN_S=82` — 已达下限（ConnectionResetError=43，不能再降）
- `HM_CONNECT_RESERVE_S=22` — 饱和，0-tier=5 极低
- NVCF 函数 ID、键、代理端口、mihomo 进程 — 完全不动

**铁律:** 只改 HM1 不改 HM2

### 部署命令
```bash
# 备份
ssh -p 222 opc_uname@100.109.153.83 'cp /opt/cc-infra/docker-compose.yml /opt/cc-infra/docker-compose.yml.bak.R48'

# 值变更 (行 417)
ssh -p 222 opc_uname@100.109.153.83 'cd /opt/cc-infra && sed -i "417s/\"44\"/\"46\"/" docker-compose.yml'

# 注释更新 (行 417)
ssh -p 222 opc_uname@100.109.153.83 "cd /opt/cc-infra && sed -i '417s/# R46:.*$/# R48: HM2优化 — 44→46: +2s upstream timeout; UPSTREAM=46 BUDGET=96 RESERVE=22 1st=46s remain=50 2nd=28s(→40s bucket捕获); deepseek >40s=39(NVCF上限持续); 少改多轮(单参数变更); 铁律:只改HM1不改HM2/' docker-compose.yml"

# 部署
ssh -p 222 opc_uname@100.109.153.83 'cd /opt/cc-infra && docker compose up -d hm40006'
```

## 📈 部署验证

```
Container hm40006 Recreated, Started (healthy)
docker exec hm40006 env:
  UPSTREAM_TIMEOUT=46        ✅ (was 44)
  TIER_TIMEOUT_BUDGET_S=96    ✅ (unchanged)
  KEY_COOLDOWN_S=38.0         ✅ (unchanged)
  MIN_OUTBOUND_INTERVAL_S=14.0 ✅ (unchanged)
  TIER_COOLDOWN_S=82          ✅ (unchanged)
  HM_CONNECT_RESERVE_S=22     ✅ (unchanged)
```

## 📈 预期效果

- >40s 桶应下降至 <35 事件（当前 39）
- 第 1 次尝试捕获更多第 44-46s 窗口的 deepseek 完成
- 第 2 次尝试头空间从 30s→28s (可接受的 2s 损失)
- 降级率可能微降（90.0%→88-89%）
- ConnectionResetError 可能因更少重试而稳定

## ⚠️ 观察项

- 如 >40s 桶持续 >30 事件在 UPSTREAM=46 下，NVCF 基础设施是根本原因 — 非配置可解
- 如第 2 次尝试头空间降至 28s 造成更多 budget_exhausted，下轮需扩展 BUDGET 96→98
- TIER_COOLDOWN_S=82 已达到下限 — ConnectionResetError=43 表示进一步降低会增加连接重置

## ⏳ 轮到 HM1 优化 HM2  ← 脚本检测此标记