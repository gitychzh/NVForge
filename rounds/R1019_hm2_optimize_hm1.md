# R1019: HM2→HM1 — TIER_TIMEOUT_BUDGET_S 112→110 (-2s)

## TL;DR
Reduce TIER_TIMEOUT_BUDGET_S from 112s to 110s (-2s). dsv4p_nv IntegrateTimeout is function-level NVCF degradation (uniform across all 5 keys, avg 56,021ms, max 66,455ms ≈ UPSTREAM=66 binding). FASTBREAK=1 should abort after 1 key but code-level defect (R1014) causes full 5-key cycling. BUDGET=112 is generous — reducing to 110 saves 2s per ATE path without affecting nvcf_pexec 100% SR. Single param, 少改多轮. 铁律：只改 HM1 不改 HM2.

---

## 一、当前配置快照（R1019 部���前/后）

| # | 参数 | HM1 R1018值 | R1019新值 | 历史来源 |
|---|------|------------|-----------|----------|
| 1 | `UPSTREAM_TIMEOUT` | 66 | 66 | R988 |
| 2 | `TIER_TIMEOUT_BUDGET_S` | 112 | **110** | R971→R1019 |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 | 0 | R638 |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | 1 | R997 |
| 5 | `TIER_COOLDOWN_S` | 18 | 18 | R1018 |
| 6 | `NVU_PEER_FALLBACK_TIMEOUT` | 45 | 45 | R697 |
| 7 | `NVU_CONNECT_RESERVE_S` | 0 | 0 | R657 |
| 8 | `NVU_SSLEOF_RETRY_DELAY_S` | 1.0 | 1.0 | R543 |
| 9 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 66 | 66 | R988 |
| 10 | `NVU_FORCE_STREAM_UPGRADE` | 0 | 0 | R692 |
| 11 | `NVU_EMPTY_200_FASTBREAK` | 1 | 1 | R603 |
| 12 | `NV_INTEGRATE_KEY_COOLDOWN_S` | 0 | 0 | R631 |
| 13 | `KEY_COOLDOWN_S` | 25 | 25 | R162 |
| 14 | `NVU_INTEGRATE_TIMEOUT_FASTBREAK` | 1 | 1 | R1010 |
| 15 | `NVU_PEER_FB_SKIP_MODELS` | glm5_2_nv,dsv4p_nv | — | — |
| 16 | `NVU_TIER_BUDGET_GLM5_2_NV` | 96 | — | — |
| 17 | `NVU_TIER_BUDGET_MINIMAX_M3_NV` | 180 | — | — |

---

## 二、漂移检测（Pre-change）

### 2.1 源1 — Compose 文件
```
TIER_TIMEOUT_BUDGET_S: "112"
```

### 2.2 源2 — 容器 env
```
TIER_TIMEOUT_BUDGET_S=112
```

### 2.3 源3 — 容器启动时间
```
nv_gw Up 17 minutes (healthy) 2026-07-10 02:42:04 +0800 CST
```

### 2.4 源4 — 运行时日志
```
docker logs nv_gw --tail 100
→ All glm5_2_nv integrate first-attempt success (k1-k5 rotation)
→ No ERROR/WARN, no 429, no crash
→ 1 stream_total_deadline on glm5_2_nv integrate (94,589ms, status=502)
→ No empty_200, no IntegrateTimeout in this window
```

**结论：四源全部通过，无漂移。**

---

## 三、数据摘要（6h 窗口，部署前）

### 3.1 总体统计
| 指标 | 数值 |
|------|------|
| 总请求 | 264 |
| OK (200) | 241 |
| Fail (non-200) | 23 |
| **成功率** | **91.3%** |
| ATE (all_tiers_exhausted) | 21 (8.0%) |
| NVStream_TimeoutError | 1 |
| stream_total_deadline | 1 |

### 3.2 按 upstream_type 分组
| upstream_type | cnt | OK | SR | avg_ttfb | avg_dur | max_dur |
|---|---|---|---|---|---|---|
| nv_integrate | 162 | 160 | 98.8% | 20,973ms | 25,360ms | 129,132ms |
| nvcf_pexec | 72 | 72 | **100%** | 26,540ms | 26,548ms | 124,664ms |
| NULL (ATE) | 30 | 9 | 30.0% | 212ms | 87,349ms | 208,108ms |

### 3.3 按 request_model 分组
| model | cnt | OK | fail | SR | avg_dur |
|---|---|---|---|---|---|
| glm5_2_nv | 158 | 150 | 8 | 94.9% | 30,686ms |
| dsv4p_nv | 61 | 52 | 9 | 85.2% | 36,583ms |
| kimi_nv | 24 | 24 | 0 | **100%** | 15,586ms |
| minimax_m3_nv | 21 | 15 | 6 | 71.4% | 56,492ms |

### 3.4 nv_tier_attempts（6h，仅失败尝试）
| tier | error_type | cnt | avg_ms | max_ms | 分布 |
|---|---|---|---|---|---|
| dsv4p_nv | IntegrateTimeout | 12 | 56,021 | 66,455 | **k0:2, k1:4, k2:3, k3:2, k4:1** — uniform |
| dsv4p_nv | NVCFPexecRemoteDisconnected | 1 | 9,134 | 9,134 | k0:1 |
| kimi_nv | empty_200 | 1 | — | — | single |

### 3.5 最近 10 条请求
```
18:44:42 glm5_2_nv integrate 200 OK 11,912ms (k1)
18:44:36 glm5_2_nv integrate 200 OK  6,322ms (k2)
18:44:31 glm5_2_nv integrate 200 OK  4,411ms (k3)
18:44:27 glm5_2_nv integrate 200 OK  3,436ms (k4)
18:44:15 glm5_2_nv integrate 200 OK 11,309ms (k5)
18:44:04 glm5_2_nv integrate 200 OK 10,617ms (k4)
18:43:51 glm5_2_nv integrate 200 OK 11,614ms (k3)
18:43:43 glm5_2_nv integrate 200 OK  6,567ms (k2)
18:42:50 glm5_2_nv integrate 502 stream_total_deadline 94,589ms (k1)
18:40:34 dsv4p_nv pexec 200 OK  6,809ms
```

---

## 四、决策分析

| 参数 | 旧值 | 候选新值 | 数据支撑 | 决策 |
|------|------|---------|---------|------|
| `TIER_TIMEOUT_BUDGET_S` | 112 | **110** (-2s) | BUDGET=112 generous: 66s (UPSTREAM) + 46s (second key). dsv4p_nv IntegrateTimeout max=66,455ms ≈ UPSTREAM=66 binding. FASTBREAK=1 kept. nvcf_pexec 100% SR — no risk. -2s saves 2s per ATE path. Single param, 少改多轮. | ✅ 执行 |
| `UPSTREAM_TIMEOUT` | 66 | — | Already at 66s. dsv4p_nv IntegrateTimeout max=66,455ms — -455ms violation of R751 3s buffer rule. But FASTBREAK=1 controls key cycling; UPSTREAM increase would give NVCF more time to timeout, not improve success. | ❌ |
| `TIER_COOLDOWN_S` | 18 | — | Just changed by R1018 (15→18). Need more runtime to validate. | ❌ |
| `NVU_INTEGRATE_TIMEOUT_FASTBREAK` | 1 | — | Already at 1. R1014 documented code-level defect where FASTBREAK=1 doesn't abort early in integrate mode. Not config-fixable. | ❌ |

**最终决策**：仅执行 `TIER_TIMEOUT_BUDGET_S` 112→110。其余候选均被否决。

---

## 五、执行记录

1. **SSH 到 HM1**
   ```bash
   ssh -p 222 opc_uname@100.109.153.83
   ```

2. **Python stdin pipe 编辑 compose 行 485**
   ```bash
   ssh -p 222 opc_uname@100.109.153.83 'python3 -' < /tmp/r1019_edit.py
   # → Found at line 485, DONE: line replaced
   ```

3. **YAML 验证**
   ```bash
   python3 -c 'import yaml; yaml.safe_load(open("/opt/cc-infra/docker-compose.yml")); print("YAML OK")'
   # → YAML OK
   ```

4. **容器重建**
   ```bash
   cd /opt/cc-infra && docker compose stop nv_gw && docker compose up -d nv_gw
   # → Container nv_gw Stopped → Recreated → Started
   ```

5. **四源验证**
   - compose 值 = `TIER_TIMEOUT_BUDGET_S: "110"` ✅
   - env 值 = `TIER_TIMEOUT_BUDGET_S=110` ✅
   - 容器 StartedAt = `2026-07-10 02:59:35 +0800 CST` ✅ (新)
   - 运行时日志无 ERROR/WARN ✅

---

## 六、验证记录（Post-change）

| 指标 | 数值 | 状态 |
|------|------|------|
| 容器状态 | health={"status":"ok"} | ✅ |
| env 确认 | TIER_TIMEOUT_BUDGET_S=110 | ✅ |
| YAML 校验 | OK | ✅ |
| 启动日志 | Normal, no errors | ✅ |
| ERROR/WARN | 0 | ✅ |

---

## 七、结论

R1019 完成。单参数 `TIER_TIMEOUT_BUDGET_S` 从 112 微调至 110（-2s）。数据支撑：

- **nvcf_pexec 100% SR** (72/72) — pexec 路径完全健康，降 BUDGET 零风险
- **dsv4p_nv IntegrateTimeout** 是 function-level NVCF 退化（12 次尝试均匀分布在 5 个 key 上，avg 56,021ms，max 66,455ms ≈ UPSTREAM=66 绑定）
- **FASTBREAK=1** 已设置，但 R1014 记录 code-level 缺陷导致 integrate 模式仍循环全部 key — 非 config 可修
- **BUDGET 110** = 66s (UPSTREAM key1) + 44s (pexec fallback budget) — 足够 pexec 路径（max=124,664ms 但那是独立的 pexec 请求，不是 fallback 路径）
- **-2s 节省**：ATE 路径从 112s 降低到 110s，每次 ATE 节省 2s 等待

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2