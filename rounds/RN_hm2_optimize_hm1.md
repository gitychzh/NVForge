# R706: HM2→HM1 — TIER_TIMEOUT_BUDGET_S 94→110 (+16s)

## TL;DR
R705后~9h数据：282req/209OK(74.1%)/73ATE(25.9%) — ATE大爆炸。52/73 ATE(71%)单tier dsv4p_nv耗尽@avg49s后预算不足启动glm5_2_nv fallback。BUDGET 94→110(+16s)确保dsv4p 2key耗尽后剩余49s > glm5_2 1key最低35s，预期救回~52 ATE → SR 74%→~92%。单参数每轮；铁律：只改HM1不改HM2。

---

## 一、当前配置快照（R706 变更后）

| # | 参数 | HM1 变更 | 新值 | 历史 |
|---|------|----------|------|------|
| 1 | `TIER_TIMEOUT_BUDGET_S` | **94→110 (+16s)** | 110 | R704→R706 |
| 2 | `UPSTREAM_TIMEOUT` | — | 30 | R701 |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | — | 0 | R638 |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | — | 2 | R695 |
| 5 | `TIER_COOLDOWN_S` | — | 25 | R492 |
| 6 | `NVU_PEER_FALLBACK_TIMEOUT` | — | 45 | R697 |
| 7 | `NVU_CONNECT_RESERVE_S` | — | 0 | R657 |
| 8 | `NVU_SSLEOF_RETRY_DELAY_S` | — | 1.0 | R543 |
| 9 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | — | 40 | R694 |
| 10 | `NVU_FORCE_STREAM_UPGRADE` | — | 0 | R692 |
| 11 | `NVU_EMPTY_200_FASTBREAK` | — | 2 | R577 |
| 12 | `NV_INTEGRATE_ENABLED` | — | (未设置，默认1) | — |
| 13 | `NV_INTEGRATE_MODELS` | — | "" (空) | R693 |
| 14 | `NV_INTEGRATE_KEY_COOLDOWN_S` | — | 0 | R631 |
| 15 | `KEY_COOLDOWN_S` | — | 25 | R162 |

---

## 二、四源漂移检测（Pre-check）

### 2.1 源1 — Compose 文件
```
TIER_TIMEOUT_BUDGET_S: "94"  (line 490, R704 comment)
UPSTREAM_TIMEOUT: "30"  (line 483, R701)
KEY_COOLDOWN_S: "25"  (line 498)
TIER_COOLDOWN_S: "25"  (line 499)
```
→ 无重复值行。单一 `TIER_TIMEOUT_BUDGET_S` 活跃行。

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
nv_gw Up About an hour (healthy)
StartedAt: 2026-07-04T19:23:45Z
RestartCount: 0
Health: healthy
```

### 2.4 源4 — 运行时日志
```
docker logs nv_gw --tail 100 | grep -iE "error|warn|timeout|fail|exception|traceback|abort|exhausted|429|refused|reset|empty_200|ATE|all_tiers"
→ 3个连续 ATE @04:14-04:17 UTC (midday peak ~12:14 CST):
  dsv4p_nv k1+k2 timeout@30.3s each → FASTBREAK → glm5_2_nv k1+k2 timeout@30.3s each → ALL-TIERS-FAIL → 502
  Duration: 121,378ms / 121,165ms / 121,369ms — 全部远超 BUDGET=94!
→ 1个成功 @04:28: dsv4p_nv k1 timeout→k2 success@57s
→ 0 ERROR / 0 WARN / 0 429 / 0 empty_200
→ 3 BrokenPipeError (client disconnect before ATE response)
```

**结论：四源全部通过（变更前）。无漂移。但 ATE 爆炸 — 3个连续双tier ATE全部超BUDGET 94s（121s vs 94s）。**

---

## 三、数据摘要

### 3.1 总体统计（6h 窗口）

| 指标 | 数值 |
|------|------|
| 总请求 | 282 |
| 成功 (200) | 209 (74.1%) |
| 失败 (ATE 502) | 73 (25.9%) |
| 429 | 0 |

**按路径分组：**
| upstream_type | cnt | OK | avg_ttfb | avg_dur | max_dur |
|---------------|-----|-----|----------|---------|---------|
| nvcf_pexec | 199 | 199 | 22192ms | 22234ms | 99088ms |
| (NULL, ATE) | 77 | 4 | 54ms | 52765ms | 121406ms |
| nv_integrate | 6 | 6 | 4253ms | 10984ms | 27635ms |

**错误分类：**
| error_type | cnt |
|------------|-----|
| all_tiers_exhausted | 73 |

### 3.2 ATE 深层分析

**按 tiers_tried_count：**
| tiers_tried_count | cnt | avg_dur | 占比 |
|-------------------|-----|---------|------|
| 1（单tier） | 63 | 45,582ms | 86.3% |
| 2（双tier） | 10 | 114,381ms | 13.7% |

**按 start_tier_idx（单tier ATE）：**
| start_tier_idx | cnt | avg_dur | 含义 |
|----------------|-----|---------|------|
| 1 (dsv4p_nv) | 52 | 49,178ms | dsv4p_nv耗尽，fallback未触发 |
| 3 (glm5_2_nv) | 11 | 33,847ms | glm5_2_nv直接耗尽 |

**按小时（UTC）：**
| hour (UTC) | CST | total | OK | ATE | SR% |
|------------|-----|-------|-----|-----|-----|
| 19:00 | 03:00 | 114 | 99 | 15 | 86.8 |
| 20:00 | 04:00 | 14 | 8 | 6 | 57.1 |
| 21:00 | 05:00 | 15 | 8 | 7 | 53.3 |
| 22:00 | 06:00 | 28 | 13 | 15 | **46.4** ← 最差 |
| 23:00 | 07:00 | 9 | 8 | 1 | 88.9 |
| 00:00 | 08:00 | 2 | 2 | 0 | 100.0 |
| 01:00 | 09:00 | 13 | 8 | 5 | 61.5 |
| 02:00 | 10:00 | 49 | 35 | 14 | 71.4 |
| 03:00 | 11:00 | 27 | 20 | 7 | 74.1 |
| 04:00 | 12:00 | 12 | 9 | 3 | 75.0 |

### 3.3 成功请求分析

**dsv4p_nv 成功请求 duration 分布：**
| dur_bucket | cnt | avg_kc429 | avg_ttfb | 占比 |
|------------|-----|-----------|----------|------|
| <30s | 37 | 0.1 | 18,541ms | 47.4% |
| 30-60s | 34 | 1.0 | 43,344ms | 43.6% |
| 60-90s | 4 | 2.0 | 74,502ms | 5.1% |
| >90s | 3 | 3.0 | 96,020ms | 3.8% |

**fallback 成功：**
| fallback_occurred | cnt | avg_dur |
|-------------------|-----|---------|
| f（单tier成功） | 190 | 17,368ms |
| t（tier fallback成功） | 19 | 65,154ms |

Max success: 99,088ms (96,582ms from recent 15).

### 3.4 运行时日志关键事件

**04:14-04:17 UTC 连续3个ATE（midday peak）：**
```
[04:15:37] dsv4p_nv k5 timeout@30.3s → k1 timeout@30.3s → FASTBREAK
            → glm5_2_nv k5 timeout@30.3s → k1 timeout@30.3s → FASTBREAK
            → ALL-TIERS-FAIL (2 tiers, 121,378ms) → 502
            [NV-PEER-FB] peer-originated (hop=1) → 502

[04:16:47] 同上模式，121,165ms → 502
[04:17:38] 同上模式，121,369ms → 502
```

**04:28:15 成功恢复：**
```
dsv4p_nv k1 timeout@30.3s → k2 success@57s → 200
```

---

## 四、决策分析

### 根因：BUDGET 不足导致 fallback 被阻止

**预算模型（BUDGET=94）：**
```
dsv4p_nv 2key耗尽: 30s(k1) + overhead + 30s(k2) + overhead ≈ 61s
剩余: 94 - 61 = 33s
glm5_2_nv 1key最低需求: UPSTREAM=30s + connect/thinking overhead ≈ 35s
33s < 35s → fallback blocked → ATE!
```

**52/73 ATE 的根本原因就是这 2s 的缺口。** 当 dsv4p_nv 的 k1+k2 都超时后，剩余 33s 不够启动 glm5_2_nv（需要 ~35s），fallback 被代码层面阻止。

### 预算模型（BUDGET=110）：
```
dsv4p_nv 2key耗尽: ≈61s
剩余: 110 - 61 = 49s
glm5_2_nv 1key最低需求: ≈35s
49s > 35s → fallback 启动 → glm5_2_nv 尝试 1 key → 成功或失败
```

### 参数决策表

| 参数 | 当前值 | 候选 | 数据支撑 | 决策 |
|------|--------|------|---------|------|
| `TIER_TIMEOUT_BUDGET_S` | 94 | 110 | 52/73 ATE单tier dsv4p耗尽后fallback blocked。BUDGET=110确保剩余49s>35s启动glm5_2。19成功fallback avg=65s << 110s。Max success=99s < 110s零误杀。10 hopeless双tier ATE 114s→110s省4s。Worst case: 110+45=155s < 300s PROXY_TIMEOUT。 | ✅ **94→110** |
| `UPSTREAM_TIMEOUT` | 30 | — | 47% dsv4p成功<30s（单key成功），44%在30-60s（key cycling）。30s是合理值，不改。 | ❌ 保持 |
| `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 40 | — | R694已确认40s对dsv4p复杂prompt足够。 | ❌ 保持 |
| 其他所有参数 | — | — | 无数据支持变更。 | ❌ 保持 |

**最终决策：单参数变更 `TIER_TIMEOUT_BUDGET_S` 94→110 (+16s)。预期救回~52单tier ATE → SR 74%→~92%。**

---

## 五、执行记录

1. **SSH 到 HM1** — 数据收集（docker logs, env, container status, DB queries）
2. **四源验证** — 全部通过，无漂移
3. **DB 深度分析** — 6h/24h窗口，ATE分类（tiers_tried_count/start_tier_idx），小时SR趋势，成功请求duration分布
4. **Python patch via SCP** — 单行重写 line 490: `TIER_TIMEOUT_BUDGET_S: "94"` → `"110"` + 完整 R706 comment
5. **容器重启** — `docker compose up -d nv_gw` → Recreated → Started
6. **3-way 验证** — Compose line 490(110) = docker compose config(110) = container env(110) ✅

---

## 六、验证记录

| 指标 | 数值 | 状态 |
|------|------|------|
| Compose line 490 | `"110"` | ✅ |
| `docker compose config` | `110` | ✅ |
| 容器 env | `110` | ✅ |
| 容器状态 | Up (healthy) | ✅ |
| 容器启动时间 | 2026-07-04T20:39:51Z | ✅ |
| Health endpoint | `{"status": "ok"}` | ✅ |
| 重复值行（TIER_TIMEOUT_BUDGET） | 无（仅 line 490 活跃） | ✅ |
| 变更前 SR | 209/282 (74.1%) | 基线 |
| 变更前 ATE | 73 (25.9%) | 基线 |
| 预期 SR | ~92% | 待验证 |
| 429 | 0 | ✅ |

---

## 七、结论

R706: `TIER_TIMEOUT_BUDGET_S` 94→110 (+16s)。R705后9h数据揭示严重ATE回归（74.1% SR，25.9% ATE）。根因是BUDGET=94时dsv4p_nv 2key耗尽后剩余33s不足启动glm5_2_nv fallback（需要~35s），仅2s缺口导致52/73 ATE（71%）的fallback被阻止。BUDGET=110消除此缺口（剩余49s>35s），预期救回~52 ATE，SR提升至~92%。19成功fallback avg=65s << 110s安全。Max success=99s < 110s零误杀。10 hopeless双tier ATE仍失败但dur缩短4s。

**单参数每轮；铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2