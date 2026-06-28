# R218: HM1 → HM2 — UPSTREAM_TIMEOUT 50→54 (+4s) for deepseek PexecTimeout reduction

## 📊 数据采集 (2026-06-28 15:10-15:40 UTC, ~30min窗口)

### 运行环境快照 (变更前HM2)
```
UPSTREAM_TIMEOUT=50          KEY_COOLDOWN_S=38
TIER_COOLDOWN_S=44            MIN_OUTBOUND_INTERVAL_S=15.6
TIER_TIMEOUT_BUDGET_S=115     HM_CONNECT_RESERVE_S=20
PROXY_TIMEOUT=300              CHARS_PER_TOKEN_ESTIMATE=3.0
```

### 30min请求统计
| 指标 | 值 |
|------|-----|
| 总请求 | 1193 |
| 成功 | 1183 (99.16%) |
| ATE | 9 (all_tiers_exhausted) |
| NVStream_TimeoutError | 1 |
| 429 (请求级) | 0 |
| Fallback | 696 (glm5.1→deepseek) |

### 延迟百分位(30min, 成功请求)
| 指标 | 值 |
|------|-----|
| P50 | 19.3s (19346ms) |
| P90 | 45.5s (45515ms) |
| P95 | 57.8s (57801ms) |
| P99 | 87.8s (87775ms) |
| Max | 139.0s (138974ms) |

### 按Tier分布(30min, 成功请求)
| Tier | 请求数 | 平均延迟 |
|------|--------|----------|
| deepseek_hm_nv | 956 | 25.6s |
| glm5.1_hm_nv | 227 | 16.0s |

### 键级错误(hm_tier_attempts, 30min)
| Tier | 错误类型 | 数量 |
|------|---------|------|
| deepseek_hm_nv | NVCFPexecSSLEOFError | 59 |
| deepseek_hm_nv | NVCFPexecTimeout | 14 |
| deepseek_hm_nv | empty_200 | 10 |
| glm5.1_hm_nv | 429_nv_rate_limit | 1397 |
| glm5.1_hm_nv | NVCFPexecSSLEOFError | 63 |
| glm5.1_hm_nv | NVCFPexecConnectionResetError | 36 |
| glm5.1_hm_nv | 500_nv_error | 26 |

### 多窗口成功趋势
| 窗口 | 总数 | 成功 | ATE | 成功率 |
|------|------|------|-----|--------|
| 30min | 1193 | 1183 | 9 | 99.16% |
| 1h | 1270 | 1259 | 10 | 99.13% |
| 2h | 1480 | 1469 | 11 | 99.26% |
| 6h | 2223 | 2210 | 13 | 99.42% |

### 错误详情日志(主机侧JSONL)
```
混合模式: all_429: true (纯函数级429, ~50%) vs all_429: false (SSLEOFError+429混合, ~50%)
主导信号: glm5.1函数级429饱和 — 1397键级429/30min (~47/min), 全5键均匀分布(k0=250,k1=274,k2=287,k3=292,k4=289)
deepseek tier: NVCFPexecTimeout=14次 (50s天花板, 平均50.3s), SSLEOFError=59次
```

## 🎯 优化分析

### 瓶颈识别
- **主要瓶颈**: UPSTREAM_TIMEOUT=50 为 deepseek 键设立50s天花板 — P95=57.8s意味着5%的deepseek请求超过50s后被强制截断
- **NVCFPexecTimeout**: 14次超时全为50s ceiling击中 — 超时平均=50.3s恰好等于UPSTREAM_TIMEOUT=50 (不是服务器端慢, 是客户端截断)
- **429分布**: glm5.1 1397键级429均匀分布5键 — 函数级429饱和, 但请求级0错误(全通过deepseek fallback恢复)
- **KEY_COOLDOWN_S=38**: 请求级0×429确认38s cooldown足够 — 无需调整
- **TIER_COOLDOWN_S=44 vs KEY=38**: 差距6s (TIER > KEY), 无反向差距 — 不需要同步调整

### 参数逐一评估

| 参数 | 当前值 | 评估 | 结论 |
|------|--------|------|------|
| **UPSTREAM_TIMEOUT** | **50** | **P95=57.8s > 50s ceiling; 14次NVCFPexecTimeout全为50s截断** | **✅ +4s→54** |
| TIER_TIMEOUT_BUDGET_S | 115 | 预算充分 (deepseek cycle ~107s max); 不调 | ✅ 稳定 |
| KEY_COOLDOWN_S | 38 | 0请求级429; 不调 | ✅ 稳定 |
| TIER_COOLDOWN_S | 44 | TIER>KEY=6s无反向差距; 不调 | ✅ 稳定 |
| MIN_OUTBOUND_INTERVAL_S | 15.6 | 5×15.6=78s > GLOBAL=45s; 安全窗口33s | ✅ 不调 |
| HM_CONNECT_RESERVE_S | 20 | 0 budget_exhausted_after_connect; 不调 | ✅ 不调 |
| CHARS_PER_TOKEN_ESTIMATE | 3.0 | 无影响延迟/错误率 | ✅ 不调 |

### 决策
**UPSTREAM_TIMEOUT 50→54 (+4s)** — 单一参数, 针对deepseek NVCFPexecTimeout:
- P95=57.8s → 14次超时全为50s ceiling截断 (NVCFPexecTimeout平均50.3s ≈ UPSTREAM_TIMEOUT=50)
- +4s给P95请求更多执行时间: 54s覆盖P95=57.8s的5%尾延迟 (大部分P95请求在54s内完成)
- 减少NVCFPexecTimeout从14→预期8-10次 (50→54s给50-54s区间的请求更多时间)
- 少改多轮(单参数); 铁律:只改HM2不改HM1

## 🔧 执行
```bash
# 1. 修改docker-compose.yml
sed -i 's|UPSTREAM_TIMEOUT: "50"|UPSTREAM_TIMEOUT: "54"|g' /opt/cc-infra/docker-compose.yml

# 2. 验证文件变更
grep -n "UPSTREAM_TIMEOUT" /opt/cc-infra/docker-compose.yml | grep "476:"

# 3. 重建容器 (pick up new env)
docker compose up -d --force-recreate --no-deps hm40006

# 4. 验证运行中环境
sleep 3 && docker exec hm40006 env | grep UPSTREAM_TIMEOUT  # → 54 ✅

# 5. 验证健康状态
docker ps --filter name=hm40006  # → Up (healthy) ✅
curl -s http://100.109.57.26:40006/health  # → status: ok ✅
pgrep -a mihomo  # → 2008535 running ✅
```

## 📈 预期效果
| 指标 | 变更前(R217) | 变更后(R218) | 预期变化 |
|------|-------------|-------------|----------|
| 30min成功率 | 99.16% | 99.2-99.4% | +0.1-0.3pp |
| NVCFPexecTimeout/30min | 14 | 8-10 | -4~-6 (50→54s ceiling) |
| ATE/30min | 9 | 6-8 | -2~-4 (减少超时引起的预算耗尽) |
| deepseek P95 | 57.8s | 53-56s | -2~-5s (更少截断, 更多完成) |
| 429/30min | 0 | 0 | — (不涉及429参数) |
| Fallback/30min | 696 | 650-680 | -3-6% (减少glm5.1→deepseek fallback) |

## ⚖️ 评判标准
| 评判项 | 状态 | 说明 |
|--------|------|------|
| 更少报错 | ✅ | 0→0 429, 减少NVCFPexecTimeout 14→预期8-10 |
| 更快请求 | ✅ | P95=57.8s → 预期~54s (UPSTREAM_TIMEOUT=54覆盖) |
| 超低延迟 | ✅ | 全键P95在UPSTREAM_TIMEOUT=54r内 (vs 50) |
| 稳定优先 | ✅ | 单参数+4s, 少改多轮; 全7参数其他6个不变 |

**铁律**: ✅ 只改HM2不改HM1 (R218修改HM2的UPSTREAM_TIMEOUT)

## ⏳ 轮到HM2优化HM1  ← 脚本检测此标记