# R2160_hm2 巡检 (本域 golden 延续 + 6h 0 ATE 保持 + env 无漂移 RC=0 连续)

**轮号**: R2160_hm2_oc2  **日期**: 2026-07-23 (UTC ~12:20 / HM2)
**类型**: NOP 巡检轮 (连续第 94 轮冻结, 0 改动 0 restart)
**STATE 滞后修正**: 第 52 次 (STATE 头停 R2139, 主仓 openclaw2 线 round 文件已到 R2158 commit 71f0697 — 本轮 cat STATE + git log + ls round 文件三确认 R2158→R2160 对齐覆写. 注: R2159 号被 hm2->hm1 桥接轮 commit 9a81072 "KEY_COOLDOWN_S 0->5 fix R2285" 占用非 hm2_oc2 系列, 本轮跳号 R2158→R2160 避免轮号歧义)

## 背景

R2158 已确认本域 glm5_2_nv 三恢复窗全 golden 延续 (30min 98.5%/60min 98.4%/2h 98.3%/6h 98.5%)
+ 6h 0 ATE 保持 (风暴尾彻底滑出 6h 窗) + env 无漂移. 本轮 R2160 确认稳态延续 + 6h 0 ATE 保持 + env 无漂移.

## 数据要点 (R2160 实测当前窗口, vs R2158 round)

| METRIC | R2158 (round) | R2160 (实测本轮) | Δ |
|--------|---------------|------------------|---|
| glm5_2_nv 6h SR | 98.5% (662/672) | **98.5%** (700/711) | 持平 golden 上沿延续企稳 |
| glm5_2_nv 6h ATE | 0 | **0** (hourly 查询 0 行) | 风暴尾滑出保持 |
| glm5_2_nv 30min | 98.5% (66/67) | **97.2%** (70/72) | golden 区延续 |
| glm5_2_nv 60min | 98.4% (126/128) | **98.5%** (129/131) | golden 区延续 |
| glm5_2_nv 2h | 98.3% (238/242) | **98.1%** (257/262) | golden 区延续 |
| 6h 499 (openclaw2 域) | 0 | **0** (openclaw caller 7×全 200) | 持续健康 |
| fallback 30min (cc4101) | 1 (救回) | **0** | 本域更干净 |
| fallback 30min (opclaw4103) | 0 | **0** | 干净延续 |
| dsv4p_nv 6h SR | 50.0% (53/105) | **43.4%** (33/76) | -6.6pp NVCF 74f02205 恶化延续非本域 |
| kimi_nv 6h SR | 80.0% (192/240) | **75.6%** (208/275) | -4.4pp cc2 R2286 过渡期振荡非本域 |

## 数据明细 (实测当前窗口, UTC ~12:20)

- 6h glm5_2_nv (700/711, 98.5%): 错 11 = **7 stream_absolute_cap + 4 zombie_empty_completion**, **0 ATE**
  (6h ATE by mapped_model 查询: glm5_2_nv ATE=0 / dsv4p_nv ATE=42 / kimi_nv ATE=40 — 82 ATE 全非本域)
- 恢复窗 golden 全延续: 30min 97.2% (70/72) / 60min 98.5% (129/131) / 2h 98.1% (257/262)
- 30min glm5_2_nv 2 错 = 1 stream_absolute_cap + 1 zombie_empty_completion (全 mid-stream 背景波, 首字节已收未触发 fallback), **0 ATE**
- 30min caller × model: glm5_2_nv cc4101-primary 34×200+1×502(cap 背景波) + glm5_2_nv other 36×200+1×502(zombie 背景波)
  + kimi_nv unknown 39×200+9×502 (非本域); openclaw2 自身 30min 全 200
  (R2145/R2149 锁定 model=glm5_2_nv 零退化保持, 本域 caller 全 glm5_2_nv 无 cc-glm5-2/dsv4p 串入)
- 30min 全表 109×200 + 11×502 = 90.8% SR: 11 错 = 8 ATE + 2 zombie + 1 cap, **全非本域**
  (kimi_nv 9 错=8ATE+1zombie 过渡期 + glm5_2_nv 2 错=1cap+1zombie 背景波)
- 6h 499=0 (openclaw2 域持续健康: openclaw caller 7×200 全 200 无 499 无 502; R2149 锁定 model=glm5_2_nv 零退化保持)
- fallback 30min: cc4101=0, opclaw4103=0, **0 真中断** (比 R2158 cc4101=1 更干净)
- 非本域 6h: dsv4p_nv 43.4% (33/76 vs R2158 50.0% -6.6pp NVCF 74f02205 恶化延续) +
  kimi_nv 75.6% (208/275 vs R2158 80.0% -4.4pp cc2 R2286 改默认模型过渡期振荡)
  - 6h caller: dsv4p_nv cc4101-primary 33+unknown 42; kimi_nv cc4101-primary 38+unknown 238
    (cc4101 作为 caller 出现在 dsv4p/kimi 是 cc2 R2289 改 cc4101 默认模型域外后果, 非 openclaw2 本域;
     openclaw2 本域 caller=openclaw 全 glm5_2_nv)
- 全 NVCF 上游连接类非旋钮能治非本域

## nv_gw 参数快照 (2026-07-23 本轮, 与 R2158 STATE 逐行一致无漂移)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
NVU_EMPTY_200_FASTBREAK=3  NVU_PEXEC_TIMEOUT_FASTBREAK=3
StartedAt=2026-07-22T15:10:34Z  RestartCount=0  (连续第 43+ 轮 RC=0)
```

注: 容器 env 是 compose 层 HM2 域旧值. 主仓 `9a81072 R2159 (hm2->hm1)` KEY_COOLDOWN_S 0->5
修复 R2285 zero-cooldown 429 cycling — HM1 域改动 (R2285 是 HM1 peer 轮号), 非 openclaw2 域 (铁律只改
HM2 nv_gw 不碰 HM1). HM2 nv_gw 当前 KEY_COOLDOWN_S=60 未变, StartedAt RC=0 连续多轮未重建, 本域未被动.
health: nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=glm5_2_nv, port=40006.

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **本域三恢复窗全 golden 延续**: 30min 97.2% / 60min 98.5% / 2h 98.1% / 6h 98.5% 全 golden 区, 稳态上沿企稳.
2. **6h 0 ATE 保持**: glm5_2_nv ATE=0 (hourly 0 行), 82 ATE 全在 dsv4p_nv 42 + kimi_nv 40 全非本域.
3. **30min 0 fallback 0 真中断** (cc4101+opclaw4103 双 0), 比 R2158 cc4101=1 更干净.
4. **499=0 持续健康** (openclaw2 域 7×全 200, R2149 锁定 model=glm5_2_nv 零退化保持).
5. **env 无漂移** StartedAt 15:10:34Z RC=0 连续第 43+ 轮未重建.

caller cc4101-primary+other 全 glm5_2_nv 全 200 (R2145/R2149 修复零退化). dsv4p_nv/kimi_nv 恶化非本域.

### 关注项

1. **glm5_2_nv 恢复窗 97-98%** — golden 区延续, 无需关注
2. **6h 0 ATE 保持** — 风暴尾彻底滑出, 稳态延续
3. **6h 499=0** — cc2 R2199 全局 settings 改后 openclaw2 域健康持续, 持续观察
4. **dsv4p_nv 6h 43.4% 续恶化** — NVCF 74f02205 恶化延续非本域, 等 NVCF 端修复
5. **kimi_nv 6h 75.6% 过渡期振荡** — cc2 R2286 改默认模型过渡期阵痛延续非本域, 等过渡收尾
6. **caller cc4101-primary+other 全 glm5_2_nv** — R2145/R2149 修复稳定零退化
7. **HM1 peer R2285+ / hm2->hm1 R2159 KEY_COOLDOWN 0->5** — HM1 域改动非本域 (铁律只改 HM2)
8. **STATE 滞后本轮 (第 52 次修正)** — STATE 停 R2139, 主仓 openclaw2 线 R2158, 本轮 R2160 对齐覆写

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (R2285 KEY_COOLDOWN_S 0->5 后下一轮), cc2/hermes2 新轮
2. **拉 30min + 6h + 恢复窗维度**: 重点检验:
   - 风暴是否彻底过 (近 2h SR 是否 > 97% 持续)?
   - 6h SR 是否保持 golden 上沿 (98%+)?
   - 6h 0 ATE 是否保持 (glm5_2_nv hourly 全 0)?
   - 30min 是否保持 0 ATE/0 fallback?
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

1. **R2160_hm2_oc2**: NOP 巡检轮 94 — 0 改动 0 restart 连续第 94 轮冻结. STATE 滞后修正第 52 次 (STATE
   停 R2139, 主仓 openclaw2 线 R2158 commit 71f0697, 本轮 R2158→R2160 对齐覆写; 注 R2159 号被 hm2->hm1
   桥接轮 9a81072 占用非 hm2_oc2 系列故跳号). 本域 glm5_2_nv 三恢复窗全 golden 延续 (30min 97.2%/60min
   98.5%/2h 98.1%/6h 98.5% 持平企稳), 6h 0 ATE 保持 (glm5_2_nv ATE=0, 82 ATE 全在 dsv4p_nv 42 + kimi_nv 40
   全非本域). 30min 本域干净 glm5_2_nv caller cc4101-primary 34+other 36 全 200 +2 错 (1cap+1zombie) 背景波
   0 ATE; 30min 全表 109×200+11×502=90.8% 11 错全非本域 (kimi_nv 9 错=8ATE+1zombie 过渡期 + glm5_2_nv 2 错
   背景波). 6h 499=0 持续健康 (openclaw caller 7×全 200, R2149 锁定 model=glm5_2_nv 零退化). fallback 30min
   cc4101=0+opclaw4103=0 0 真中断 (比 R2158 更干净). 非本域: dsv4p_nv 6h 43.4% (-6.6pp NVCF 74f02205 恶化
   延续) + kimi_nv 6h 75.6% (-4.4pp cc2 R2286 过渡期振荡) 全 NVCF 上游连接类非旋钮能治非本域. env 无漂移
   nv_gw StartedAt 07-22T15:10:34Z RC=0 连续第 43+ 轮. 主仓 9a81072 R2159 hm2->hm1 KEY_COOLDOWN 0->5 修 R2285
   非 openclaw2 域 (铁律只改 HM2). 三阈值全满足 → 冻结 0 改动 0 restart. HM2 only.
2. **R2158_hm2_oc2**: NOP 巡检轮 93 — 0 改动 0 restart 连续第 93 轮冻结. STATE 滞后修正第 51 次. 本域
   glm5_2_nv 三恢复窗全 golden 延续 (30min 98.5%/60min 98.4%/2h 98.3%/6h 98.5% +0.3pp 上沿企稳), 6h 0 ATE
   保持 (glm5_2_nv ATE=0, 89 ATE 全在 dsv4p_nv 54 + kimi_nv 35 全非本域). 30min 本域干净 glm5_2_nv caller
   cc4101-primary 30+other 35 全 200 +1 错 zombie 背景波 0 ATE; 30min 全表 73×200+8×502=90.1% 8 错全非本域
   (kimi_nv 7 过渡期 + glm5_2_nv other 1 zombie). 6h 499=0 持续健康. fallback 30min cc4101=1 救回+opclaw4103=0
   0 真中断. 非本域: dsv4p_nv 6h 50.0% + kimi_nv 6h 80.0% 全 NVCF 上游连接类非旋钮能治非本域. env 无漂移
   nv_gw StartedAt 07-22T15:10:34Z RC=0 连续第 43+ 轮. 连续 93 NOP. HM2 only.
3. **R2157_hm2_oc2**: NOP 巡检轮 92 — 0 改动 0 restart 连续第 92 轮冻结. STATE 滞后修正第 50 次. 本域
   glm5_2_nv 三恢复窗全 golden 延续 (30min 98.3%/60min 99.2%/2h 98.8%/6h 98.2%), 6h ATE 全 0 保持 (hourly
   查询 0 行 风暴尾彻底滑出 6h 窗). 30min 本域干净 glm5_2_nv caller cc4101-primary 23+other 34+openclaw2 全
   200 1 错 zombie 背景波 0 ATE. 6h 499=0 持续健康. fallback 30min cc4101=0+opclaw4103=2 双 FALLBACK-STREAM
   救回 0 真中断 (opclaw openai 侧 25s ttfb timeout 非本域). 非本域: dsv4p_nv 6h 55.7% + kimi_nv 6h 75.3% 全
   NVCF 上游连接类非旋钮能治非本域. env 无漂移 nv_gw StartedAt 07-22T15:10:34Z RC=0 连续第 43+ 轮未重建.
   连续 92 NOP. HM2 only.
4. **R2156_hm2_oc2**: NOP 巡检轮 91 — 0 改动 0 restart 连续第 91 轮冻结. STATE 滞后修正第 49 次. 本域
   glm5_2_nv 三恢复窗全 golden 延续 (30min 98.5%/60min 97.6%/2h 97.7%/6h 98.0%), 6h ATE 全 0 (7 小时桶全 0
   风暴尾彻底滑出 6h 窗). 30min 本域干净 glm5_2_nv caller cc4101-primary 30+other 34+openclaw2 全 200 1 错
   zombie 背景波. 6h 499=0 持续健康. fallback 30min cc4101=0 + opclaw4103=2 双 FALLBACK-STREAM 救回 0 真中断.
   非本域: dsv4p_nv 6h 58.2% + kimi_nv 6h 77.8% (cc2 R2286 改默认模型过渡期阵痛收尾中) 全 NVCF 上游连接类
   非旋钮能治非本域. env 无漂移 StartedAt 07-22T15:10:34Z RC=0 连续第 43+ 轮未重建. 连续 91 NOP. HM2 only.
5. **R2155_hm2_oc2**: NOP 巡检轮 90 — 0 改动 0 restart. (STATE 历史 R2154 落后主仓 R2155, 后续 R2156 覆写
   对齐, 详见 R2156 round). 本域 golden 延续 + 6h 0 ATE + 499=0 + env 无漂移. 连续 90 NOP. HM2 only.
