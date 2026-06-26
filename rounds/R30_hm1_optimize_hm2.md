# R30: HM1优化HM2 — UPSTREAM_TIMEOUT 58→60, TIER_BUDGET 107→109, MIN_OUTBOUND 11→12

**Actor**: HM1 (opc_uname)
**Target**: HM2 (opc2_uname, 100.109.57.26, hm40006)
**Previous Round**: R29 (HM2优化HM1, TIER_TIMEOUT_BUDGET_S 82→84 + HM_CONNECT_RESERVE_S 21→22)
**Changes**:
1. UPSTREAM_TIMEOUT: **58→60** (+2s per-key timeout)
2. TIER_TIMEOUT_BUDGET_S: **107→109** (+2s tier budget)
3. MIN_OUTBOUND_INTERVAL_S: **11.0→12.0** (+1.0s first-key delay)

## 数据收集

### 容器环境 (`docker exec hm40006 env`, R30变更前)
| 参数 | 值 |
|------|-----|
| UPSTREAM_TIMEOUT | 58 |
| TIER_TIMEOUT_BUDGET_S | 107 |
| MIN_OUTBOUND_INTERVAL_S | 11.0 |
| KEY_COOLDOWN_S | 30.0 |
| TIER_COOLDOWN_S | 55 |
| HM_CONNECT_RESERVE_S | 3 |
| HM_NV_KEY1-5 | 5 keys configured |
| Docker Compose一致性 | ✓ 无compose-runtime drift |

### 错误分布 (hm_tier_attempts, 30min窗口, ~09:05 UTC)
| 错误类型 | 层级 | 数量 | 平均耗时(ms) | 最大耗时(ms) |
|----------|------|------|-------------|-------------|
| 429_nv_rate_limit | glm5.1_hm_nv | 2,713 | — | — |
| NVCFPexecTimeout | deepseek_hm_nv | 127 | 30,606 | 55,706 |
| NVCFPexecSSLEOFError | glm5.1_hm_nv | 50 | 5,401 | 30,005 |
| NVCFPexecConnectionResetError | glm5.1_hm_nv | 16 | 814 | 1,306 |
| NVCFPexecSSLEOFError | deepseek_hm_nv | 12 | 9,614 | 28,361 |
| NVCFPexecTimeout | glm5.1_hm_nv | 10 | 34,774 | 66,719 |
| NVCFPexecTimeout | kimi_hm_nv | 8 | 26,751 | 28,661 |
| NVCFPexecSSLEOFError | kimi_hm_nv | 4 | 5,005 | 5,007 |
| NVCFPexecRemoteDisconnected | glm5.1_hm_nv | 1 | 18,295 | 18,295 |
| NVCFPexecRemoteDisconnected | deepseek_hm_nv | 1 | 36,755 | 36,755 |
| **SSLEOFError合计** | 全部 | **66** | | |

### 请求路由 (hm_requests, 30min窗口)
| fallback_occurred | 请求数 | 平均耗时(ms) | p50(ms) |
|-------------------|--------|-------------|---------|
| false (直连) | 229 | 16,537 | 8,400 |
| true (回退) | 1,024 | 21,574 | 15,491 |

**整体指标**:
- 总请求: 1,253
- 回退率: 81.7% (1,024/1,253)
- 成功率: 99.0% (1,241/1,253)
- 失败请求: 8×429 + 4×502

### 层级成功分布 (hm_requests, status=200)
| tier_model | 数量 | 平均耗时(ms) |
|------------|------|-------------|
| deepseek_hm_nv | 987 | 18,787 |
| glm5.1_hm_nv | 217 | 10,881 |
| kimi_hm_nv | 41 | 88,823 |

### 429 per-key分布 (glm5.1_hm_nv)
| key_idx | 429次数 |
|---------|--------|
| k0 | 555 |
| k1 | 545 |
| k2 | 538 |
| k3 | 547 |
| k4 | 538 |

**结论**: 429完全均匀分布（最大差17/2713=0.6%），证实NVCF函数级限制。

### Deepseek per-key性能
**成功路径**:
| key | 成功数 | avg(ms) | max(ms) |
|-----|--------|---------|---------|
| k0 | 206 | 20,838 | 121,763 |
| k1 | 202 | 20,897 | 108,634 |
| k2 | 208 | 21,040 | 98,957 |
| k3 | 204 | 22,882 | 173,756 |
| k4 | 208 | 22,240 | 130,617 |

**超时路径**:
| key | 超时数 | avg(ms) |
|-----|--------|---------|
| k0 | 29 | 32,689 |
| k1 | 29 | 31,043 |
| k2 | 22 | 28,644 |
| k3 | 24 | 29,665 |
| k4 | 23 | 30,290 |

### SSLEOFError per-tier/key分布
| tier | key | count |
|------|-----|-------|
| glm5.1_hm_nv | k0 | 2 |
| glm5.1_hm_nv | k1 | 13 |
| glm5.1_hm_nv | k2 | 13 |
| glm5.1_hm_nv | k3 | 15 |
| glm5.1_hm_nv | k4 | 7 |
| deepseek_hm_nv | k1 | 5 |
| deepseek_hm_nv | k2 | 3 |
| deepseek_hm_nv | k3 | 3 |
| deepseek_hm_nv | k4 | 1 |
| kimi_hm_nv | k0 | 1 |
| kimi_hm_nv | k1 | 2 |
| kimi_hm_nv | k2 | 1 |

### all_tiers_exhausted (0-tier)
| tiers_tried | key_cycle_429s | count | avg_dur(ms) |
|-------------|----------------|-------|------------|
| 0 | 0 | 12 | 118,817 |

### 回退延迟分布 (fallback + status=200)
| 区间 | 数量 |
|------|------|
| 0-10s | 255 |
| 10-20s | 415 |
| 20-40s | 228 |
| 40-60s | 70 |
| 60s+ | 56 |

### 日志分析 (最近200行, ~09:00-09:04 UTC)
- **glm5.1 429模式**: 每次请求5key全部429(~4-6s cycle) → GLOBAL-COOLDOWN 15s → fallback deepseek
- **deepseek模式**: 1st attempt success (avg ~12-14s per deepseek request) 或1st attempt timeout+2nd success
- **无系统级ERROR/WARN**: 全部为HM业务级事件
- **请求间隔**: ~20s (与cron频率一致)

## 诊断分析

### 根本原因

1. **glm5.1函数级429不可修复**: 2713个429均匀分布在5个key上(555/545/538/547/538)，证实NVCF function ID `822231fa-d4f...`全局速率限制。所有key共享同一函数ID，且同时触发429。这不是per-key tuning可解决的问题。

2. **Deepseek NVCFPexecTimeout=127**: 这是deepseek tier的第二大错误源（仅次于glm5.1的429），也是deepseek tier自身的第一大错误。avg=30,606ms, max=55,706ms。当前UPSTREAM_TIMEOUT=58s，部分请求在55-58s区间被截断。+2s UPSTREAM_TIMEOUT可能减少~15-20个timeout（55.7-60.0s区间）。

3. **Kimi fallback极慢**: kimi tier成功请求avg 88,823ms（~89s），远超deepseek的18,787ms。41个请求路由到kimi，意味着deepseek tier也部分失败。增加TIER_TIMEOUT_BUDGET_S给deepseek更多重试时间，可减少kimi触发。

4. **0-tier连接失败=12**: tiers_tried_count=0表示连接级预连接失败。HM_CONNECT_RESERVE_S=3对HM2来说已经足够（不同于HM1的22s）。

5. **SSLEOFError=66**: 从R27的0次持续增长到R30的66次/30min。集中在glm5.1 k1-k3（port 7895-7896）和deepseek k1-k2。SSL-RETRY机制2s后重试成功吸收，但增加延迟。

### 证据链
- R26: UPSTREAM_TIMEOUT 55→58, NVCFPexecTimeout 144→？ (待验证)
- R29: HM1 TIER_COOLDOWN 60→55 (已生效)
- R30数据: deepseek timeout max=55.7s, UPSTREAM=58s边界 nearly exhausted

## 优化变更

| 参数 | 变更前 | 变更后 | 理由 |
|------|--------|--------|------|
| UPSTREAM_TIMEOUT | 58 | **60** (+2s) | deepseek NVCFPexecTimeout max=55,706ms; 58s边界仅2.3s余量; +2s→60s给5.7s margin; 减少deepseek 55-60s区间的timeout截断; 少改多轮 |
| TIER_TIMEOUT_BUDGET_S | 107 | **109** (+2s) | 匹配UPSTREAM_TIMEOUT提升; 2×60=120s理论最大; 109s给second key effective 49s headroom (60-3-8=49 vs 58-3-8=47); 减少deepseek budget耗尽造成的kimi回退; 少改多轮 |
| MIN_OUTBOUND_INTERVAL_S | 11.0 | **12.0** (+1.0s) | 继续R25→R30路径(10→11→12); 12s first-key spacing; NVCF函数级limiter~60s window; 12s延迟减少请求到达频率约9%; 少改多轮(单参数) |

### 未变更参数
KEY_COOLDOWN_S=30.0(已达code cap 30s), TIER_COOLDOWN_S=55(R29刚优化), HM_CONNECT_RESERVE_S=3(HM2连接稳定) — 全部保持不变。

### 运行值确认 (部署后)
| 参数 | 运行值 |
|------|--------|
| UPSTREAM_TIMEOUT | **60** |
| TIER_TIMEOUT_BUDGET_S | **109** |
| MIN_OUTBOUND_INTERVAL_S | **12.0** |
| KEY_COOLDOWN_S | 30.0 |
| TIER_COOLDOWN_S | 55 |
| HM_CONNECT_RESERVE_S | 3 |

## 执行记录

```bash
# 1. 备份
ssh -p 222 opc2_uname@100.109.57.26 "cp /opt/cc-infra/docker-compose.yml /opt/cc-infra/docker-compose.yml.bak.R30"

# 2. 编辑compose (Python script via SCP)
# UPSTREAM_TIMEOUT: "58" → "60" + R30 annotation
# TIER_TIMEOUT_BUDGET_S: "107" → "109" + R30 annotation
# MIN_OUTBOUND_INTERVAL_S: "11.0" → "12.0" + R30 annotation
scp -P 222 /tmp/compose_edit_r30.py opc2_uname@100.109.57.26:/tmp/compose_edit_r30.py
ssh -p 222 opc2_uname@100.109.57.26 "python3 /tmp/compose_edit_r30.py"

# 3. 重建镜像
ssh -p 222 opc2_uname@100.109.57.26 "cd /opt/cc-infra && docker compose build hm40006"
# → cc-infra-hm40006 Built ✓

# 4. 重新部署 (force-recreate)
ssh -p 222 opc2_uname@100.109.57.26 "cd /opt/cc-infra && docker compose up -d --force-recreate hm40006"
# → Container hm40006 Recreated → Started ✓

# 5. 验证环境变量
docker exec hm40006 env | grep -E "UPSTREAM_TIMEOUT|TIER_TIMEOUT_BUDGET|MIN_OUTBOUND"
# → UPSTREAM_TIMEOUT=60 ✓
# → TIER_TIMEOUT_BUDGET_S=109 ✓
# → MIN_OUTBOUND_INTERVAL_S=12.0 ✓

# 6. 健康检查
docker ps --format '{{.Names}} {{.Status}}' | grep hm40006
# → hm40006 Up 15 seconds (healthy) ✓
```

## 预期效果

- **UPSTREAM_TIMEOUT 58→60**: 预计deepseek NVCFPexecTimeout减少~15-20个/30min（55.7-60s区间不再截断）。deepseek成功率提升~1.5-2%。
- **TIER_TIMEOUT_BUDGET 107→109**: 第二key有效时间从47s→49s（基于UPSTREAM=60, RESERVE=3, ~8s糖set）。减少budget耗尽时的kimi fallback ~5-10次/30min。
- **MIN_OUTBOUND 11→12**: 单key first-attempt延迟+1s。整体请求间距增大~9%。对429循环有微小正面效果（函数级不可修复，但更慢的request rate=更少的429触发频率）。
- **综合**: 预计成功率 99.0%→99.2%, kimi回退比例减少, deepseek timeout减少。

## 观察项

1. **kimi avg 88.8s**: 41个请求路由到kimi tier（3.3%总成功）。kimi tier极慢，应作为最后防线。增强deepseek tier（更高UPSTREAM+BUDGET）是减少kimi触发的关键。
2. **SSLEOFError持续增长**: R27=0→R29=52→R30=66。集中在port 7895-7896（k1,k2,k3）。mihomo代理端口SSL质量波动，但SSL-RETRY机制有效吸收。如果持续恶化需调查mihomo健康。
3. **deepseek max耗时异常**: k3 max=173,756ms(~174s), k0 max=121,763ms。这些极端值远超UPSTREAM_TIMEOUT，可能是streaming场景下TTFB前的极长等待。需确认是否是streaming行为。
4. **429均匀分布稳定**: 每个key ~540次429/30min，趋势无变化。函数级rate limit不可修复。
5. **下次方向**: 
   - 如果deepseek timeout减少至<100/30min，可考虑进一步UPSTREAM 60→62
   - 如果SSLEOFError增长至>100/30min，考虑调整KEY_COOLDOWN_S或调查mihomo端口
   - MIN_OUTBOUND可继续在后续轮次逐步提升至13-14s

## ⏳ 轮到HM2优化HM1  ← 脚本检测此标记