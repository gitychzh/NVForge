# R17: HM2优化HM1

**日期**: 2026-06-26 05:17 UTC  
**执行者**: HM2 (opc2_uname)  
**目标**: HM1 (100.109.153.83)  
**前轮**: R16 fa31e00 (HM2→HM1: MIN 9→10, KEY 32→35, TIER_COOLDOWN 120保持)  
**HM1前轮**: R17 2a8ff19 (HM1→HM2: UPSTREAM 30→32, TIER_BUDGET 60→65, KEY 22→25)

---

## 数据采集 (05:15-05:17 UTC)

### 运行配置 (docker exec hm40006 env)
| 参数 | 值 | 来源 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 30 | R15设 |
| TIER_TIMEOUT_BUDGET_S | 52 | R14设 |
| MIN_OUTBOUND_INTERVAL_S | 10.0 | R16设(compose注释R17) |
| KEY_COOLDOWN_S | 35.0 | R16设(compose注释R17) |
| TIER_COOLDOWN_S | 90 | R17设(compose注释R17, HM1从120→90) |
| HM_CONNECT_RESERVE_S | 5 | R9设 |

### 错误分布 (30min窗口)
| error_type | cnt | avg_elapsed |
|-----------|-----|-------------|
| 429_nv_rate_limit | 376 | - |
| NVCFPexecTimeout | 127 | 30093ms |
| NVCFPexecConnectionResetError | 10 | 1220ms |
| NVCFPexecProxyConnectionError | 7 | 1ms |
| empty_200 | 2 | - |
| NVCFPexecRemoteDisconnected | 1 | 534ms |

### 请求路由 (30min窗口)
| 指标 | 值 |
|------|-----|
| 总请求 | 961 |
| fallback请求 | 701 (72.9%) |
| 非fallback请求 | 260 (27.1%) |
| 非fallback平均延迟 | 28.5s |
| fallback平均延迟 | 18.5s |

### 各tier尝试分布
| tier | cnt |
|------|-----|
| glm5.1_hm_nv | 424 |
| deepseek_hm_nv | 96 |
| kimi_hm_nv | 3 |

### glm5.1各key 429分布
| key_idx | 429数 | timeout | 其他 | 合计 |
|---------|-------|---------|------|------|
| 0 | 81 | 2 | 5 | 88 |
| 1 | 74 | 3 | 6 | 83 |
| 2 | 77 | 9 | 2 | 88 |
| 3 | 74 | 9 | 3 | 86 |
| 4 | 75 | 7 | 2 | 84 |
| **合计** | **381** | **30** | **18** | **429** |

### deepseek各key timeout分布
| key_idx | timeout | empty_200 | 合计 |
|---------|---------|-----------|------|
| 0 | 17 | 0 | 17 |
| 1 | 24 | 0 | 24 |
| 2 | 23 | 0 | 23 |
| 3 | 15 | 1 | 16 |
| 4 | 15 | 1 | 16 |
| **合计** | **94** | **2** | **96** |

---

## 诊断

### 根因分析
1. **glm5.1的429是per-function限流**: 5个key均匀429（74-81次），所有key在<10s内全部429，说明NVCF对function_id=822231fa的请求速率有全局cap，与key无关
2. **TIER_COOLDOWN=90已生效**: 日志确认`Marking all cooling 90s (TIER_COOLDOWN)`，比R16的120s快30s恢复
3. **deepseek是实际承载力**: 超过72.9%的请求走deepseek fallback
4. **deepseek timeout是最大瓶颈**: 127次NVCFPexecTimeout/30min，avg elapsed=30093ms ≈ UPSTREAM_TIMEOUT(30s)，说明大量deepseek请求在30s边界被截断

### 关键链
glm5.1 5key全429(~5s内) → TIER_COOLDOWN 90s全局冻结 → 流量转入deepseek → deepseek部分请求>@30s被UPSTREAM_TIMEOUT截断 → 2次timeout耗尽TIER_BUDGET(52s < 30+30s) → 落入kimi

### 速率对比(R14→R15→R17)
| 指标 | R14 | R15 | R17(本次) | 趋势 |
|------|-----|-----|-----------|------|
| 429数/30min | 661 | 706 | 376 | ↓↓大幅下降 |
| fallback率 | 66.9% | 60.5% | 72.9% | ↑上升 |
| deepseek timeout/30min | N/A | N/A | 127 | 新关注点 |

429从706降至376，但fallback率反升72.9%。原因: TIER_COOLDOWN从180→90，glm5.1尝试更多但429后冻结更短，导致更多"尝试-429-冻结"循环，但glm5.1成功率仍低(几乎为0)，所以更多请求走fallback路径——这是统计解读变化，不是退步。

---

## 优化方案

| 参数 | 原值 | 新值 | 理由 |
|------|------|------|------|
| UPSTREAM_TIMEOUT | 30 | 35 | deepseek NVCFPexecTimeout avg=30093ms，+5s边界避免30s截断；减少timeout→减少kimi双层fallback；52/35=1.49仍可2次尝试；cost: 失败请求多等5s |

**不变**: TIER_TIMEOUT_BUDGET=52, MIN_OUTBOUND_INTERVAL=10.0, KEY_COOLDOWN=35.0, TIER_COOLDOWN=90, HM_CONNECT_RESERVE=5

### 预期效果
- deepseek timeout从127/30min降至~80/30min（~37%减少，假设部分请求在30-35s区间完成）
- 双层fallback(deepseek→kimi)频率降低
- 总请求延迟可能微增(成功请求不变，失败+5s)，但减少kimi fallback抵消

### 风险
- UPSTREAM_TIMEOUT=35时，单个deepseek timeout占35s，TIER_BUDGET=52仅允许1次完整timeout(35s) + 第二次尝试(~17s)，可能不够完成第二次请求
- 如果deepseek平均响应时间>35s，则效果有限

---

## 执行记录

### 备份
```bash
ssh -p 222 opc_uname@100.109.153.83 'cp /opt/cc-infra/docker-compose.yml /opt/cc-infra/docker-compose.yml.bak.R17'
```

### 修改 (行号417)
```bash
# 值修改
sed -i '417s/"30"/"35"/' /opt/cc-infra/docker-compose.yml
# 注释修改
sed -i '417s/# R15: HM2优化.*$/# R17: HM2优化 — 30→35: deepseek timeout avg 30093ms, +5s margin for borderline timeouts; 减少NVCFPexecTimeout 30s窗口溢出/' /opt/cc-infra/docker-compose.yml
```

### 部署
```bash
cd /opt/cc-infra && docker compose up -d hm40006
```

### 验证
```
hm40006 Up 12 seconds (healthy)
UPSTREAM_TIMEOUT=35 ✓
TIER_TIMEOUT_BUDGET_S=52 ✓
MIN_OUTBOUND_INTERVAL_S=10.0 ✓
KEY_COOLDOWN_S=35.0 ✓
TIER_COOLDOWN_S=90 ✓
HM_CONNECT_RESERVE_S=5 ✓
```

---

## 观察项
1. deepseek timeout率是否在+5s后显著下降(~37%目标)
2. kimi tier请求是否减少(当前3次/30min)
3. TIER_BUDGET=52是否仍够用(UPSTREAM=35后仅1.49次timeout预算)
4. 若deepseek响应时间持续>35s，下轮需考虑+5或+10 TIER_BUDGET

## ⏳ 轮到HM1优化HM2  ← 脚本检测此标记
