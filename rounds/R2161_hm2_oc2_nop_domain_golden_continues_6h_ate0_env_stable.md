# R2161_hm2 巡检 (本域 golden 延续 + 6h 0 ATE 保持 + env 无漂移 RC=0 连续)

**轮号**: R2161_hm2_oc2  **日期**: 2026-07-23 (UTC ~12:40 / HM2)
**类型**: NOP 巡检轮 (连续第 95 轮冻结, 0 改动 0 restart)
**STATE 滞后修正**: 第 53 次 (STATE 头停 R2139, 主仓 openclaw2 线 round 文件已到 R2160 commit 938a238 — 本轮 cat STATE + git log + ls round 文件三确认 R2160→R2161 对齐覆写. 注: R2159 号被 hm2->hm1 桥接轮 commit 9a81072 "KEY_COOLDOWN_S 0->5 fix R2285" 占用非 hm2_oc2 系列, openclaw2 线 R2158→R2160→R2161 连续避歧义)

## 背景

R2160 已确认本域 glm5_2_nv 三恢复窗全 golden 延续 (30min 97.2%/60min 98.5%/2h 98.1%/6h 98.5%)
+ 6h 0 ATE 保持 (风暴尾彻底滑出 6h 窗) + env 无漂移. 本轮 R2161 确认稳态延续 + 6h 0 ATE 保持 + env 无漂移.

## 数据要点 (R2161 实测当前窗口, vs R2160 round)

| METRIC | R2160 (round) | R2161 (实测本轮) | Δ |
|--------|---------------|------------------|---|
| glm5_2_nv 6h SR | 98.5% (700/711) | **98.37%** (723/735) | 持平 golden 上沿延续 |
| glm5_2_nv 6h ATE | 0 | **0** (nv_tier_attempts 无 all_tiers_exhausted) | 风暴尾滑出保持 |
| glm5_2_nv 30min | 97.2% (70/72) | **98.4%** (60/61) | golden 区延续 |
| glm5_2_nv 60min | 98.5% (129/131) | **97.7%** (129/132) | golden 区延续 |
| glm5_2_nv 2h | 98.1% (257/262) | **98.0%** (247/251) | golden 区延续 |
| 6h 499 (openclaw2 域) | 0 | **0** | 持续健康 |
| fallback 30min | cc4101=0+opclaw4103=0 | cc4101=1救回+opclaw4103=0 | 0 真中断 |
| env StartedAt | 07-22T15:10:34Z RC=0 | 07-22T15:10:34Z RC=0 | 无漂移连续 43+ 轮 |

## 数据明细 (实测当前窗口, UTC ~12:40)

- 6h glm5_2_nv (723/735, 98.37%): 错 12 = **8 stream_absolute_cap + 4 zombie_empty_completion**, **0 ATE**
- 6h 按小时全程稳 (每小时 100+×200, 502 散点 2-4 个/小时全背景波, 无风暴窗):
  06:00=14×200 / 07:00=94×200 / 08:00=134×200+2×502 / 09:00=135×200+4×502 /
  10:00=119×200+2×502 / 11:00=121×200+2×502 / 12:00=106×200+2×502
- nv_tier_attempts 6h 无 all_tiers_exhausted (本域 glm5_2_nv tier 全 pexec_success 628 + pexec_429 90 +
  pexec_SSLEOFError 46 + pexec_empty_200 28 + pexec_conn_RemoteDisconnected 16 + pexec_504 1, 全上游连接类背景波非系统性)
- 恢复窗稳态: 30min 98.4% (60/61) / 60min 97.7% (129/132) / 2h 98.0% (247/251) 全 golden 区
- 30min 本域干净: glm5_2_nv cc4101-primary 31×200 + other 29×200 全 200, 1 错=openclaw 1 stream_absolute_cap 背景波 0 ATE
- 6h 499=0 (openclaw2 域): openclaw caller 6h glm5_2_nv 7×200 + 1×502(cap) + dsv4p_nv 1×200 (pexec 单点降级非退化);
  R2149 锁定 model=glm5_2_nv 零退化保持 (无 cc-glm5-2 串入)
- fallback 30min: cc4101=1 救回 + opclaw4103=0, **0 真中断** (单点非系统性)
- 非本域: kimi_nv 6h tier NVCFPexecRemoteDisconnected 35 + empty_200 8 (cc2 R2286 过渡期阵痛延续非本域);
  dsv4p_nv 6h tier NVCFPexecRemoteDisconnected 6 (NVCF 74f02205 恶化延续非本域)

## nv_gw 参数快照 (2026-07-23 本轮, 与 R2160 STATE 逐行一致无漂移)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
NVU_EMPTY_200_FASTBREAK=3  NVU_PEXEC_TIMEOUT_FASTBREAK=3  NVU_BIG_INPUT_THRESHOLD=250000
StartedAt=2026-07-22T15:10:34Z  RestartCount=0  (连续第 43+ 轮 RC=0)
```

注: 容器 env 是 compose 层 HM2 域值. HM1 peer R2282-R2285 全 HM1 域 (R2282 SSLEOF key_cycle_attempts 修复代码改,
R2283 TIER_COOLDOWN_S 66→0, R2284 PEXEC_TIMEOUT_FASTBREAK 1→2, R2285 KEY_COOLDOWN_S 66→0 多轮连调),
主仓 R2159 hm2->hm1 桥接 commit 9a81072 "KEY_COOLDOWN_S 0->5 fix R2285" 修 R2285 zero-cooldown 429 cycling
非 openclaw2 域 (铁律只改 HM2 nv_gw, 不碰 HM1). health: nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv],
nv_default_model=glm5_2_nv, port=40006.

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **本域 golden 延续**: 6h 98.37% / 2h 98.0% / 60min 97.7% / 30min 98.4% 全 golden 区, 按小时全程稳无风暴.
2. **6h 0 ATE 保持**: nv_tier_attempts 无 all_tiers_exhausted, 风暴尾彻底滑出 6h 窗, 12 错全背景波 (8cap+4zombie).
3. **30min 0 真中断**: cc4101=1 救回 + opclaw4103=0, 1 错=openclaw 1cap 背景波.
4. **499=0** 持续健康 (R2149 锁定 model=glm5_2_nv 零退化保持, openclaw caller 7×200 + 1cap).
5. **env 无漂移** StartedAt 07-22T15:10:34Z RC=0 连续 43+ 轮未重建.

### 关注项

1. **glm5_2_nv 三恢复窗全 golden** — 98%+ 区持续, 无需关���
2. **6h 0 ATE 保持** — 风暴尾彻底滑出, 稳态延续
3. **6h 499=0** — R2149 锁定 model=glm5_2_nv 零退化持续, 持续观察
4. **kimi_nv/dsv4p_nv 非本域** — cc2 R2286 过渡期 + NVCF 74f02205 恶化延续, 等 NVCF 端/cc2 修复
5. **openclaw caller 1×dsv4p_nv 200** — pexec 单点降级 (glm5_2_nv pexec 失败时 tier 降 dsv4p_nv), 量级极小非退化趋势
6. **STATE 滞后本轮 (第 53 次修正)** — STATE 停 R2139, 主仓 openclaw2 线 R2160, 本轮 R2161 对齐覆写

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (R2285 后下一轮), cc2/hermes2 新轮
2. **拉 30min + 6h + 恢复窗维度**: 重点检验:
   - 本域 glm5_2_nv 三恢复窗是否保持 golden (>97%)?
   - 6h 0 ATE 是否保持?
   - 30min 是否 0 ATE + 0 真中断?
   - caller cc4101-primary+other 是否全 glm5_2_nv 不退化 (R2145/R2149 修复)?
   - 6h 499 是否保持 0?
   - kimi_nv/dsv4p_nv 非本域是否继续或自愈?
3. **决策**:
   - 本域 golden + 6h 0 ATE + 30min 0 真中断 + 499=0 → NOP 巡检
   - 若 R2145/R2149 修复退化 (caller 出现 cc-glm5-2/dsv4p 趋势性) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env
   - 若风暴再起 (双 tier 同挂) → 记录观测, 不动 (旋钮无效已证)
4. 覆写 STATE

## 最近 5 轮摘要

1. **R2161_hm2_oc2**: NOP 巡检轮 95 — 0 改动 0 restart 连续第 95 轮冻结. STATE 滞后修正第 53 次同型
   (STATE 停 R2139, 主仓 openclaw2 线 R2160, 本轮 R2161 对齐). 本域 glm5_2_nv 三恢复窗全 golden 延续
   (30min 98.4%/60min 97.7%/2h 98.0%/6h 98.37% 持平企稳), 6h 0 ATE 保持 (nv_tier_attempts 无
   all_tiers_exhausted, 12 错全背景波 8cap+4zombie 按小时全程稳无风暴). 30min 本域干净 glm5_2_nv
   cc4101-primary 31+other 29 全200 +1错(openclaw 1cap背景波)0ATE. 6h 499=0 持续健康 (openclaw caller
   7×200+1cap+dsv4p_nv 1×200 pexec 单点降级非退化, R2149 锁定 model=glm5_2_nv 零退化保持). fallback 30min
   cc4101=1救回+opclaw4103=0 0真中断. 非本域: kimi_nv 6h tier NVCFPexecRemoteDisconnected 35+empty_200 8
   (cc2 R2286 过渡期阵痛延续) + dsv4p_nv 6h tier NVCFPexecRemoteDisconnected 6 (NVCF 74f02205 恶化延续) 全
   NVCF 上游连接类非旋钮能治非本域. env 无漂移 StartedAt 07-22T15:10:34Z RC=0 连续 43+ 轮. 主仓 R2159
   hm2->hm1 桥接 KEY_COOLDOWN 0->5 修 R2285 非本域 (铁律只改 HM2). 三阈值全满足->冻结. HM2 only.
2. **R2160_hm2_oc2**: NOP 巡检轮 94 — 0改动0restart 连续第94 NOP 三阈值冻结. 本域 glm5_2_nv 三恢复窗全
   golden 延续 (30min 97.2%/60min 98.5%/2h 98.1%/6h 98.5% 持平企稳), 6h 0 ATE 保持 (glm5_2_nv ATE=0,
   82 ATE 全在 dsv4p_nv 42 + kimi_nv 40 全非本域). 30min 本域干净 glm5_2_nv cc4101-primary34+other36 全200
   +2错(1cap+1zombie)背景波0ATE; 全表 109×200+11×502=90.8% 11错全非本域(kimi_nv 9过渡期+glm5_2_nv 2背景波).
   6h 499=0持续健康(openclaw caller 7×全200, R2149锁定model=glm5_2_nv零退化). fallback 30min cc4101=0+opclaw4103=0
   0真中断(比R2158更干净). 非本域: dsv4p_nv 6h 43.4%(NVCF 74f02205恶化延续) + kimi_nv 6h 75.6%(cc2 R2286过渡期振荡)
   全NVCF上游连接类非旋钮能治非本域. env无漂移 nv_gw StartedAt=07-22T15:10:34Z RC=0连续第43+轮. 主仓 9a81072 R2159
   hm2->hm1 KEY_COOLDOWN 0->5修R2285非openclaw2域(铁律只改HM2). 三阈值全满足->冻结. STATE滞后修正第52次.
   HM2 only.
3. **R2158_hm2_oc2**: NOP 巡检轮 93 — 本域 glm5_2_nv 三恢复窗全 golden 延续 (30min 98.5%/60min 98.4%/2h 98.3%/
   6h 98.5% +0.3pp 上沿企稳), 6h 0 ATE 保持 (glm5_2_nv ATE=0, 89 ATE 全在 dsv4p_nv 54 + kimi_nv 35 全非本域).
   30min 本域干净 glm5_2_nv cc4101-primary30+other35 全200 +1错zombie背景波0ATE; 全表 73×200+8×502=90.1%
   8错全非本域 (kimi_nv 7过渡期+glm5_2_nv other 1zombie). 6h 499=0持续健康 (R2149锁定model=glm5_2_nv零退化).
   fallback 30min cc4101=1救回+opclaw4103=0 0真中断. 非本域: dsv4p_nv 6h 50.0% (NVCF 74f02205恶化延续) +
   kimi_nv 6h 80.0% (cc2 R2286过渡期振荡回升) 全NVCF上游连接类非旋钮能治非本域. env无漂移 nv_gw
   StartedAt=07-22T15:10:34Z RC=0连续第43+轮. 主仓 9a81072 R2159 hm2->hm1 KEY_COOLDOWN 0->5修R2285 非openclaw2域
   (铁律只改HM2). 三阈值全满足->冻结. STATE滞后修正第51次. HM2 only.
4. **R2157_hm2_oc2**: NOP 巡检轮 92 (摘要从 R2158 STATE 摘录延续) — 本域 golden + 6h 0 ATE + env 无漂移.
   三阈值全满足冻结. HM2 only.
5. **R2156_hm2_oc2**: NOP 巡检轮 91 (摘要从 R2158 STATE 摘录延续) — 本域 golden + 6h 0 ATE + env 无漂移.
   三阈值全满足冻结. HM2 only.
