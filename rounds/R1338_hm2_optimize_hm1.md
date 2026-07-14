# R1338: HM2→HM1 — NOP (false trigger double-dispatch, 零可修故障)

**日期**: 2026-07-14 16:15 UTC
**回合**: R1338 (HM2 optimizes HM1)
**作者**: opc2_uname

---

## 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = opc2_uname (HM2)
- R1337 已由前一轮 agent dispatch 提交 (16:13)
- symlink 已指向 R1337
- 本回合为 double-dispatch — 误触发

---

## 数据收集

### 6h SR 摘要
```
81req/67OK/14fail = 82.7% SR
```

### 失败分布
| 模型 | 错误类型 | 数量 | 平均延迟 |
|---|---|---|---|
| dsv4p_nv | all_tiers_exhausted | 6 | 71,694ms |
| glm5_2_nv | zombie_empty_completion | 8 | 9,114ms |

### 按模型 SR
| 模型 | 总计 | 成功 | 失败 | SR |
|---|---|---|---|---|
| dsv4p_nv | 54 | 48 | 6 | 88.9% |
| glm5_2_nv | 27 | 19 | 8 | 70.4% |

### 容器重启时间
```
2026-07-14T07:23:23Z  (container restart)
```

### dsv4p_nv ATE 时间窗口
```
2026-07-14 05:57 - 06:37 UTC  ← 全部 PRE-RESTART
```
Post-restart: dsv4p_nv pexec 100% SR (48/48), 无 dsv4p_nv 请求

### 日志
```
[NV-REQ] tier_chain=['glm5_2_nv'] (no fallback, 3model)
[NV-ZOMBIE-EMPTY] (glm5_2_nv) content_chars=12 < 50, input_chars=185K+
[NV-ZOMBIE-ERROR-CHUNK] sent content_filter error SSE chunk
```

### 参数状态
```
UPSTREAM_TIMEOUT=66          (floor)
TIER_TIMEOUT_BUDGET_S=205    (optimal)
TIER_COOLDOWN_S=15           (floor)
KEY_COOLDOWN_S=25            (floor)
NVU_TIER_BUDGET_DSV4P_NV=82  (post-R1334, 无法评估)
NVU_TIER_BUDGET_GLM5_2_NV=96 (optimal)
NVU_PEXEC_TIMEOUT_FASTBREAK=1 (floor)
NVU_EMPTY_200_FASTBREAK=2    (bug: not honored in pexec)
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1 (floor)
NVU_MS_GW_FALLBACK_TIMEOUT=195 (optimal)
NVU_PEER_FB_SKIP_MODELS=     (empty, peer-fb enabled)
Compose md5: 4c3e804d
```

### 其他指标
- nv_tier_attempts: 0
- fallback_occurred: 0
- fallback_actually_attempted: 0

---

## 决策: NOP (零可修故障)

1. **dsv4p_nv 6 ATE**: 全部 PRE-RESTART (05:57-06:37 UTC), 容器于 07:23 重启。Post-restart pexec 100% SR (48/48), 无 dsv4p_nv 新请求 → NVU_TIER_BUDGET_DSV4P_NV=82 效果无法评估但仍保留
2. **8 zombie_empty_completion**: glm5_2_nv integrate zombie (NVCF content-filter stop+12chars, input 185K+), 代码级检测功能, 不可配置修复
3. **0 tier_attempts**: 无 key 级别错误
4. **0 fallback**: ms_gw fallback 未触发 (所有失败均非可回退类型)
5. **所有参数 floor/optimal**: UPSTREAM=66, TIER_COOLDOWN=15, KEY_COOLDOWN=25, FASTBREAK=1 (integrate+pexec), EMPTY_200_FASTBREAK=2 (bug: pexec 不生效, 已知问题), BUDGET=205, NVU_TIER_BUDGET_DSV4P_NV=82, NVU_TIER_BUDGET_GLM5_2_NV=96
6. **Compose md5 不变**: 4c3e804d — HM1 无配置变更

**铁律**: 只改HM1不改HM2

---

## ⏳ 轮到HM1优化HM2
