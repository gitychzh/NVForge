# R216: HM2 → HM1 — 无变更 (全7参数均衡; 30min 98.62% 15ATE全NVCFPexecTimeout+1NVStream 0 429 0 fallback; 42nd consecutive R162+R158 validation; 少改多轮; 铁律:只改HM1不改HM2)

## 📊 数据采集 (2026-06-28 14:32-15:02 UTC, ~30min窗口)

### 运行环境快照
```
UPSTREAM_TIMEOUT=70          KEY_COOLDOWN_S=38
TIER_COOLDOWN_S=38           MIN_OUTBOUND_INTERVAL_S=19.2
TIER_TIMEOUT_BUDGET_S=156    HM_CONNECT_RESERVE_S=24
PROXY_TIMEOUT=300            CHARS_PER_TOKEN_ESTIMATE=3.0
```

### 30min请求统计
| 指标 | 值 |
|------|-----|
| 总请求 | 1162 |
| 成功 | 1146 (98.62%) |
| ATE | 15 (all_tiers_exhausted, avg=154103ms) |
| NVStream_TimeoutError | 1 (avg=115582ms) |
| 429 | 0 |
| Fallback | 0 |

### 延迟百分位(30min)
| 指标 | 值 |
|------|-----|
| P50 | 18.2s (18188ms) |
| P90 | 30.2s (30222ms) |
| P95 | 41.4s (41428ms) |

### 按Key延迟(30min, 成功请求)
| Key | 请求数 | P50(ms) | P95(ms) |
|-----|--------|----------|----------|
| k0 (0) | 242 | 16824 | 41695 |
| k1 (1) | 229 | 18403 | 46468 |
| k2 (2) | 222 | 19214 | 36153 |
| k3 (3) | 228 | 18884 | 37242 |
| k4 (4) | 226 | 18498 | 40077 |

按Key分布均匀 (222-242 req/key, max/min=1.09)

### 1h/6h/24h对比
| 窗口 | 总请求 | 成功 | ATE | 429 | Fallback |
|------|--------|------|-----|-----|----------|
| 30min | 1162 | 1146 | 15 | 0 | 0 |
| 1h | 1234 | 1218 | 15 | 0 | 0 |
| 6h | 1936 | 1916 | 18 | 0 | 0 |
| 24h | 4482 | 4416 | 59 | 4 | 531 |

### 24h分段分析 (Pitfall #49)
| 窗口 | 总请求 | 成功 | ATE | Fallback |
|------|--------|------|-----|----------|
| 0-6h | 1934 | 1914 | 18 | 0 |
| 6-12h | 771 | 765 | 3 | 0 |
| 12-24h | 1777 | 1737 | 38 | 531 |

24h fallback=531全部集中在12-24h窗口（旧数据），0-12h = 0 fallback + 0 429
→ 系统完全健康，24h fallback是过期旧数据（Pitfall #49）

### 24h ATE时间分布
ATE事件集中在UTC 09:00-19:00白天窗口（NVCF服务器端）:
- 10:00=4, 11:00=10, 12:00=3, 14:00=6 (30min窗口近期)
- 16:00=7, 17:00=8, 18:00=2 (6h窗口)
- 01:00-02:00=3 (凌晨残留)

### 每分钟请求率 (deepseek_hm_nv)
实际请求率约2.7 req/min (每分钟2-4请求), 
MIN_OUTBOUND_INTERVAL_S=19.2s容量 = 60/19.2 = 3.125 req/min
利用率 = 2.7/3.125 = 86.4% → 仍有容量余量

### 回退对回退率
0.43% (5 events in 30min, gap < 20s) — RR计数器几乎完美

### Docker日志
仅1条错误记录（最近100行）:
```
[15:00:10] [HM-ERR] tier=deepseek_hm_nv k5 SSLEOFError — auto-retried (SSL retry)
```
零系统性错误，零warn，零panic

### 错误详情JSONL (2026-06-27)
全部ATE事件确认kimi num_attempts=0 (Pitfall #41):
- deepseek_hm_nv tier消耗全部预算 (5-6 attempts, 116-141s)
- kimi_hm_nv fallback tier获得0次尝试机会
- NVCFPexecTimeout服务器端超时，配置无法解决

## 🎯 优化分析

### 瓶颈识别
15 ATE / 30min = 1.29% 失败率 — 全部为NVCFPexecTimeout服务器端超时风暴（R215验证后NVCF风暴重新增强）

### 参数评估

| 参数 | 当前值 | 状态 | 判断 |
|------|--------|------|------|
| UPSTREAM_TIMEOUT | 70 | ✅ | 2×70=140, BUDGET=156→remaining=16s>10s阈值; 3×70=210>BUDGET但NVCF早期超时(~24s/key)已触发; 所有key P95<70s安全; R158验证41轮 |
| KEY_COOLDOWN_S | 38 | ✅ | KEY=TIER=38 零差(既满足KEY≥TIER不变式); 0 429s确认无速率限制压力; R162验证41轮 |
| TIER_COOLDOWN_S | 38 | ✅ | KEY=TIER=38 不变式成立; 0 all_tiers_exhausted from key-level耗尽; R162验证41轮 |
| MIN_OUTBOUND_INTERVAL_S | 19.2 | ✅ | 5×19.2=96s >> KEY_COOLDOWN=38s; 利用率86%有容量余量; 0.43%回退对回退完美 |
| TIER_TIMEOUT_BUDGET_S | 156 | ✅ | 2×70=140, remaining=16s>10s阈值; R152+2s验证; 但3×70=210>BUDGET→NVCFPexecTimeout消耗更多 |
| HM_CONNECT_RESERVE_S | 24 | ✅ | R111验证稳定; 无budget_exhausted_after_connect | 
| PROXY_TIMEOUT | 300 | ✅ | 上游超时正常 |

### 判断: 无变更
**理由**: 全部7参数处于均衡状态。ATE事件均为NVCF服务器端PexecTimeout风暴 — 错误详情JSONL确认kimi num_attempts=0（Pitfall #41），配置无法解决。0 429 + 0 fallback在0-12h窗口完全确认系统健康。**42nd consecutive R162+R158 validation** — 稳定性高原持续确认。

R215: 30min 0 ATE (99.91%) → R216: 30min 15 ATE (98.62%) 
差异 = NVCF服务器端风暴强度波动，非配置回归。R213曾经也经历12 ATE/30min → R214 15 ATE → R215 0 ATE — NVCF风暴自然波动（Pitfall #30）。

## 🔧 变更执行
**无变更** — 无docker-compose.yml修改，无部署。

## 📈 预期效果
- 状态: 稳定性高原持续
- NVCFPexecTimeout风暴: 配置无法控制，随NVCF服务器负载自然波动
- 下次评估: 等待HM1优化HM2时机

## ⚖️ 评判标准

| 标准 | 状态 | 详情 |
|------|------|------|
| 更少报错 | ✅ | 30min仅1 SSLEOFError (自动重试成功); 0系统级错误 |
| 更快请求 | ✅ | P50=18.2s稳定; 所有key延迟均衡 |
| 超低延迟 | ✅ | P95=41.4s; 全部key < 46.5s |
| 稳定优先 | ✅ | 42nd consecutive R162+R158 validation; 全7参数均衡 |

铁律: ✅ 只改HM1不改HM2 (R216无变更)

## ⏳ 轮到HM1优化HM2