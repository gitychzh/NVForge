# R2158_hm2_oc2 巡检 (本域 golden 延续 + 6h 0 ATE 保持 + env 无漂移 RC=0 连续)

**轮号**: R2158_hm2_oc2  **日期**: 2026-07-23 (UTC ~11:56 / HM2)
**类型**: NOP 巡检轮 (连续第 93 轮冻结, 0 改动 0 restart)
**STATE 滞后修正**: 第 51 次 (STATE 头停 R2139, 主仓 openclaw2 线 round 文件已到 R2157 commit 6ff3606 — 本轮 cat STATE + git log + ls round 文件三确认 R2157→R2158 对齐覆写)

## 背景

R2157 已确认本域 glm5_2_nv 三恢复窗全 golden 延续 (30min 98.3%/60min 99.2%/2h 98.8%/6h 98.2%)
+ 6h ATE 全 0 保持 (风暴尾彻底滑出 6h 窗). 本轮 R2158 确认稳态延续 + 6h 0 ATE 保持 + env 无漂移.

## 数据要点 (R2158 实测当前窗口, vs R2157 round)

| METRIC | R2157 (round) | R2158 (实测本轮) | Δ |
|--------|---------------|------------------|---|
| glm5_2_nv 6h SR | 98.2% (651/663) | **98.5%** (662/672) | +0.3pp golden 上沿延续企稳 |
| glm5_2_nv 6h ATE | 0 (hourly 0 行) | **0** (glm5_2_nv 6h 0 ATE) | 风暴尾滑出保持 |
| glm5_2_nv 30min | 98.3% (59/60) | **98.5%** (66/67) | golden 区延续 |
| glm5_2_nv 60min | 99.2% (125/126) | **98.4%** (126/128) | golden 区延续 |
| glm5_2_nv 2h | 98.8% (248/251) | **98.3%** (238/242) | golden 区延续 |
| 6h 499 (openclaw2 域) | 0 | **0** | 持续健康 |
| fallback 30min (cc4101) | 0 | **1** (救回 0 真中断) | 0 真中断延续 |
| fallback 30min (opclaw4103) | 2 | **0** | opclaw 侧干净 |
| dsv4p_nv 6h SR | 55.7% (78/140) | **50.0%** (53/105) | -5.7pp NVCF 74f02205 恶化延续非本域 |
| kimi_nv 6h SR | 75.3% (165/219) | **80.0%** (192/240) | +4.7pp cc2 R2286 过渡期振荡回升非本域 |

## 数据明细 (实测当前窗口, UTC ~11:56)

- 6h glm5_2_nv (662/672, 98.5%): 错 10 = **6 stream_absolute_cap + 4 zombie_empty_completion**, **0 ATE**
  (6h ATE by mapped_model 查询: glm5_2_nv ATE=0 / dsv4p_nv ATE=54 / kimi_nv ATE=35 — 89 ATE 全非本域)
- 恢复窗 golden 全延续: 30min 98.5% (66/67) / 60min 98.4% (126/128) / 2h 98.3% (238/242)
- 30min glm5_2_nv 1 错 = zombie_empty_completion (mid-stream 背景波, 首字节已收未触发 fallback), **0 ATE**
- 30min caller × model: glm5_2_nv cc4101-primary 30×200 + glm5_2_nv other 35×200+1×502(zombie 背景波)
  + kimi_nv unknown 13×200+7×502 (非本域); openclaw2 自身 30min 全 200
  (R2145/R2149 锁定 model=glm5_2_nv 零退化保持, 本域 caller 全 glm5_2_nv 无 cc-glm5-2/dsv4p 串入)
- 30min 全表 73×200 + 8×502 = 90.1% SR: 8 错 = 5 ATE + 3 zombie, **全非本域**
  (kimi_nv 7 错=5ATE+2zombie 过渡期 + glm5_2_nv other 1 zombie 背景波)
- 6h 499=0 (openclaw2 域持续健康, R2149 锁定 model=glm5_2_nv 零退化保持)
- fallback 30min: cc4101=1 (救回, 0 真中断), opclaw4103=0, **0 真中断**
- 非本域 6h: dsv4p_nv 50.0% (53/105 vs R2157 55.7% -5.7pp NVCF 74f02205 恶化延续) +
  kimi_nv 80.0% (192/240 vs R2157 75.3% +4.7pp cc2 R2286 改默认模型过渡期振荡回升)
- 30min kimi_nv 13×200+7×502 (过渡期振荡型 5ATE+2zombie, 非本域) + dsv4p_nv 30min 流量小
- 全 NVCF 上游连接类非旋钮能治非本域

## nv_gw 参数快照 (2026-07-23 本轮, 与 R2157 STATE 逐行一致无漂移)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
NVU_EMPTY_200_FASTBREAK=3  NVU_PEXEC_TIMEOUT_FASTBREAK=3
StartedAt=2026-07-22T15:10:34Z  RestartCount=0  (连续第 43+ 轮 RC=0)
```

注: 容器 env 是 compose 层 HM2 域旧值. 主仓新 commit `9a81072 R2159 (hm2->hm1)` KEY_COOLDOWN_S 0->5
修复 R2285 zero-cooldown 429 cycling — HM1 域改动 (R2285 是 HM1 peer 轮号), 非 openclaw2 域 (铁律只改
HM2 nv_gw 不碰 HM1). HM2 nv_gw 当前 KEY_COOLDOWN_S=60 未变, StartedAt RC=0 连续多轮未重建, 本域未被动.
health: nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=glm5_2_nv, port=40006.

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **本域三恢复窗全 golden 延续**: 30min 98.5% / 60min 98.4% / 2h 98.3% / 6h 98.5%, 全 golden 上沿企稳.
2. **6h 0 ATE 保持**: glm5_2_nv 6h ATE=0 (89 ATE 全在 dsv4p_nv 54 + kimi_nv 35, 全非本域), 风暴尾彻底滑出.
3. **30min 0 真中断**: cc4101 fallback 1 救回 + opclaw4103 0, 30min 全表 8 错全非本域.
4. **499=0** 持续健康 (R2149 锁定 model=glm5_2_nv 零退化保持, 本域 caller 全 glm5_2_nv).
5. **env 无漂移** StartedAt 07-22T15:10:34Z RC=0 连续第 43+ 轮未重建.

caller cc4101-primary 30 + other 35 全 glm5_2_nv 全 200 (R2145/R2149 修复零退化).
dsv4p_nv 恶化 + kimi_nv 过渡期振荡全非本域 (NVCF 上游连接类非旋钮能治).

### 关注项

1. **glm5_2_nv 本域 golden 98.5%** — 稳态持续, 无需关注
2. **6h 0 ATE 保持** — 风暴尾彻底滑出, 非稳态指标已干净
3. **6h 499=0** — openclaw2 域健康持续, R2149 锁定零退化保持
4. **dsv4p_nv 6h 50.0% 恶化** — NVCF 74f02205 恶化延续非本域, 等 NVCF 端修复
5. **kimi_nv 6h 80.0% 振荡回升** — cc2 R2286 改默认模型过渡期阵痛非本域
6. **caller cc4101-primary+other 全 glm5_2_nv** — R2145/R2149 修复稳定零退化
7. **主仓 9a81072 R2159 hm2->hm1 KEY_COOLDOWN 0->5** — HM1 域修复 R2285, 非 openclaw2 域 (铁律只改 HM2)
8. **STATE 滞后本轮 (第 51 次修正)** — STATE 停 R2139, 主仓 openclaw2 线已 R2157, 本轮 R2158 对齐

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (9a81072 KEY_COOLDOWN 0->5 修复 R2285 后下一轮), cc2/hermes2 新轮
2. **拉 30min + 6h + 恢复窗维度**: 重点检验:
   - 本域 glm5_2_nv 三恢复窗是否保持 golden (>97%)?
   - 6h 0 ATE 是否保持 (风暴尾不回潮)?
   - 30min 是否保持 0 真中断?
   - caller cc4101-primary+other 是否全 glm5_2_nv 不退化 (R2145/R2149 修复)?
   - 6h 499 是否保持 0?
   - dsv4p_nv 恶化是否止跌或 NVCF 74f02205 再恶化?
   - kimi_nv 过渡期是否收尾 (振荡回升趋稳)?
3. **决策**:
   - 恢复窗 golden + caller 全 glm5_2_nv + 30min 0 真中断 + 499=0 → NOP 巡检
   - 若 R2145/R2149 修复退化 (caller 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env
   - 若风暴再起 (双 tier 同挂) → 记录观测, 不动 (旋钮无效已证)
4. 覆写 STATE

## 最近 5 轮摘要

1. **R2158_hm2_oc2**: NOP 巡检轮 93 — 0 改动 0 restart 连续第 93 轮冻结. STATE 滞后修正第 51 次 (STATE
   停 R2139, 主仓 openclaw2 线 R2157 commit 6ff3606, 本轮 R2157→R2158 对齐). 本域 glm5_2_nv 三恢复窗全
   golden 延续 (30min 98.5%/60min 98.4%/2h 98.3%/6h 98.5% +0.3pp 上沿企稳), 6h 0 ATE 保持 (glm5_2_nv ATE=0,
   89 ATE 全在 dsv4p_nv 54 + kimi_nv 35 全非本域). 30min 本域干净 glm5_2_nv caller cc4101-primary 30+other 35
   全 200 +1 错 zombie 背景波 0 ATE; 30min 全表 73×200+8×502=90.1% 8 错全非本域 (kimi_nv 7 过渡期 + glm5_2_nv
   other 1 zombie). 6h 499=0 持续健康 (R2149 锁定 model=glm5_2_nv 零退化). fallback 30min cc4101=1 救回+opclaw4103=0
   0 真中断. 非本域: dsv4p_nv 6h 50.0% (-5.7pp NVCF 74f02205 恶化延续) + kimi_nv 6h 80.0% (+4.7pp cc2 R2286 过渡期
   振荡回升) 全 NVCF 上游连接类非旋钮能治非本域. env 无漂移 nv_gw StartedAt 07-22T15:10:34Z RC=0 连续第 43+ 轮.
   主仓 9a81072 R2159 hm2->hm1 KEY_COOLDOWN 0->5 修复 R2285 非 openclaw2 域 (铁律只改 HM2). 连续 93 NOP. HM2 only.
2. **R2157_hm2_oc2**: NOP 巡检轮 92 — 0 改动 0 restart 连续第 92 轮冻结. STATE 滞后修正第 50 次 (STATE 停
   R2139 主仓 openclaw2 线 R2156 本轮 R2156→R2157 对齐覆写). 本域 glm5_2_nv 三恢复窗全 golden 延续 (30min
   98.3%/60min 99.2%/2h 98.8%/6h 98.2%), 6h ATE 全 0 保持 (hourly 查询 0 行 风暴尾彻底滑出 6h 窗). 30min 本域
   干净 glm5_2_nv caller cc4101-primary 23+other 34+openclaw2 全 200 1 错 zombie 背景波 0 ATE. 6h 499=0 持续
   健康 (R2149 锁定 model=glm5_2_nv 零退化). fallback 30min cc4101=0+opclaw4103=2 双 FALLBACK-STREAM 救回 0 真
   中断 (opclaw openai 侧 25s ttfb timeout 非本域). 非本域: dsv4p_nv 6h 55.7% (NVCF 74f02205 恶化延续) +
   kimi_nv 6h 75.3% (cc2 R2286/R2289 改默认模型过渡期阵痛收尾��) 全 NVCF 上游连接类非旋钮能治非本域. env 无漂移
   nv_gw StartedAt 07-22T15:10:34Z RC=0 连续第 43+ 轮未重建. 连续 92 NOP. HM2 only.
3. **R2156_hm2_oc2**: NOP 巡检轮 91 — 0 改动 0 restart 连续第 91 轮冻结. STATE 滞后修正第 49 次. 本域 glm5_2_nv
   三恢复窗全 golden 延续 (30min 98.5%/60min 97.6%/2h 97.7%/6h 98.0%), 6h ATE 全 0 (7 小时桶全 0 风暴尾彻底
   滑出 6h 窗). 30min 本域干净 glm5_2_nv caller cc4101-primary 30+other 34+openclaw2 全 200 1 错 zombie 背景波.
   6h 499=0 持续健康. fallback 30min cc4101=0 + opclaw4103=2 双 FALLBACK-STREAM 救回 0 真中断. 非本域:
   dsv4p_nv 6h 58.2% + kimi_nv 6h 77.8% (cc2 R2286 改默认模型过渡期阵痛收尾中) 全 NVCF 上游连接类非旋钮能治非
   本域. env 无漂移 StartedAt 07-22T15:10:34Z RC=0 连续第 43+ 轮未重建. 连续 91 NOP. HM2 only.
4. **R2155_hm2_oc2**: NOP 巡检轮 90 — 0 改动 0 restart. (STATE 历史 R2154 落后主仓 R2155, 本轮已 R2156 覆写,
   详见 R2156 round). 本域 golden 延续 + 6h 0 ATE + 499=0 + env 无漂移. 连续 90 NOP. HM2 only.
5. **R2154_hm2_oc2**: NOP 巡检轮 89 — 0 改动 0 restart. (STATE 历史 R2153 落后主仓 R2154, 后续 R2156 覆写对齐,
   详见 R2156 round). 本域 golden 延续 + 6h 0 ATE + 499=0 + env 无漂移. 连续 89 NOP. HM2 only.
