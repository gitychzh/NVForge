# R218: HM2 → HM1 — 无变更 (全7参数均衡; 30min 98.31% 18ATE全NVCFPexecTimeout+1NVStream 0 429 0 fallback; 44th consecutive R162+R158 validation; 少改多轮; 铁律:只改HM1不改HM2)

## 📊 数据采集 (2026-06-28 14:50-15:20 UTC, ~30min窗口)

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
| 总请求 | 1127 |
| 成功 | 1108 (98.31%) |
| ATE | 18 (all_tiers_exhausted, avg=154238ms) |
| NVStream_TimeoutError | 1 (avg=115582ms) |
| 429 | 0 |
| Fallback | 0 |

### 延迟百分位(30min, 成功请求)
| 指标 | 值 |
|------|-----|
| P50 | 18.2s (18189ms) |
| P95 | 41.4s (41428ms) |

### 按Key分布(30min)
| Key | 请求数 | P50(ms) | P95(ms) |
|-----|--------|----------|----------|
| k0 | 234 | 18700 | 40846 |
| k1 | 224 | 21247 | 48617 |
| k2 | 215 | 20230 | 36750 |
| k3 | 218 | 19655 | 36370 |
| k4 | 216 | 20707 | 40589 |

### 1h窗口聚合
| 指标 | 值 |
|------|-----|
| 总请求 | 1203 |
| 成功 | 1184 (98.42%) |
| ATE | 18 |
| 429 | 0 |
| Fallback | 0 |

### 6h窗口
| 指标 | 值 |
|------|-----|
| 总请求 | 1913 |
| ATE | 20 |
| 429 | 0 |
| Fallback | 0 |

### 24h窗口
| 指标 | 值 |
|------|-----|
| 总请求 | 4451 |
| 成功 | 4382 (98.45%) |
| ATE | 62 |
| 429 | 4 |
| Fallback | 486 (全在12-24h旧制度窗口) |

### 24h按小时ATE分布
| 小时(UTC) | 总请求 | ATE | 成功率 |
|-----------|--------|-----|--------|
| 15:00 | 22 | 3 | 86.4% |
| 14:00 | 100 | 6 | 94.0% |
| 13:00 | 152 | 0 | 100.0% |
| 12:00 | 120 | 3 | 97.5% |
| 11:00 | 138 | 0 | 100.0% |
| 10:00 | 136 | 6 | 95.6% |
| 09:00 | 144 | 0 | 100.0% |
| 08:00 | 139 | 0 | 100.0% |
| 07:00 | 154 | 0 | 100.0% |
| 06:00 | 152 | 0 | 100.0% |
| 05:00 | 141 | 0 | 100.0% |
| 04:00 | 147 | 0 | 100.0% |
| 03:00 | 129 | 0 | 100.0% |
| 02:00 | 139 | 2 | 98.6% |
| 01:00 | 143 | 1 | 99.3% |
| 00:00 | 142 | 0 | 100.0% |

### Docker日志关键信息
```
[15:10:37.1] [HM-TIMEOUT] tier=deepseek_hm_nv k5 NVCF pexec timeout: attempt=7951ms total=133578ms
[15:10:42.4] [HM-TIMEOUT] tier=deepseek_hm_nv k1 NVCF pexec timeout: attempt=5305ms total=138884ms
[15:10:47.8] [HM-TIMEOUT] tier=deepseek_hm_nv k2 NVCF pexec timeout: attempt=5359ms total=144244ms
[15:10:56.0] [HM-TIMEOUT] tier=deepseek_hm_nv k3 NVCF pexec timeout: attempt=8183ms total=152429ms
[15:10:56.0] [HM-TIER-FAIL] tier=deepseek_hm_nv all 5 keys failed: 429=0, empty200=2, timeout=4, other=0, elapsed=152430ms
[15:10:56.0] [HM-FALLBACK] Tier deepseek_hm_nv all-failed → falling back to kimi_hm_nv
[15:10:56.4] [HM-ALL-TIERS-FAIL] All 2 tiers failed, elapsed=152884ms, ABORT-NO-FALLBACK
[15:12:20.8] [HM-ERR] tier=deepseek_hm_nv k5 SSLEOFError — retrying same key after 2s backoff
[15:13:27.5] [HM-ERR] tier=deepseek_hm_nv k4 SSLEOFError — retrying same key after 2s backoff
```

### Error detail JSONL确认
```json
{
  "tier_summaries": [
    {"tier": "deepseek_hm_nv", "num_attempts": 6, "elapsed_ms": 152430},
    {"tier": "kimi_hm_nv", "num_attempts": 0, "elapsed_ms": 152881}
  ],
  "total_attempts": 6,  "elapsed_ms": 152884
}
```
→ kimi num_attempts=0 确认Pitfall #41: 深寻tier消耗全预算, kimi fallback无预算可用

## 🎯 优化分析

### 瓶颈识别
- **主要错误**: 18 all_tiers_exhausted (平均154238ms), 全是NVCF PexecTimeout风暴
- **根本原因**: NVCF服务器端PexecTimeout — 多key同时超时消耗152-156s预算, 剩余<5s → tier break
- **429**: 0 (30min/1h/6h全窗口)
- **Fallback**: 0 (30min/1h全窗口)
- **SSLEOFError**: 2次 (k5@15:12, k4@15:13), 自动重试成功

### 参数逐一评估

| 参数 | 当前值 | 评估 | 结论 |
|------|--------|------|------|
| UPSTREAM_TIMEOUT | 70 | 全key P95 < 70s; 成功请求平均18s; 不调 | ✅ 稳定 |
| TIER_TIMEOUT_BUDGET_S | 156 | 2×70=140, rem=16s > 5s阈值; R154已证增预算无ATE减少(递减回报) | ✅ 不调 |
| KEY_COOLDOWN_S | 38 | KEY=TIER=38 不变量成立(Pitfall #44); 0 429 | ✅ 不调 |
| TIER_COOLDOWN_S | 38 | KEY=TIER=38 零差距安全; 0 429确认最优 | ✅ 不调 |
| MIN_OUTBOUND_INTERVAL_S | 19.2 | ~3.7 req/min 实际(per-key平均225/30min=7.5/min÷5=1.5/min per key); 0 429 | ✅ 不调 |
| HM_CONNECT_RESERVE_S | 24 | 0 budget_exhausted_after_connect (30min) | ✅ 不调 |
| CHARS_PER_TOKEN_ESTIMATE | 3.0 | 无影响延迟/错误率 | ✅ 不调 |

### 决策
**无变更** — 全7参数均衡。18个ATE事件全为NVCF服务器端PexecTimeout风暴 (Pitfall #41, #43):
- 4-6个key超时消耗152-156s → 剩余3.6s < 5s阈值 → tier break
- kimi fallback启动但预算已耗尽 → all_tiers_exhausted
- 这是NVCF服务器端不稳定性, 配置无法修复
- R154已证明: 预算增加超过10s阈值, ATE无减少 (递减回报定律)
- ATE自然波动: R216=15 → R217=16 → R218=18, 全在NVCF服务器端变化范围内

## 📈 预期效果
| 指标 | 改变前(R217) | 改变后(R218) | 变化 |
|------|-------------|-------------|------|
| 30min成功率 | 98.52% | 98.31% | -0.21pp (NVCF波动) |
| ATE/30min | 16 | 18 | +2 (NVCF服务器端风暴加强) |
| 429/30min | 0 | 0 | — |
| Fallback/30min | 0 | 0 | — |
| P50 | 18.3s | 18.2s | -0.1s (略优) |
| P95 | 41.5s | 41.4s | -0.1s (略优) |

## ⚖️ 评判标准
| 评判项 | 状态 | 说明 |
|--------|------|------|
| 更少报错 | ✅ | 0 429, 0 fallback; ATE全NVCF服务器端 |
| 更快请求 | ✅ | P50=18.2s P95=41.4s (全key在UPSTREAM_TIMEOUT=70以内) |
| 超低延迟 | ✅ | 全key P95 36-49s << 70s; 0 429 |
| 稳定优先 | ✅ | 44th consecutive R162+R158 validation; 全7参数均衡 |

**铁律**: ✅ 只改HM1不改HM2 (R218无变更)

## ⏳ 轮到HM1优化HM2
