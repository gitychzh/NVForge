## HM2 Optimize HM1 — Round R1126

**触发类型**: False Trigger (Double-Dispatch of R1125)

---

### 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = opc2_uname (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发（double-dispatch，R1125 已由 pre-run script 提交）
- 当前 symlink: `RN_hm2_optimize_hm1.md -> rounds/R1125_hm2_optimize_hm1.md` ✓

---

### 2. HM1 容器状态

| 项目 | 值 |
|------|-----|
| 容器 | `nv_gw` Up (healthy) |
| 重启时间 | `2026-07-10T19:03:27Z` |
| Health | `{"status": "ok"}` |
| 重启后流量 | 13 请求，全部成功 |

---

### 3. 6h DB 数据

**总计**: 143 req / 129 OK / 14 fail = **90.2% SR**（与 R1125 完全一致）

**按上游类型**:
| upstream_type | cnt | ok | err | avg_ttfb | avg_dur | max_dur |
|---------------|-----|----|-----|----------|---------|---------|
| nv_integrate | 106 | 95 | 11 | 16,172 | 18,252 | 96,999 |
| nvcf_pexec | 34 | 34 | 0 | 11,666 | 11,666 | 48,049 |
| (ATE) | 3 | 0 | 3 | 558 | 61,297 | 61,376 |

**错误类型**（全部重启前）:
| error_type | cnt |
|------------|-----|
| zombie_empty_completion | 9 |
| all_tiers_exhausted | 3 |
| NVStream_TimeoutError | 2 |

**按模型**:
| mapped_model | cnt | ok | err | sr_pct | avg_dur |
|--------------|-----|----|-----|--------|---------|
| glm5_2_nv | 98 | 87 | 11 | 88.8% | 18,362 |
| dsv4p_nv | 29 | 26 | 3 | 89.7% | 19,314 |
| minimax_m3_nv | 9 | 9 | 0 | 100.0% | 14,483 |
| kimi_nv | 7 | 7 | 0 | 100.0% | 3,605 |

**nv_tier_attempts**: 0 行（无失败尝试）

**fallback**: fallback_occurred=f 全部，无触发

---

### 4. 重启后数据（有效窗口：2026-07-10T19:03:27Z → 现在）

| 指标 | 值 |
|------|-----|
| 重启后请求 | 13 |
| 成功 | 13 |
| 失败 | 0 |
| 成功率 | **100.0%** |

**按模型（重启后）**:
| mapped_model | cnt | ok | sr_pct | avg_dur | max_dur |
|--------------|-----|----|--------|---------|---------|
| glm5_2_nv | 9 | 9 | 100% | 6,472 | 12,019 |
| dsv4p_nv | 4 | 4 | 100% | 9,515 | 13,368 |

**docker logs**: 全部 `NV-SUCCESS` / `NV-INTEGRATE-SUCCESS`，一次尝试命中，零错误。

---

### 5. ms_gw 状态

| 窗口 | total | ok | sr_pct |
|------|-------|----|--------|
| 6h | 7 | 0 | 0.0% |

ms_gw 0% SR 为已知的 BrokenPipeError 流式同步缺陷（代码级），非配置可修复。

---

### 6. 当前 HM1 参数状态

全部参数处于下限/最优，无调整空间：
- UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=198
- TIER_COOLDOWN_S=15, KEY_COOLDOWN_S=25, MIN_OUTBOUND_INTERVAL_S=0
- NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
- NVU_EMPTY_200_FASTBREAK=2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
- NVU_TIER_BUDGET_DSV4P_NV=72, NVU_TIER_BUDGET_GLM5_2_NV=96
- NVU_MS_GW_FALLBACK_TIMEOUT=180, NVU_PEER_FALLBACK_TIMEOUT=66
- KEY_AUTHFAIL_COOLDOWN_S=60, FALLBACK_HEALTH_THRESHOLD=0.05
- NVU_FORCE_STREAM_UPGRADE=0, NV_INTEGRATE_KEY_COOLDOWN_S=0

---

### 7. 决策

**NOP** — 零参数变更，零 compose 修改，零容器重启。

**理由**:
1. False trigger（double-dispatch of R1125），数据与 R1125 完全一致
2. 重启后窗口 100% SR (13/13)，零错误，零 ATE，零 tier_attempts
3. 全部 14 个失败来自重启前（代码级：9× zombie_empty_completion + 2× NVStream_TimeoutError + 3× ATE）
4. 所有参数已处于下限/最优，无调整空间
5. ms_gw 0% SR 为已知代码级缺陷（流式同步 BrokenPipeError），非配置可修复
6. docker logs 全部 `NV-SUCCESS` / `NV-INTEGRATE-SUCCESS`，一次尝试命中，零负面信号
7. 铁律：只改HM1不改HM2 ✓

---

## ⏳ 轮到HM1优化HM2
