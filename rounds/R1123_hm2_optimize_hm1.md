## HM2 Optimize HM1 — Round R1123

**触发**: 误触发（双重派遣，R1122 已由预运行脚本提交并推送，锚点已正确。cron 再次派遣。脚本输出: `"这是我提交的, 不触发"`）

**类型**: NOP（无优化，所有参数已处于下限/最优，容器重启后 100% 成功率）

---

### 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = `opc2_uname` (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- 预运行脚本已提交 R1122（NOP），锚点已正确指向 R1122
- cron 仍被派遣 — 双重派遣误触发
- HM1 本地 git log 停留在 R821（302 轮落后）

---

### 2. HM1 容器状态

| 项目 | 值 |
|------|-----|
| 容器 | `nv_gw` Up ~9.3h (healthy) |
| 重启时间 | `2026-07-10T19:03:27Z` |
| 重启后流量 | 8 请求，全部成功 |

---

### 3. 6h DB 数据（全窗口：含重启前）

**总计**: 140 req / 126 OK / 14 fail = **90.0% SR**

**按上游类型**:
| upstream_type | cnt | ok | err | avg_ttfb | avg_dur | max_dur |
|---------------|-----|----|-----|----------|---------|---------|
| nv_integrate | 103 | 92 | 11 | 16,548 | 18,680 | 96,999 |
| nvcf_pexec | 34 | 34 | 0 | 11,666 | 11,666 | 48,049 |
| (ATE) | 3 | 0 | 3 | 558 | 61,297 | 61,376 |

**错误类型**（全部重启前）:
| error_type | cnt |
|------------|-----|
| zombie_empty_completion | 9 |
| all_tiers_exhausted | 3 |
| NVStream_TimeoutError | 2 |

**按模型**:
| mapped_model | cnt | ok | err | sr_pct |
|--------------|-----|----|-----|--------|
| glm5_2_nv | 95 | 84 | 11 | 88.4% |
| dsv4p_nv | 29 | 26 | 3 | 89.7% |
| minimax_m3_nv | 9 | 9 | 0 | 100.0% |
| kimi_nv | 7 | 7 | 0 | 100.0% |

**nv_tier_attempts**: 0 行（无失败尝试）

**fallback**: fallback_occurred=f 全部，无触发

---

### 4. 重启后数据（有效窗口）

| 指标 | 值 |
|------|-----|
| 重启后请求 | 8 |
| 成功 | 8 |
| 失败 | 0 |
| 成功率 | **100.0%** |

**按模型（重启后）**:
| mapped_model | cnt | ok | sr_pct |
|--------------|-----|----|--------|
| dsv4p_nv | 4 | 4 | 100% |
| glm5_2_nv | 4 | 4 | 100% |

**重启后错误**: 0（零错误，零 ATE，零 zombie）

---

### 5. ms_gw 状态

| 窗口 | total | ok | sr_pct |
|------|-------|----|--------|
| 6h 全窗口 | 7 | 0 | 0.0% |
| 重启后 | 1 | 0 | 0.0% |

ms_gw 0% SR 为已知的 BrokenPipeError 流式同步缺陷（代码级），非配置可修复。

---

### 6. 当前 HM1 参数状态

| 参数 | 值 | 评估 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | per-key 上限 |
| TIER_TIMEOUT_BUDGET_S | 198 | 充裕，<300 安全 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 下限 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | 下限 |
| NVU_EMPTY_200_FASTBREAK | 2 | R1031 修复（R1039 已确认 bug：不生效，但 nv_tier_attempts=0 → 无 empty_200 信号） |
| TIER_COOLDOWN_S | 15 | 下限 |
| KEY_COOLDOWN_S | 25 | 近下限 |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | dsv4p_nv peer-fb 启用 |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | >UPSTREAM=66，安全 |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | 充裕 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 | 充裕 |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | 匹配 UPSTREAM |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | 防御性参数 |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | 下限（dead param，实际由 NVU_FALLBACK_HEALTH_THRESHOLD=0.05 控制） |

**全部参数处于下限/最优，无调整空间。**

---

### 7. 决策

**NOP** — 零参数变更，零 compose 修改，零容器重启。

**理由**:
1. 重启后窗口 100% SR (8/8)，零错误，零 ATE，零 tier_attempts
2. 全部 14 个失败来自重启前（代码级：9× zombie_empty_completion + 2× NVStream_TimeoutError + 3× ATE）
3. 所有参数已处于下限/最优，无调整空间
4. ms_gw 0% SR 为已知代码级缺陷（流式同步 BrokenPipeError），非配置可修复
5. HM1 仍停留在 R821（302 轮落后），未提交任何新内容

---

## ⏳ 轮到HM1优化HM2
