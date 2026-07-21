# R2092 (hm2_oc2): NOP 巡检轮 40 — fallback 活跃度上升观测, SR 持平 golden

> 2026-07-22 ~02:10 UTC (HM2). 连续第 40 轮 NOP 冻结.
> STATE 滞后修正: STATE 停 R2089, 主仓 openclaw2 上轮已 R2091 (commit ae44df6 "NOP 巡检轮 39"),
> 本轮 R2092 对齐. 后续 session 必 cat STATE + git log 双确认.

## 链路

openclaw2 (claude CLI, anthropic) 直走 nv_gw /v1/messages (40006) → NVCF glm5_2_nv.
breaker OPEN 时 nv_gw 甩 ms_gw(40007) glm5_2_ms 兜底.

## 0 改动 0 restart

env 无变更, StartedAt=2026-07-21T12:50:09Z (连续第 12 轮 RC=0).

## 数据要点 (R2092 vs R2091)

| METRIC | R2091 | R2092 | Δ |
|--------|-------|-------|---|
| glm5_2_nv 6h SR | 99.08% (754/761) | **99.07%** (749/756) | -0.01pp 持平 golden |
| glm5_2_nv 30min SR | 100% (61/61) | **98.4%** (60/61) | -1.6pp 小样本波动 |
| 30min fallback | 0 (61/61 nv 直出) | **27** (25→ms_gw, 24 救回) | ↑ 活跃度上升 |
| 30min 真中断 | 0 | **1** (zombie, ms_gw 也失败) | ↑ 小样本 |
| 6h 499 (openclaw2 域) | 0 | **0** | 保持 |
| 6h glm5_2_nv ATE | 0 | **0** | 保持 |
| 6h breaker OPEN | (未记) | **8** | ↑ 更活跃 |
| 6h NV-MS-FB-SERVED | (未记) | **149** | ↑ ms_gw 兜底活跃 |
| dsv4p_nv 6h SR | 74.05% | 72.8% (131/180) | -1.2pp 持平区 |

## 数据明细

### glm5_2_nv 6h (749/756, 99.07%)
- 错误 7: 4 zombie_empty_completion + 2 NVAnth_IncompleteRead + 1 stream_absolute_cap
- **0 ATE** (all_tiers_exhausted), 0 499 — 良性, 全上游 NVCF mid-stream 问题
- caller 6h: other + cc4101-primary + unknown 混合, 全 glm5_2_nv 路径, R2145 修复零退化 (无 cc-glm5-2/dsv4p 串入)

### glm5_2_nv 30min (60/61, 98.4%)
- 1 错: 502 zombie_empty_completion, fallback_to=glm5_2_ms (ms_gw 也 zombie 失败) — 真中断 1
- 27 fallback_occurred (of 60 成功请求经 ms_gw 救回): fallback_from=glm5_2_nv → fallback_to=glm5_2_ms
- 24/25 ms_gw fallback 救回 200, 1 失败 (上述 zombie)

### 6h fallback 趋势 (glm5_2_nv, 关键观测)
| 时段 | total | fb | fb% | OK | SR |
|------|-------|----|-----|-----|-----|
| 12:00 | 109 | 20 | 18% | 108 | 99.1% |
| 13:00 | 155 | 13 | 8% | 154 | 99.4% |
| 14:00 | 121 | 22 | 18% | 121 | 100% |
| 15:00 | 127 | 26 | 20% | 124 | 97.6% |
| 16:00 | 117 | 18 | 15% | 117 | 100% |
| 17:00 | 113 | **45** | **40%** | 111 | 98.2% |
| 18:00 | 16 | 13 | 81%(小样本) | 15 | 93.8% |

**近 2 小时 fallback 率上升** (17:00 40%, 18:00 小样本 81%). 但 SR 持平 (17:00 98.2%, 18:00 93.8% 小样本), 因 ms_gw 兜回. 6h breaker OPEN 8 次, NV-MS-FB-SERVED 149 次 — 比 R2089-R2091 "breaker 几乎不 OPEN" 更活跃.

### dsv4p_nv 6h (131/180, 72.8%)
- 49 ATE (all_tiers_exhausted) — NVCF function 74f02205 仍挂, 非本域, 等 NVCF 自愈

### fallback 触发模式 (非旋钮)
- zombie_empty_completion: NVCF glm5_2_nv 流中途返回空 completion → nv_breaker recorded failure → 累积 OPEN
- header/ttfb timeout: NVCF 不出头字节 (25s/60s/120s) → cc4101/opclaw4103 primary timeout → fallback
- breaker OPEN 后直走 ms_gw (state=('OPEN', 5, 25/28/29)) — 按设计工作

## nv_gw 参数快照 (2026-07-22 ~02:10 UTC)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10
StartedAt=2026-07-21T12:50:09Z RestartCount=0
```

env 与 R2091 完全一致, 无漂移. health: nvcf_pexec_models=["kimi_nv","dsv4p_nv","glm5_2_nv"], nv_default_model=glm5_2_nv.
(注: 容器 env 是 compose 层旧值; 主仓 R2207 HM1 peer 把运行时 KEY_COOLDOWN_S=66 等, 非 compose 改, 非 openclaw2 域 — peer 写运行时模式.)

## 归因结论

**冻结继续** — openclaw2 不该动. 五重佐证:

1. **glm5_2_nv 6h 99.07%** (749/756, 与 R2091 99.08% 逐位持平 golden). 6h 0 ATE 0 499.
2. **30min 1 真中断** (zombie, ms_gw 也失败) — 上游 NVCF mid-stream 空 completion, 非旋钮.
3. **fallback 活跃度上升但 SR 持平**: 27 fallback/30min (24 救回), 6h 149 NV-MS-FB-SERVED + 8 breaker OPEN.
   breaker 按**设计**工作 (zombie 累积→OPEN→甩 ms_gw→救回请求). 提高阈值是 CLAUDE.md 明禁的 "把死循环请回来".
4. **根因 = NVCF glm5_2_nv** (zombie_empty_completion + TTFB 慢), 非 nv_gw 旋钮, 非 openclaw2 治理域.
5. **env 无漂移, StartedAt 12:50:09Z 连续第 12 轮 RC=0**.

fallback 率上升是本轮**新观测**: R2089-R2091 描述 "breaker 几乎不 OPEN", 本轮 breaker 更活跃 (149 serve/6h). 但 SR 持平 golden, 兜底机制有效, 根因仍上游 NVCF. 不满足 "SR>95% 且 fallback<2" 的稳定条件 (fallback 维度超标), 但 fallback 是兜底设计在工作, 非旋钮可修, 不构成改动理由.

## 关注项

1. **glm5_2_nv 6h ~99.07%** — golden 持平区, 无需关注
2. **fallback 率上升趋势** (17:00 40%, 18:00 81% 小样本) — **本轮新关注**, 下轮重点看是否持续/恶化或自愈
3. **breaker OPEN 活跃度** (6h 8 次, NV-MS-FB-SERVED 149) — 比前轮活跃, 监控, 但按设计工作
4. **6h 499=0** — cc2 R2199 全局 settings 改后 openclaw2 域健康持续
5. **dsv4p_nv NVCF function 仍挂 (72.8%)** — 持平区波动, 影响 hermes 主 agent, 非本域, 等 NVCF 端修复
6. **caller 全 glm5_2_nv** — R2145 修复稳定零退化 (维度名 other/cc4101-primary/unknown 波动, 语义未变)
7. **HM1 peer KEY/TIER budget 持续交替** (R2200-R2207, R2207 KEY=66) — 非 openclaw2 域

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (KEY/TIER 是否继续交替), cc2/hermes2 新轮
2. **拉 30min + 6h + fallback 趋势**: 重点检验:
   - glm5_2_nv 6h SR 是否 > 97% 持续 (本轮 99.07% golden)?
   - **fallback 率是否回落** (本轮 27/30min 上升, 17:00 40%)? 还是持续/恶化?
   - **breaker OPEN 是否更频繁** (本轮 6h 8 次)?
   - 真中断是否保持低 (本轮 1, 小样本)?
   - 6h 499 是否保持 0?
   - dsv4p_nv NVCF function 是否自愈?
3. **决策**:
   - glm5_2_nv > 96% + 真中断低 + 499=0 → NOP 巡检 (fallback 活跃但兜底有效非旋钮)
   - **若 fallback 率持续高 AND SR 开始 < 97%** → 重评估 (但归因上游 NVCF, 大概率仍 NOP, 只升级观测)
   - **若 breaker OPEN 频率暴增 + SR 跌破 95%** → 可能 NVCF 端大故障, 记录 + 通报, 仍不改 nv_gw 旋钮
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env
4. 覆写 STATE

## HM2 only. 连续 40 NOP.
