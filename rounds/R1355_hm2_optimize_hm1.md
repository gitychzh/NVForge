# R1355: HM2→HM1 — NOP (false trigger, R1000 settling, 零可修故障, 515th chain of R1133)

## TL;DR
NOP. 6h: 83req/70OK 84.3%SR. dsv4p_nv pexec 100%SR(48/48), 6 ATE all PRE-RESTART (before 11:29 UTC). Post-restart 3/3 OK. glm5_2_nv 7 zombie_empty_completion code-level. 0 tier_attempts 0 fallback. All params floor/optimal. R1000 NVU_TIER_BUDGET_DSV4P_NV 82→94 needs settling. 铁律:只改HM1不改HM2.

---

## 一、当前配置快照（R1355 部署前）

| # | 参数 | HM1 值 | 历史来源 |
|---|------|--------|----------|
| 1 | `UPSTREAM_TIMEOUT` | 66 | R988 |
| 2 | `TIER_TIMEOUT_BUDGET_S` | 205 | R1286 |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 | R638 |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | R997 |
| 5 | `TIER_COOLDOWN_S` | 15 | R1103 |
| 6 | `NVU_PEER_FALLBACK_TIMEOUT` | 66 | R697 |
| 7 | `NVU_CONNECT_RESERVE_S` | 0 | R657 |
| 8 | `NVU_SSLEOF_RETRY_DELAY_S` | 1.0 | R543 |
| 9 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 66 | R988 |
| 10 | `NVU_FORCE_STREAM_UPGRADE` | 0 | R692 |
| 11 | `NVU_EMPTY_200_FASTBREAK` | 2 | R1031 |
| 12 | `NV_INTEGRATE_KEY_COOLDOWN_S` | 0 | R631 |
| 13 | `KEY_COOLDOWN_S` | 25 | R162 |
| 14 | `NVU_INTEGRATE_TIMEOUT_FASTBREAK` | 1 | R1010 |
| 15 | `NVU_PEER_FB_SKIP_MODELS` | "" | R1000 |
| 16 | `NVU_TIER_BUDGET_GLM5_2_NV` | 96 | — |
| 17 | `NVU_TIER_BUDGET_MINIMAX_M3_NV` | 100 | R1035 |
| 18 | `NVU_TIER_BUDGET_DSV4P_NV` | 94 | R1000 |
| 19 | `NVU_STREAM_TOTAL_DEADLINE_S` | 42 | R839 |
| 20 | `NVU_MS_GW_FALLBACK_TIMEOUT` | 195 | R1286 |
| 21 | `NV_INTEGRATE_MODELS` | glm5_2_nv | R838b |

---

## 二、漂移检测（四源验证）

| 源 | 方法 | 结果 |
|----|------|------|
| 源1 — compose | `grep` /opt/cc-infra/docker-compose.yml | 全部参数与env一致 ✅ |
| 源2 — 容器 env | `docker exec nv_gw env` | 全部参数与compose一致 ✅ |
| 源3 — 容器启动时间 | `docker ps` | nv_gw Up 23 minutes (healthy) ✅ |
| 源4 — 运行时日志 | `docker logs nv_gw --tail 200` | 零 ERROR/WARN，3/3 NV-INTEGRATE-SUCCESS first-attempt ✅ |

**结论：四源全部通过，无漂移。**

---

## 三、数据摘要（6h 窗口）

### 3.1 总体统计
| 指标 | 数值 |
|------|------|
| 总请求 | 83 |
| OK (200) | 70 |
| Fail (non-200) | 13 |
| **成功率** | **84.3%** |
| tier_attempts | 0 |
| fallback_occurred | 0 |

### 3.2 按 upstream_type 分组
| upstream_type | cnt | OK | SR | avg_ttfb | avg_dur | max_dur |
|---|---|---|---|---|---|---|
| nvcf_pexec | 48 | 48 | **100%** | 20,934ms | 20,938ms | 64,362ms |
| nv_integrate | 29 | 22 | 75.9% | 12,437ms | 12,694ms | 39,654ms |
| NULL (ATE) | 6 | 0 | 0% | 820ms | 71,694ms | 72,032ms |

### 3.3 按 request_model 分组
| model | cnt | OK | fail | SR | avg_dur |
|---|---|---|---|---|---|
| dsv4p_nv | 54 | 48 | 6 | 88.9% | 26,577ms |
| glm5_2_nv | 29 | 22 | 7 | 75.9% | 12,694ms |

### 3.4 错误分类
| error_type | cnt | 归类 |
|---|---|---|
| zombie_empty_completion | 7 | code-level, NVCF content filter, not config-fixable |
| all_tiers_exhausted | 6 | all PRE-RESTART (before 11:29 UTC) |

### 3.5 每小时 SR
| hour (UTC) | total | ok | fail | sr_pct |
|---|---|---|---|---|
| 05:00 | 1 | 0 | 1 | 0.0% |
| 06:00 | 59 | 52 | 7 | 88.1% |
| 07:00 | 4 | 3 | 1 | 75.0% |
| 08:00 | 5 | 4 | 1 | 80.0% |
| 09:00 | 5 | 4 | 1 | 80.0% |
| 10:00 | 4 | 3 | 1 | 75.0% |
| 11:00 | 5 | 4 | 1 | 80.0% |

### 3.6 最近 10 条请求
```
11:33:46 glm5_2_nv integrate 200 OK  7,482ms k3 (NV-INTEGRATE-SUCCESS)
11:33:34 glm5_2_nv integrate 200 OK 11,324ms k2 (NV-INTEGRATE-SUCCESS)
11:33:20 glm5_2_nv integrate 200 OK 14,342ms k1 (NV-INTEGRATE-SUCCESS)
11:03:27 glm5_2_nv integrate 502 zombie_empty_completion 9,644ms
11:03:20 glm5_2_nv integrate 200 OK  7,170ms
10:33:31 glm5_2_nv integrate 200 OK  7,819ms
10:33:20 glm5_2_nv integrate 200 OK 11,237ms
10:03:36 glm5_2_nv integrate 502 zombie_empty_completion 5,261ms
10:03:20 glm5_2_nv integrate 200 OK 15,476ms
09:33:46 glm5_2_nv integrate 200 OK 10,916ms
```

### 3.7 nv_gw 日志 (tail 200)
- 全部 glm5_2_nv integrate，k1-k5 轮转，first-attempt success
- 零 NV-TIER-FAIL, 零 NV-EMPTY-FASTBREAK, 零 NV-TIMEOUT-FASTBREAK
- 零 NV-GLOBAL-COOLDOWN, 零 NV-MS-FB, 零 NV-PEER-FB
- 零 ERROR/WARN
- 零 zombie 日志条目（当前窗口）

---

## 四、决策分析

| 候选参数 | 决策 | 理由 |
|---------|------|------|
| 所有参数 | ❌ NOP | 全部 floor/optimal，零可修故障 |
| `NVU_TIER_BUDGET_DSV4P_NV` | ❌ 不调 | R1000 94 需要更多 runtime 验证 settle |
| `UPSTREAM_TIMEOUT` | ❌ 不调 | 66s 已验证安全，缓冲区 3.4s ≥ R751 3s 规则 |
| FASTBREAK 系列 | ❌ 不调 | 全部 floor=1，已验证稳定 |
| 任何 cooldown | ❌ 不调 | 全部 floor=0/15/25，零 key_cycle_429s |

**NOP 理由详解：**
1. **7 zombie_empty_completion** — glm5_2_nv integrate 返回 finish_reason=stop + 内容过短。NVCF 服务端 content filter 行为，非 proxy config 可修复。每次 integrate 首 key 成功（NV-INTEGRATE-SUCCESS），但流内容被 NVCF 截断 → zombie 检测注入 content_filter 错误 → 502 返回客户端。
2. **6 ATE** — 全部在容器重启前（11:29 UTC 之前）。Post-restart 3/3 OK，零错误。
3. **dsv4p_nv pexec 100% SR** (48/48) — pexec 路径完全健康，零风险。
4. **0 tier_attempts, 0 fallback** — 零 key 级失败，零 ms_gw/peer-fb 触发。系统自愈能力充分。
5. **全部参数 floor/optimal** — FASTBREAK=1（floor），cooldowns=0/15/25（floor），CONNECT_RESERVE=0（floor），MIN_INTERVAL=0（floor），FORCE_STREAM_UPGRADE=0（floor）。无任何可调参数。
6. **R1000 settling** — NVU_TIER_BUDGET_DSV4P_NV 82→94 需要更多 runtime 数据验证。当前 post-restart 窗口过短（23min），无法判断 94 是否 optimal。
7. **False trigger** — commit 8364dbe 是 HM2 自己的提交（"这是我提交的, 不触发"），非 HM1 新 commit。

**最终决策：零参数变更。NOP。**

---

## 五、结论

R1355 NOP 完成。系统 post-restart 完全健康（3/3 OK），零可修故障。全部 7 个 zombie 和 6 个 ATE 均为 code-level 或 pre-restart 问题，非 config 可修。全部参数 floor/optimal，无任何可调参数。R1000 budget 94 需要更多 runtime 验证。

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2