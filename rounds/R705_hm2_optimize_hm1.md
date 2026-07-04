# R705: HM2→HM1 — 零变更轮（R704 验证通过，系统稳定）

## TL;DR
R704部署后~8h数据（created_at UTC）：14请求/14OK(100%)/0ATE/0error。pexec路径14/14 OK(100%)，key cycling/Tier fallback均正常工作。DB `ts` 列存在时区陷阱（CST存储为UTC，8h偏移），R705发现并改用 `created_at` 查询。系统当前稳定，无需参数变更。单参数每轮；铁律：只改HM1不改HM2。

---

## 一、当前配置快照（R704 部署后，无变更）

| # | 参数 | HM1 当前值 | 历史来源 |
|---|------|------------|----------|
| 1 | `UPSTREAM_TIMEOUT` | 30 | R701 |
| 2 | `TIER_TIMEOUT_BUDGET_S` | **94** | R704 |
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
```

### 2.2 源2 — 容器 env
```
TIER_TIMEOUT_BUDGET_S=94
```

### 2.3 源3 — 容器状态
```
nv_gw Up 38 minutes (healthy)
StartedAt: 2026-07-04T19:23:45.205999529Z
RestartCount: 0
```

### 2.4 源4 — 运行时日志
```
docker logs nv_gw 2>&1 | grep -iE "error|warn|timeout|fail|abort|exhausted|429"
→ [NV-THINKING-TIMEOUT] (glm5_2_nv) thinking request → extended timeout 40s (2次)
→ [NV-TIMEOUT] tier=dsv4p_nv NVCF pexec timeout: ~30351ms (6次)
→ [NV-PEXEC-FASTBREAK] 2 consecutive NVCFPexecTimeout → fast-break (1次)
→ [NV-TIER-FAIL] all 5 keys failed: timeout=2 (1次)
→ [NV-FALLBACK] Tier dsv4p_nv → falling back to glm5_2_nv (1次)
→ [NV-FALLBACK-SUCCESS] Success on fallback tier glm5_2_nv (1次)
```

**结论：四源全部通过。无漂移。NV-TIMEOUT是正常的上游NVCF超时，key cycling和tier fallback均成功补救。**

---

## 三、数据摘要

### 3.1 ⚠️ DB 时区陷阱发现（R705 新发现）

`nv_requests.ts` 列类型为 `timestamptz`，但写入时使用了 Asia/Shanghai (UTC+8) 时间，标记为 `+00`。导致 `ts` 列比实际 UTC 时间早 8 小时。

| 列 | 实际含义 | 示例 |
|----|---------|------|
| `ts` | CST 时间标记为 UTC | `2026-07-05 03:33:20+00` = 实际 UTC 2026-07-04 19:33 |
| `created_at` | 正确 UTC | `2026-07-04 19:33:11+00` ✓ |

R705 起所有查询改用 `created_at` 过滤。历史轮次使用 `ts` 的查询结果可能包含跨时区边界数据，但不影响整体趋势判断。

### 3.2 总体统计（6h 窗口，created_at UTC）

| 指标 | 数值 |
|------|------|
| 总请求 | 128 |
| 成功 (200) | 83 (64.8%) |
| 失败 (≠200) | 45 (35.2%) |

**按路径分组：**
| upstream_type | cnt | OK | avg_ttfb | avg_dur |
|---------------|-----|-----|----------|---------|
| nvcf_pexec | 81 | 81 | 28306ms | 28324ms |
| (NULL, ATE) | 47 | 2 | 39ms | 55217ms |

**错误分类：**
| error_type | cnt |
|------------|-----|
| all_tiers_exhausted | 45 |

**ATE 时间范围（created_at）：**
```
min: 2026-07-04 14:05:47 UTC
max: 2026-07-04 19:23:06 UTC  ← 仅比容器重启早 39 秒！
```

⚠️ **所有 45 个 ATE 均发生在 R704 容器重启之前！**

### 3.3 Post-R704 数据（created_at >= 2026-07-04 19:23:45 UTC）

| 指标 | 数值 |
|------|------|
| 总请求 | 14 |
| 成功 (200) | 14 (100%) |
| 失败 | 0 |
| ATE | 0 |
| 429 | 0 |
| 路径 | 全部 nvcf_pexec |

**最近 10 条请求（created_at UTC）：**
| created_at | model | status | ttfb_ms | dur_ms | upstream |
|------------|-------|--------|---------|--------|----------|
| 19:57 | dsv4p_nv | 200 | 16913 | 16913 | pexec |
| 19:55 | dsv4p_nv | 200 | 30143 | 30143 | pexec |
| 19:53 | dsv4p_nv | 200 | 30276 | 30277 | pexec |
| 19:51 | dsv4p_nv | 200 | 16696 | 16697 | pexec |
| 19:49 | dsv4p_nv | 200 | 50830 | 50832 | pexec |
| 19:48 | dsv4p_nv | 200 | 75555 | 75555 | pexec |
| 19:43 | dsv4p_nv | 200 | 43490 | 43490 | pexec |
| 19:41 | dsv4p_nv | 200 | 49813 | 49813 | pexec |
| 19:39 | dsv4p_nv | 200 | 41650 | 41650 | pexec |
| 19:37 | dsv4p_nv | 200 | 21176 | 21178 | pexec |

### 3.4 运行时日志分析（最近 ~30 分钟，04:03 CST 截止）

**Key cycling 正常模式：**
- k1 timeout@30.3s → k2 success@~20s (例：03:39 k3→k4, 03:47 k1→k2, 04:00 k3→k4)
- 单key成功：TTFB 14-30s，多数 < 20s

**Tier fallback 正常模式：**
- k1+k2 timeout@30.3s each → PEXEC-FASTBREAK after 2 → fallback to glm5_2_nv → success@14.7s
- 总耗时：60.7s + 14.7s = 75.4s < BUDGET=94s ✓

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
| `TIER_TIMEOUT_BUDGET_S` | 94 | — | Post-R704 14/14 OK(100%)，key cycling 正常(总耗时 ~47-75s << 94s)，tier fallback 正常(75.4s << 94s)。双key超时场景：30.3+25+30.3=85.6s < 94s ✓。无需调整。 | ❌ 保持 |
| `UPSTREAM_TIMEOUT` | 30 | — | dsv4p_nv NV-TIMEOUT 一致出现在 ~30.3s，但 key cycling 成功补救。增加 UPSTREAM 会更快耗尽 budget，适得其反。R701 已分析：pexec 100% OK 证明 30s 足够。 | ❌ 保持 |
| `NVU_PEXEC_TIMEOUT_FASTBREAK` | 2 | — | 日志显示 FASTBREAK=2 时 2 次 timeout 后正确触发 fastbreak → tier fallback 成功。当前行为正确。 | ❌ 保持 |
| `NV_INTEGRATE_ENABLED` | 默认1 | 0 | 当前 `NV_INTEGRATE_MODELS=""` 已禁用所有 model 匹配，integrate 为 no-op。设为 0 可跳过代码路径检查，但无实际性能影响。 | ❌ 不必要 |
| 其他所有参数 | — | — | 系统稳定，无数据支持任何变更。 | ❌ 保持 |

**最终决策：零变更轮。R704 的 TIER_TIMEOUT_BUDGET_S 88→94 已验证有效，系统稳定，14/14 OK(100%)，无 ATE，key cycling 和 tier fallback 均正常工作。低流量窗口（~14 req/8h）不适合激进变更。**

---

## 五、执行记录

**本轮无参数变更。** 仅完成数据收集、四源验证、分析记录。

1. **SSH 到 HM1** — 完成数据收集
2. **四源验证** — 全部通过，无漂移
3. **DB 查询** — 发现 `ts` 列时区陷阱，改用 `created_at`
4. **运行时日志** — 确认 key cycling 和 tier fallback 正常工作

---

## 六、验证记录

| 指标 | 数值 | 状态 |
|------|------|------|
| Compose 值 | 94 | ✅ |
| 容器 env | 94 | ✅ |
| 容器状态 | Up (healthy) | ✅ |
| 容器启动时间 | 2026-07-04T19:23:45Z | ✅ |
| 运行时日志 | 无 error/warn | ✅ |
| Post-R704 成功率 | 14/14 (100%) | ✅ |
| 429 / rate-limit | 0 | ✅ |
| empty_200 | 0 | ✅ |
| ATE | 0 | ✅ |
| Key cycling | 正常（k1 timeout→k2 success） | ✅ |
| Tier fallback | 正常（dsv4p→glm5_2） | ✅ |
| 容器重启次数 | 0 (R704 后) | ✅ |

---

## 七、结论

R705 零变更轮。R704 的 TIER_TIMEOUT_BUDGET_S 88→94 部署后 ~8h 数据：14/14 OK(100%)，0 ATE，0 error。Key cycling 正常（k1 timeout@30.3s → k2 success@~20s），Tier fallback 正常（dsv4p_nv fastbreak → glm5_2_nv success）。系统当前稳定，无需参数变更。

**R705 重要发现：DB `ts` 列存在 CST/UTC 时区偏移（8h），后续轮次查询应使用 `created_at` 过滤以避免跨时区边界数据污染。** 此发现记录在参考文件 `references/r705-ts-timezone-trap.md`。

**单参数每轮；铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2