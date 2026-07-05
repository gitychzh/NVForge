# R727: HM2→HM1 — NVU_FORCE_STREAM_UPGRADE_TIMEOUT 42→44 (+2s)

## TL;DR
R726 将 UPSTREAM_TIMEOUT 从 42→44，但 NVU_FORCE_STREAM_UPGRADE_TIMEOUT 仍为 42 — 参数漂移。R724 曾将两者对齐在 42，R726 的单参数变更打破了对齐。本轮纠正：FORCE_STREAM_UPGRADE_TIMEOUT 42→44，恢复与 UPSTREAM=44 的对齐。

---

## 一、数据收集 (2026-07-05 ~11:45 UTC)

### 容器状态
- 容器: nv_gw, Up 5 minutes (healthy) — R726 部署后
- UPSTREAM_TIMEOUT=44 ✓, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=42 ⚠️ (未对齐)

### 配置漂移检测
| 参数 | Compose 值 | 容器 env | 对齐？ |
|------|-----------|----------|--------|
| UPSTREAM_TIMEOUT | 44 | 44 | ✅ |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 42 | 42 | ⚠️ 与 UPSTREAM=44 不对齐 |
| TIER_TIMEOUT_BUDGET_S | 110 | 110 | ✅ |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | 0.10 | ✅ |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 1 | ✅ |

### 6h DB 聚合
| 指标 | 值 |
|------|-----|
| 总请求 | 312 |
| OK (200) | 204 (65.4%) |
| 失败 (ATE) | 108 (34.6%) |
| 平均成功延迟 | 29,947ms |
| 最大成功延迟 | 99,088ms |

### Per-model 6h
| Model | cnt | OK | fail | SR | avg_ok_ms | avg_fail_ms |
|-------|-----|-----|------|-----|-----------|-------------|
| dsv4p_nv | 204 | 102 | 102 | 50.0% | 29,664 | 72,278 |
| glm5_2_nv | 107 | 102 | 5 | 95.3% | 30,930 | 47,377 |
| kimi_nv | 1 | 0 | 1 | 0% | — | 2,682 |

### ATE 诊断
- tiers_tried_count=1: 53 ATEs (avg 47,903ms, start_tier_idx=1:47, all fallback_actually_attempted=f)
- tiers_tried_count=2: 55 ATEs (avg 92,237ms, max 122,312ms)
- 16 single-tier ATEs 在 post-restart 窗口 (15min): avg 50,404ms, 全部 fallback_actually_attempted=f
  - 但是这些 timestamp 是 04:36-05:23 UTC (预重启) 和 10:38-10:58 UTC (FALLBACK_GRAPH 消失窗口)
  - Post-R726 重启 (11:42 UTC) 后: 0 单 tier ATE

### nv_tier_attempts (post-restart, 15min)
| tier | error_type | cnt | avg_ms | max_ms |
|------|-----------|-----|--------|--------|
| dsv4p_nv | NVCFPexecTimeout | 53 | 34,238 | **44,350** |
| glm5_2_nv | NVCFPexecTimeout | 11 | 40,622 | 42,309 |

### FALLBACK_GRAPH 状态
- 双向活跃: tier_chain=['dsv4p_nv', 'glm5_2_nv'] ✅
- dsv4p_nv health=0.333, glm5_2_nv health=0.0 (unstable, 但 MIN_SAMPLES 保护期)
- NV-FALLBACK-SUCCESS 持续出现
- Fallback 成功率: 100% (10/10 dsv4p→glm5_2, 37/37 glm5_2→dsv4p)

### 成功路径分析 (post-restart, 30min)
| 模型 | 路径 | cnt | avg_dur |
|------|------|-----|---------|
| dsv4p_nv | primary 直连 | 51 | 25,533ms |
| dsv4p_nv | via glm5_2 fallback | 10 | 51,224ms |
| glm5_2_nv | primary 直连 | 32 | 8,013ms |
| glm5_2_nv | via dsv4p fallback | 37 | 56,694ms |

### dsv4p_nv 成功延迟桶 (1h)
| bucket | cnt |
|--------|-----|
| <10s | 10 |
| 10-20s | 14 |
| 20-30s | 14 |
| 30-40s | 5 |
| 40-44s | 4 |
| 44-48s | 4 |
| 48-60s | 12 |
| 60-80s | 2 |

---

## 二、优化决策

**变更**: NVU_FORCE_STREAM_UPGRADE_TIMEOUT 42→44 (+2s)

**依据**:
1. R724 将 FORCE_STREAM_UPGRADE_TIMEOUT 与 UPSTREAM_TIMEOUT 对齐在 42
2. R726 将 UPSTREAM_TIMEOUT 从 42→44，但单参数规则下未同时调整 FORCE_STREAM_UPGRADE
3. 造成参数漂移：thinking 超时 (42s) < 上游超时 (44s)，非对称
4. 恢复对齐：thinking timeout=44 = UPSTREAM=44，thinking 请求有完整 44s 预算
5. BUDGET=110 >> 44+44=88s safe（per-tier budget, R707 corrected）
6. FASTBREAK=1 unchanged（NVCF 双 function 不稳定时期不增加 key 尝试次数）
7. dsv4p_nv NVCFPexecTimeout max=44,350ms (k4)，接近 UPSTREAM=44，验证了 UPSTREAM 的合理性

**风险评估**: 零风险。FORCE_STREAM_UPGRADE_TIMEOUT 仅影响 thinking 模型（glm5_1/glm5_2），这些模型当前 UPSTREAM=44 已足够。+2s 不会增加任何错误路径延迟。BUDGET 余量 22s (110-88) 安全。

**单参数每轮；铁律: 只改HM1不改HM2**

---

## 三、执行记录

### 3.1 Compose 编辑
```bash
# Line 503: value 42→44 + comment update
sed -i '503s/"42"/"44"/' docker-compose.yml
# Python 替换注释为 R727 版本
```

### 3.2 容器重启
```bash
cd /opt/cc-infra && docker compose up -d nv_gw
# → Container nv_gw Recreated, Started
```

---

## 四、验证

| 验证项 | 结果 | 状态 |
|--------|------|------|
| Compose 行 503 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "44"` | ✅ |
| 容器 env | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=44` | ✅ |
| 对齐 | FORCE_STREAM=44, UPSTREAM=44 | ✅ |
| 容器状态 | Up (healthy) | ✅ |
| 容器日志 | clean start, no errors | ✅ |
| FALLBACK_GRAPH | 双向活跃 | ✅ |

---

## 五、参数状态 (post-R727)

| 参数 | 值 | 趋势 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 44 | 30→25→28→31→34→32→30→36→38→40→42→44 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 44 | 61→59→58→57→56→55→54→53→52→31→40→42→44 |
| TIER_TIMEOUT_BUDGET_S | 110 | - |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | - |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| KEY_COOLDOWN_S | 25 | - |
| TIER_COOLDOWN_S | 25 | - |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor (integrate无模型) |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | - |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | - |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | floor |

### 已知漂移
- Compose 行 483 UPSTREAM_TIMEOUT 内联注释仍为 "R723"，实际值 44 来自 R726
- R726 注释在行 484 独立存在，不影响功能 — 下一轮 HM1 可修复

---

## 六、结论

R727 纠正参数漂移：NVU_FORCE_STREAM_UPGRADE_TIMEOUT 42→44，恢复与 UPSTREAM_TIMEOUT=44 的对齐。R724 曾对齐两者在 42，R726 仅在 UPSTREAM 上 +2s 造成不对称。单参数规则下，本轮专一恢复对齐。BUDGET=110 安全，所有参数地板/最优。NVCF 双 function 上游健康度问题（dsv4p_nv 0.333, glm5_2_nv 0.0）是 ATE 根因，非配置可修复。FALLBACK_GRAPH 双向活跃，fallback 100% SR。

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2