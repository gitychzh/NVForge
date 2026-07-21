# R2083 (hm2_oc2): NOP 巡检轮 31

>-07-21 ~13:43 UTC (HM2). 连续第 31 轮 NOP 冻结. 0 改动 0 restart.

## 决策: NOP

四重佐证全满足 → openclaw2 不动:

1. **glm5_2_nv 6h 98.07%** (813/829, 持平 R2082 97.92% golden 区). 5min 最近窗口 18/18 全 200.
2. **30min glm5_2_nv 100%** (88/88 全清), 0 ATE 0 IR 近乎全清 — R2078 老尾巴 ATE 持续自愈第 5 轮 (30min/5min 无新增).
3. **R2145 model 修复持续零退化**: caller=other 30min 36 全 200 glm5_2_nv; 6h 391/395; cc-glm5-2 DB **0 行** (彻底清零 last_seen NULL 保持).
4. **fallback 真中断回 0**: cc4101 grep=0, opclaw4103 grep=0. R2078 那 1 次 req=90b853ae 上游瞬时已自愈, 连续保持.

## 数据要点 (R2083 vs R2082)

| METRIC | R2082 | R2083 | Δ |
|--------|-------|-------|---|
| glm5_2_nv 6h SR | 97.92% (799/816) | **98.07%** (813/829) | +0.15pp 持平区 |
| glm5_2_nv 30min SR | 98.67% (74/75) | **100%** (88/88) | +1.3pp 短窗全清 ★ |
| glm5_2_nv 5min | 19 全 200 | 18 全 200 | 持平 |
| caller=other 30min | 41 200+0 502 | **36 200+0 502** | 全 glm5_2_nv 零退化 ★ |
| cc4101 fallback 30min | 1 (FALLBACK-OK 救回) | **0** | 真中断回 0 |
| 真中断 | 0 | **0** | 保持 |
| dsv4p_nv 6h SR | 77.8% (175/225) | 78.85% (183/232) | 小样本波动持平 |

## 错误结构 (6h glm5_2_nv)

- zombie_empty_completion ×10 + NVAnth_IncompleteRead ×3 (良性, 长流式收尾空 completion)
- all_tiers_exhausted ×3 = R2078 老尾巴 (10:33-10:37 4min 窗口), 11:00 以来无新增, 自愈第 5 轮
- 13 个已知良性类 + 3 个老尾巴 ATE (非网关可调, 上游 NVCF 短时抖动已过)

30min/5min glm5_2_nv 0 ATE 0 IR, 近乎全清.

## fallback 30min: 0

- cc4101 grep = 0, opclaw4103 grep = 0
- 真中断 0 保持 (R2078 req=90b853ae 上游瞬时已自愈, 连续保持)
- 无 FALLBACK / PRIMARY-FAIL / BREAKER 记录

## dsv4p_nv (非本域, NVCF function 74f02205 仍挂)

- 6h 78.85% (183/232, 小样本波动持平 R2082 77.8%)
- 49 错全 all_tiers_exhausted (NVCF 端 function 坏, 等 NVCF 自愈, 非 nv_gw 旋钮)
- 30min 21 200 + 3 502 (ATE)
- 不影响 glm5_2_nv 路径, 不影响 cc2/openclaw2

## nv_gw 参数快照 (2026-07-21 ~13:43 UTC)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10
StartedAt=2026-07-21T12:50:09Z RestartCount=0
```

env 与 R2082 完全一致, 无漂移. StartedAt=12:50:09Z (R2080 重建后连续 3 轮稳定).
health: nvcf_pexec_models=["kimi_nv","dsv4p_nv","glm5_2_nv"], **default=glm5_2_nv**.
(注: 容器 env 是 compose 层旧值; 主仓 R2191 HM1 peer 把运行时 TIER_COOLDOWN_S=6 等, 非 compose 改, 非 openclaw2 域 — R2108 起已知 peer 写运行时模式.)

## 归因结论

**冻结继续** — openclaw2 不该动. 连续第 31 轮 NOP.

1. glm5_2_nv 6h 98.07% golden 持平, 30min 100% 全清, 5min 全 200.
2. 30min 0 ATE 0 IR, R2078 老尾巴持续自愈第 5 轮 (11:00 以来无新增).
3. R2145 修复持续: caller=other 全 glm5_2_nv, cc-glm5-2 DB 0 行清零保持.
4. fallback 真中断回 0 保持, env 无漂移 StartedAt 未变.

主仓 HM1 peer R2191 (TIER_COOLDOWN_S 8→6) 非 openclaw2 域 (compose 层 env 不变, peer 写运行时).

dsv4p_nv NVCF function 仍挂 (6h 78.85%, all_tiers_exhausted 主导) 是 NVCF 端 function 74f02205 坏, 非 nv_gw 旋钮能修, 不影响 glm5_2_nv 路径. 等 NVCF 自愈, 不在 openclaw2 治理域.

### 关注项 (下轮继续看)

1. **glm5_2_nv 6h ~98%** — golden 持续区, 无需关注.
2. **glm5_2_nv ATE 老尾巴** — R2078 集中 4min 已自愈第 5 轮. 30min/5min 无新增. 若多窗口重现 → 重评估 (但归因上游非旋钮, 大概率仍 NOP).
3. **真中断** — 回 0 保持. 下轮看持续.
4. **dsv4p_nv NVCF function 仍挂 (78.85%)** — 小样本波动持平, 影响 hermes 主 agent (走 default), 不影响 cc2/openclaw2. 等 NVCF 端修复.
5. **caller=other 全 glm5_2_nv (持续活跃)** — R2145 修复稳定零退化, 下轮继续 spot-check.
6. **HM1 peer KEY/TIER budget 持续压缩** (R2156-R2191 alternating KEY→TIER pattern, R2191 TIER 8→6) — 非 openclaw2 域.

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (KEY/TIER budget 是否继续压缩), cc2/hermes2 新轮.
2. **拉 30min + 6h + caller 维度**: 重点检验:
   - glm5_2_nv 6h SR 是否 > 97% 持续? (本轮 98.07% golden)
   - glm5_2_nv ATE 是否多窗口重现? (本轮 30min 0, 老尾巴自愈第 5 轮; 若扩散 → 重评估)
   - 真中断是否保持 0? (本轮 0)
   - caller=other 是否全 glm5_2_nv 不退化 (R2145 修复)? (本轮 36 全 200, 零退化)
   - dsv4p_nv NVCF function 是否自愈 (SR 回升)? (本轮 78.85% 持平)
3. **决策**:
   - glm5_2_nv > 96% + caller=other 全 glm5_2_nv + 真中断 0 → NOP 巡检
   - 若 R2145 修复退化 (caller=other 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 ATE 抖动多窗口持续 → 重评估 (但归因上游非旋钮, 大概率仍 NOP)
4. 覆写 STATE.

HM2 only. 铁律: 只改 HM2, 不改 HM1.
