# RN: HM2→HM1 — 零变更轮（R705 验证通过，系统持续稳定）

## TL;DR
R705后~49min数据（created_at UTC）：18请求/18OK(100%)/0ATE/0error。pexec路径18/18 OK(100%)。3次tier fallback全部成功（dsv4p_nv→glm5_2_nv），key cycling和tier fallback均正常工作。系统当前稳定，无需参数变更。单参数每轮；铁律：只改HM1不改HM2。

---

## 一、当前配置快照（R705 后，无变更）

| # | 参数 | HM1 当前值 | 历史来源 |
|---|------|------------|----------|
| 1 | `UPSTREAM_TIMEOUT` | 30 | R701 |
| 2 | `TIER_TIMEOUT_BUDGET_S` | 94 | R704 |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 | R638 |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | 2 | R695 |
| 5 | `TIER_COOLDOWN_S` | 25 | R492 |
| 6 | `NVU_PEER_FALLBACK_TIMEOUT` | 45 | R697 |
| 7 | `NVU_CONNECT_RESERVE_S` | 0 | R657 |
| 8 | `NVU_SSLEOF_RETRY_DELAY_S` | 1.0 | R543 |
| 9 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 40 | R694 |
| 10 | `NVU_FORCE_STREAM_UPGRADE` | 0 | R692 |
| 11 | `NVU_EMPTY_200_FASTBREAK` | 2 | R577 |
| 12 | `NV_INTEGRATE_ENABLED` | (未设置，默认1) | — |
| 13 | `NV_INTEGRATE_MODELS` | "" (空) | R693 |
| 14 | `NV_INTEGRATE_KEY_COOLDOWN_S` | 0 | R631 |
| 15 | `KEY_COOLDOWN_S` | 25 | R162 |

---

## 二、四源漂移检测（Pre-check）

### 2.1 源1 — Compose 文件
```
TIER_TIMEOUT_BUDGET_S: "94"  (line 490)
UPSTREAM_TIMEOUT: "30"  (line 483)
KEY_COOLDOWN_S: "25"  (line 498)
TIER_COOLDOWN_S: "25"  (line 499)
```

### 2.2 源2 — 容器 env
```
TIER_TIMEOUT_BUDGET_S=94
UPSTREAM_TIMEOUT=30
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=25
NVU_PEXEC_TIMEOUT_FASTBREAK=2
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=40
NVU_FORCE_STREAM_UPGRADE=0
NVU_EMPTY_200_FASTBREAK=2
NV_INTEGRATE_MODELS=
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_CONNECT_RESERVE_S=0
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_PEER_FALLBACK_TIMEOUT=45
```

### 2.3 源3 — 容器状态
```
nv_gw Up 48 minutes (healthy)
StartedAt: 2026-07-04T19:23:45.205999529Z
RestartCount: 0
Health: healthy
```

### 2.4 源4 — 运行时日志
```
docker logs nv_gw --tail 100 | grep -iE "error|warn|timeout|fail|exception|traceback|abort|exhausted|429|refused|reset"
→ [NV-TIMEOUT] tier=dsv4p_nv k3 pexec timeout: ~30.4s (3次)
→ [NV-TIMEOUT] tier=dsv4p_nv k1 pexec timeout: ~30.4s (1次)
→ [NV-TIMEOUT] tier=dsv4p_nv k2 pexec timeout: ~30.4s (1次)
→ [NV-TIMEOUT] tier=dsv4p_nv k4 pexec timeout: ~30.4s (1次)
→ [NV-TIMEOUT] tier=dsv4p_nv k5 pexec timeout: ~30.4s (1次)
→ [NV-TIMEOUT] tier=glm5_2_nv k2 pexec timeout: ~30.4s (1次，fallback第2次尝试)
→ [NV-PEXEC-FASTBREAK] 2 consecutive NVCFPexecTimeout → fast-break (3次)
→ [NV-TIER-FAIL] tier=dsv4p_nv all 5 keys failed: timeout=2 (3次)
→ [NV-FALLBACK] Tier dsv4p_nv → falling back to glm5_2_nv (3次)
→ [NV-FALLBACK-SUCCESS] Success on fallback tier glm5_2_nv (3次)
→ [NV-THINKING-TIMEOUT] (glm5_2_nv) thinking request → extended timeout 40s (1次)
```

**结论：四源全部通过。无漂移。3次tier fallback全部成功，key cycling和tier fallback均正常工作。0 ERROR/WARN/429/empty_200/ATE。**

---

## 三、数据摘要

### 3.1 总体统计（6h 窗口，created_at UTC）

| 指标 | 数值 |
|------|------|
| 总请求 | 125 |
| 成功 (200) | 90 (72.0%) |
| 失败 (≠200) | 35 (28.0%) |

**按路径分组：**
| upstream_type | cnt | OK | avg_ttfb | avg_dur | max_dur |
|---------------|-----|-----|----------|---------|---------|
| nvcf_pexec | 88 | 88 | 29602ms | 29619ms | 99088ms |
| (NULL, ATE) | 37 | 2 | 39ms | 58512ms | 121406ms |

**错误分类：**
| error_type | cnt |
|------------|-----|
| all_tiers_exhausted | 35 |

**ATE 时间范围（created_at）：**
```
min: 2026-07-04 14:19:29 UTC
max: 2026-07-04 19:23:06 UTC  ← 比容器重启早 39 秒！
```

⚠️ **所有 35 个 ATE 均发生在 R704 容器重启之前！**

### 3.2 Post-R704 数据（created_at >= 2026-07-04 19:23:45 UTC）

| 指标 | 数值 |
|------|------|
| 总请求 | 18 |
| 成功 (200) | 18 (100%) |
| 失败 | 0 |
| ATE | 0 |
| 429 | 0 |
| 路径 | 全部 nvcf_pexec |
| avg_ttfb | 38833ms |
| avg_dur | 38833ms |
| max_dur | 96582ms |

**最近 15 条请求（created_at UTC）：**
| created_at | model | status | ttfb_ms | dur_ms | key_cycle | upstream |
|------------|-------|--------|---------|--------|-----------|----------|
| 20:08 | dsv4p_nv | 200 | 74244 | 74244 | 2 | pexec |
| 20:07 | dsv4p_nv | 200 | 71481 | 71482 | 2 | pexec |
| 20:06 | dsv4p_nv | 200 | 96582 | 96582 | 3 | pexec |
| 20:03 | dsv4p_nv | 200 | 14713 | 14714 | 0 | pexec |
| 20:03 | glm5_2_nv | 200 | 3025 | 3025 | 0 | pexec |
| 20:01 | dsv4p_nv | 200 | 47234 | 47234 | 1 | pexec |
| 19:57 | dsv4p_nv | 200 | 16913 | 16913 | 0 | pexec |
| 19:55 | dsv4p_nv | 200 | 30143 | 30143 | 0 | pexec |
| 19:53 | dsv4p_nv | 200 | 30276 | 30277 | 0 | pexec |
| 19:51 | dsv4p_nv | 200 | 16696 | 16697 | 0 | pexec |
| 19:49 | dsv4p_nv | 200 | 50830 | 50832 | 1 | pexec |
| 19:48 | dsv4p_nv | 200 | 75555 | 75555 | 2 | pexec |
| 19:43 | dsv4p_nv | 200 | 43490 | 43490 | 1 | pexec |
| 19:41 | dsv4p_nv | 200 | 49813 | 49813 | 1 | pexec |
| 19:39 | dsv4p_nv | 200 | 41650 | 41650 | 1 | pexec |

### 3.3 运行时日志分析（~49 min，04:10 CST 截止）

**Key cycling 正常模式：**
- k1 timeout @30.3s → k2 success @~20s 或 k1 success @14-30s
- 单key成功：TTFB 14-50s，多数 < 30s
- 示例：03:39 k3 timeout→k4 success@42s, 03:43 k4 timeout→k1 success@43s, 03:49 k3 timeout→k4 success@30s

**Tier fallback 正常模式（3次，全部成功）：**
- 03:48: k1+k2 timeout@30.3s each → FASTBREAK → glm5_2_nv k2 success@14.7s → Total 75.4s < BUDGET=94s ✓
- 04:05: k1+k2 timeout@30.3s each → FASTBREAK → glm5_2_nv k2 timeout→k3 success@35.8s → Total 96.5s ≈ BUDGET=94s (略超2.5s，但成功)
- 04:07: k3+k4 timeout@30.3s each → FASTBREAK → glm5_2_nv k? success@10.7s → Total 72.4s < BUDGET=94s ✓

**Dynamic health 正常：**
- dsv4p_nv 健康度在 fallback 之间从 0.833 恢复到 0.923
- 系统在 pexec 短暂不可用时自动降级→恢复

**无异常：**
- 0 ERROR / 0 WARN
- 0 429 / 0 empty_200
- 0 ABORT-NO-FALLBACK
- 0 ATE
- 0 peer fallback 触发（本地 tier fallback 已足够）

---

## 四、决策分析

| 参数 | 当前值 | 候选 | 数据支撑 | 决策 |
|------|--------|------|---------|------|
| `TIER_TIMEOUT_BUDGET_S` | 94 | — | Post-R704 18/18 OK(100%)。3次tier fallback总耗时: 75.4s, 96.5s, 72.4s。96.5s略超94s但仍在容忍范围且成功。正常key cycling: 1-2key总耗时~47-61s << 94s。双key超时场景: 30.3+25+30.3=85.6s < 94s ✓。无需调整。 | ❌ 保持 |
| `UPSTREAM_TIMEOUT` | 30 | — | dsv4p_nv NV-TIMEOUT一致出现在~30.3s，key cycling成功补救。pexec 18/18 OK(100%)证明30s足够。glm5_2_nv avg_ttfb=3s << 30s不受影响。 | ❌ 保持 |
| `NVU_PEXEC_TIMEOUT_FASTBREAK` | 2 | — | 3次FASTBREAK=2后正确触发→tier fallback成功。当前行为正确。 | ❌ 保持 |
| `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 40 | — | 1次glm5_2 thinking请求触发40s扩展，正常行为。R694已确认40s对dsv4p复杂prompt足够。 | ❌ 保持 |
| 其他所有参数 | — | — | 系统稳定，无数据支持任何变更。 | ❌ 保持 |

**最终决策：零变更轮。R704的TIER_TIMEOUT_BUDGET_S 88→94已验证有效，系统持续稳定。Post-R704 18/18 OK(100%)，0 ATE，0 error。3次tier fallback全部成功，key cycling和动态健康度恢复均正常工作。低流量窗口（~18 req/49min）不适合激进变更。唯一值得注意：04:05的fallback总耗时96.5s略超BUDGET=94s（超2.5s），但请求仍然成功，是偶发边缘case。下一轮如果流量更高且fallback超时更频繁，可考虑BUDGET 94→96。**

---

## 五、执行记录

**本轮无参数变更。** 仅完成数据收集、四源验证、分析记录。

1. **SSH 到 HM1** — 完成数据收集（docker logs, env, container status）
2. **四源验证** — 全部通过，无漂移
3. **DB 查询** — 使用 `created_at` 过滤（延续R705时区陷阱修复），6h + Post-R704 双窗口分析
4. **运行时日志** — 确认 key cycling、tier fallback、dynamic health 均正常工作

---

## 六、验证记录

| 指标 | 数值 | 状态 |
|------|------|------|
| Compose 值 | 94 | ✅ |
| 容器 env | 94 | ✅ |
| 容器状态 | Up (healthy) | ✅ |
| 容器启动时间 | 2026-07-04T19:23:45Z | ✅ |
| 运行时日志 | 无 error/warn | ✅ |
| Post-R704 成功率 | 18/18 (100%) | ✅ |
| 429 / rate-limit | 0 | ✅ |
| empty_200 | 0 | ✅ |
| ATE | 0 | ✅ |
| Key cycling | 正常（k1 timeout→k2 success） | ✅ |
| Tier fallback | 正常（dsv4p→glm5_2, 3/3成功） | ✅ |
| Dynamic health | 正常（0.833→0.923恢复） | ✅ |
| 容器重启次数 | 0 (R704 后) | ✅ |

---

## 七、结论

RN 零变更轮。R704的TIER_TIMEOUT_BUDGET_S 88→94部署后~49min数据：18/18 OK(100%)，0 ATE，0 error。3次tier fallback全部成功（dsv4p→glm5_2），dynamic health正确恢复。系统当前稳定，无需参数变更。

**观察项：** 04:05的fallback总耗时96.5s略超BUDGET=94s（+2.5s），但请求仍然成功。若后续流量更高且fallback超时更频繁，可考虑BUDGET微调94→96。

**单参数每轮；铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2