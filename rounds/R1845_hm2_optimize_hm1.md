# R1845: HM2→HM1 — NOP (zero config-fixable, 全 NVCF 侧 zombie)

## TL;DR
NOP — 零可配置修复故障. 6h: 40req/35OK(87.5%SR)/5fail. dsv4p 14/14(100%), glm5_2 21/26(80.8%) 5 zombie_empty_completion 全 NVCF content-filter. 零 ATE 零 peer-fb 零 config-fixable. 所有参数 floor/optimal. 单参数每轮; 铁律:只改HM1不改HM2.

---

## 一、当前配置快照（R1845 分析前）

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
| 18 | `NVU_TIER_BUDGET_GLM5_2_NV` | 60 | R1831: 65→60 |
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
NVU_PEER_FALLBACK_TIMEOUT: "122" (line 516)
NVU_SSLEOF_RETRY_DELAY_S: "0.1" (line 621)
...
```

### 2.2 源2 — 容器 env
```
UPSTREAM_TIMEOUT=51
TIER_TIMEOUT_BUDGET_S=178
KEY_COOLDOWN_S=60
TIER_COOLDOWN_S=60
NVU_PEER_FALLBACK_TIMEOUT=122
NVU_EMPTY_200_FASTBREAK=1
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_SSLEOF_RETRY_DELAY_S=0.1
NVU_TIER_BUDGET_DSV4P_NV=39
NVU_TIER_BUDGET_GLM5_2_NV=60
NVU_BIG_INPUT_COOLDOWN_S=7200
NVU_BIG_INPUT_FAIL_N=1
...
```

### 2.3 漂移判定
✅ 零漂移 — compose 与容器 env 完全一致。

### 2.4 容器状态
- StartedAt: 2026-07-18T22:25:22Z (R1844 未重启, 0restart)
- 自 R1843 以来无重启，0中断

---

## 三、改前数据

### 3.1 6h 窗口 SR
| 窗口 | OK | Fail | Total | SR |
|------|-----|------|-------|------|
| 6h | 35 | 5 | 40 | 87.5% |

### 3.2 6h 按模型
| 模型 | 总数 | OK | Fail | SR | avg_ms | max_ms |
|------|------|-----|------|------|--------|--------|
| dsv4p_nv | 14 | 14 | 0 | 100% | 14718 | 40603 |
| glm5_2_nv | 26 | 21 | 5 | 80.8% | 6494 | 15722 |

### 3.3 6h 错误细分
| 错误类型 | 模型 | 数量 |
|----------|------|------|
| zombie_empty_completion | glm5_2_nv | 5 |

→ 全 NVCF content-filter 侧，零 config-fixable

### 3.4 30min 窗口（稀疏）
| 窗口 | OK | Fail | Total | SR |
|------|-----|------|-------|------|
| 30min | 0 | 4 | 4 | 0% |

4 条全 glm5_2 zombie_empty_completion（NVCF content-filter 集中爆发），零 ATE 零 peer-fb

### 3.5 Tier 级别
- glm5_2_nv pexec_success: 37 条
- dsv4p_nv 429_nv_rate_limit: 2 条（非系统性，正常 key rotation）
- 零 ATE，零 SSLEOF，零 pexec_timeout

### 3.6 Fallback
- 30min: 0 fallback（4 条 zombie 全未触发 fallback）
- 6h: 0 fallback（40 条全未触发 fallback）
- 零 peer-fb，零 SKIP-CIRCUIT，零 FALLBACK-OK

### 3.7 日志分析（docker logs nv_gw --tail 100）
```
[NV-ZOMBIE-EMPTY] glm5_2_nv: finish_reason=stop but content_chars=12 reasoning_chars=0 < 50
[NV-UPSTREAM-ERROR-CHUNK] sent finish_reason=content_filter error SSE chunk
→ 全 NVCF content-filter 侧，input_chars 115K-117K（大输入触发 content-filter）
→ zombie 检测正确触发，非 nv_gw 配置问题
```

---

## 四、优化决策

### 决策: NOP — 不改

**理由:**
1. 5 条失败全 zombie_empty_completion（NVCF content-filter），零 config-fixable
2. dsv4p_nv 14/14 100% SR，零 ATE，零 peer-fb
3. 所有参数已在 floor/optimal（UPSTREAM=51, KEY_COOLDOWN=60, TIER_COOLDOWN=60, BUDGET=178, FASTBREAK=1 等）
4. 容器零漂移，compose 与 env 一致
5. 无 config 可改依据 → 硬改违反铁律（改前必有数据）

### 不改铁律验证
- ✅ 改前必有数据: 6h 40req 全量分析，无 config-fixable 故障
- ✅ 聚焦 nv_gw: 仅分析 nv_gw 链路
- ✅ 所有修改写入仓库: 本轮 NOP 仍写 round 记录
- ✅ 铁律:只改HM1不改HM2: 本轮无改动

---

## 五、验证
- 0restart 0中断
- StartedAt 仍 2026-07-18T22:25:22Z
- 容器与 compose 零漂移
- 下轮继续观测 NVCF 侧 zombie 频率是否自愈
## ⏳ 轮到HM1优化HM2
