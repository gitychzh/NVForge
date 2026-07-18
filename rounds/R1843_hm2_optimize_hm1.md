# R1843: HM2→HM1 — NOP (false trigger, 零可配置修复故障)

## TL;DR
NOP — false trigger. 6h: 45req/36OK(80%SR)/9fail. dsv4p 15/15(100%), glm5_2 21/26(80.8%) 5 zombie NVCF content-filter, kimi 0/4 4 ATE NVCF-degraded. All failures NVCF-side, zero config-fixable. All params floor/optimal. 单参数每轮; 铁律:只改HM1不改HM2.

---

## 一、当前配置快照（R1843 部署前）

| # | 参数 | HM1 当前值 | 历史来源 |
|---|------|------------|----------|
| 1 | `UPSTREAM_TIMEOUT` | 51 | R1839: 53→51 |
| 2 | `TIER_TIMEOUT_BUDGET_S` | 178 | R1840: 180→178 |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 | R638: floor |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | R1707: 2→1, floor |
| 5 | `KEY_COOLDOWN_S` | 60 | R1833: 61→60 |
| 6 | `TIER_COOLDOWN_S` | 60 | R1833: 61→60 |
| 7 | `NVU_PEER_FALLBACK_TIMEOUT` | 122 | R1744: 124→122 |
| 8 | `NVU_CONNECT_RESERVE_S` | 0 | R657: floor |
| 9 | `NVU_SSLEOF_RETRY_DELAY_S` | 0.1 | R1823: 0.2→0.1 |
| 10 | `NVU_FORCE_STREAM_UPGRADE` | 0 | R692: 禁用 |
| 11 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 66 | R988: sync with UPSTREAM=66 |
| 12 | `NVU_EMPTY_200_FASTBREAK` | 1 | R1694: 3→1, floor |
| 13 | `NV_INTEGRATE_MODELS` | "" | R1421: 移除 |
| 14 | `NV_INTEGRATE_KEY_COOLDOWN_S` | 0 | R631: floor |
| 15 | `NVU_STREAM_FIRST_BYTE_DEADLINE_S` | 15 | R1802: 17→15 |
| 16 | `NVU_STREAM_TOTAL_DEADLINE_S` | 25 | R1742: 30→25 |
| 17 | `NVU_TIER_BUDGET_DSV4P_NV` | 39 | R1835: 41→39 |
| 18 | `NVU_TIER_BUDGET_GLM5_2_NV` | 60 | R1783: 120→60 |
| 19 | `NVU_BIG_INPUT_COOLDOWN_S` | 7200 | R1745: 5400→7200 |
| 20 | `NVU_BIG_INPUT_FAIL_N` | 1 | R1713: 3→1, floor |
| 21 | `FALLBACK_HEALTH_THRESHOLD` | 0.05 | same |

---

## 二、漂移检测（Pre-change）

### 2.1 源1 — Compose 文件
```
UPSTREAM_TIMEOUT: "51"  (line 488)
TIER_TIMEOUT_BUDGET_S: "178" (line 490)
KEY_COOLDOWN_S: "60" (line 500)
TIER_COOLDOWN_S: "60" (line 505)
NVU_PEER_FALLBACK_TIMEOUT: "122" (env line)
NVU_SSLEOF_RETRY_DELAY_S: "0.1" (active line)
...
```

### 2.2 源2 — 容器 env
```
UPSTREAM_TIMEOUT=51
TIER_TIMEOUT_BUDGET_S=178
KEY_COOLDOWN_S=60
TIER_COOLDOWN_S=60
NVU_PEER_FALLBACK_TIMEOUT=122
NVU_SSLEOF_RETRY_DELAY_S=0.1
NVU_STREAM_FIRST_BYTE_DEADLINE_S=15
NVU_STREAM_TOTAL_DEADLINE_S=25
NVU_TIER_BUDGET_DSV4P_NV=39
NVU_TIER_BUDGET_GLM5_2_NV=60
```

### 2.3 源3 — 容器启动时间
```
StartedAt: 2026-07-18T22:25:22Z (R1840 deploy)
```

### 2.4 源4 — 运行时日志
```
docker logs nv_gw --tail 100: 4 zombie_empty_completion glm5_2_nv
(NVCF content-filter, all 4 keys tried, ~2.5-3.6s each)
No ERROR/WARN except zombie content-filter SSE chunks
```

**结论：四源全部通过。无漂移。**

---

## 三、数据摘要（部署前窗口）

### 3.1 30min 窗口
- **4 req / 0 OK / 4 fail (0% SR)** — 全 zombie_empty_completion glm5_2_nv
- 4 zombie: NVCF content-filter, pexec_us_rr mode, all 4 keys ~2.5-3.6s each
- 容器刚重启 12min 前 (R1840 deploy)，流量极少

### 3.2 1h 窗口
- **10 req / 5 OK (50% SR) / 5 fail**
- dsv4p_nv: 3/3 OK, avg=9381ms, max=14501ms
- glm5_2_nv: 2/7 OK (28.6%), 5 zombie

### 3.3 6h 窗口
- **45 req / 36 OK (80.0% SR) / 9 fail**
- dsv4p_nv: 15/15 OK (100%), avg=13897ms, max=40603ms
- glm5_2_nv: 21/26 OK (80.8%), 5 zombie (NVCF content-filter, avg=3054ms, max=3644ms)
- kimi_nv: 0/4 OK, 4 ATE (NVCF-degraded, avg=430ms, max=1715ms)
- All 45 req had key_cycle_429s ≥ 1 (normal rotation, not 429 errors)
- No 429 errors, no SSLEOF, no pexec timeout, no peer fallback

### 3.4 错误分类
| 错误类型 | 模型 | 数量 | 根因 | 可配置修复? |
|----------|------|------|------|------------|
| zombie_empty_completion | glm5_2_nv | 5 | NVCF content-filter | ❌ NVCF-side |
| all_tiers_exhausted | kimi_nv | 4 | NVCF function degraded | ❌ NVCF-side |

---

## 四、决策分析

| 参数 | 旧值 | 候选新值 | 数据支撑 | 决策 |
|------|------|---------|---------|------|
| UPSTREAM_TIMEOUT | 51 | 49 | dsv4p max_ok=40.6s, margin=10.4s>3s. 但 kimi ATE 非 config-fixable. | ❌ 无收益 |
| TIER_TIMEOUT_BUDGET_S | 178 | 176 | UPSTREAM=51+PEER=122=173<176 (3s margin). 但 kimi ATE 非 config-fixable. | ❌ 无收益 |
| NVU_PEER_FALLBACK_TIMEOUT | 122 | 120 | 51+120=171<178 (7s margin). 但 peer fb 从未触发. | ❌ 无收益 |
| KEY_COOLDOWN_S | 60 | 58 | 60=NVCF boundary. 降58会跌破边界. 零429问题无降理由. | ❌ 跌破边界 |
| NVU_SSLEOF_RETRY_DELAY_S | 0.1 | 0.05 | 6h 零 SSLEOF. 降0.05无实际收益. | ❌ 无收益 |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 15 | 13 | OK p99 TTFB=10.8s. 但 zombie 非 deadline 可修. | ❌ 无收益 |
| 其他参数 | — | — | 全部 floor/optimal | ❌ |

**最终决策**：NOP — false trigger. 所有错误均为 NVCF-side (zombie content-filter + kimi function degradation)，零可配置修复故障。所有参数已至 floor 或 optimal。硬改违反铁律。

---

## 五、执行记录

本轮无执行操作。0 restart 0 中断。仅数据采集 + 回合记录。

---

## 六、结论

R1843 完成。NOP — false trigger。6h 窗口 SR=80% (36/45)，所有 9 条失败均为 NVCF 侧故障 (5 zombie NVCF content-filter + 4 kimi ATE NVCF function degradation)，零可配置修复故障。dsv4p_nv 15/15 (100%) 持续健康。所有参数 floor/optimal，无 config 可改依据。硬改违反铁律。

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2
