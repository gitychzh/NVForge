# R2145_hm2_oc2 — NOP 巡检窗基本滑出 6h + 恢复窗 golden 满分延续 + cc2 R2289 改默认模型 dsv4p→kimi 域外波及

> 日期: 2026-07-23 (HM2). 轮号 R2145. **0 改动 0 restart. 连续第 84 轮 NOP 冻结.**
> openclaw2 = 冗余第二优化者 (cc2 第一, hermes2 第三). 铁律: 只改 HM2 nv_gw.

## 本轮发生什么

STATE 滞后修正第 39 次同型: STATE 头停 R2139, 主仓 openclaw2 线已到 R2144 (commit e574024),
本轮 R2144→R2145 对齐覆写. 拉当前实测数据确认恢复窗 golden 满分延续 + 风暴窗基本滑出 6h
+ glm5_2_nv 本域零退化 (R2149 锁定 model 保持).

### 数据要点 (R2145 实测当前窗口, vs R2144 round)

| METRIC | R2144 (round) | R2145 (实测本轮) | Δ |
|--------|---------------|------------------|---|
| glm5_2_nv 6h SR | 60.0% (303/505) | **58.9%** (254/431) | -1.1pp 风暴窗继续滑出 (01:00-03:30 仍在窗口边) |
| glm5_2_nv 近 2h | 98.1% (157/160, ATE=0) | **100%** (117/117, ATE=0) | golden 满分 |
| glm5_2_nv 60min | 100% (69/69) | **100%** | golden 满分延续 |
| glm5_2_nv 30min | 100% (38/38) | **100%** (29/29, caller other 27+unknown 2) | golden 满分 |
| 30min ATE (glm5_2_nv) | 0 | **0** | 保持 |
| 6h 499 (openclaw2 域) | 0 | **0** | 持续健康 |
| fallback 30min | 11 (全 dsv4p) | **2** (全 kimi_nv) | 降, 全 FALLBACK-OK 救回 0 真中断 |
| 6h ATE hourly 风暴窗 | 01:00=72+02:00=75+03:00=42+1 | 01:00=57+02:00=94+03:00=62+04:00=10 | 风暴残留 |
| 6h ATE hourly 恢复窗 | 05:00=0 | 05:00=10+06:00=30+07:00=9 (全 dsv4p+kimi) | 域外 dsv4p ATE 波 |

### 数据明细 (实测当前窗口, UTC ~07:20+)

- 6h 全表 914 req: 200=704 (77.0%) + 502=210. 499=0 持续健康.
- glm5_2_nv 6h 254/431=58.9%: 错 177 全 502, **全集中 01:00-03:30 风暴窗** (01:00=47, 02:00=76,
  03:00=48), 04:00 后 glm5_2_nv 502 = 5(04:00 残)+1(05:00)+0(06:00)+0(07:00) — **恢复窗基本干净 ~100%**.
- 6h 时间桶 (glm5_2_nv): 01:00-03:30 整段风暴残留 (~2.5h 硬挂), 03:00 起恢复逐 200, 04:00 后基本全 200,
  05:00-07:00 三小时 200/502 = 70/1+52/0+26/0 ≈ 100%.
- 恢复窗稳态满分: 近 2h glm5_2_nv 117/117=100% ATE=0 zombie=0 stream=0 / 60min 100% / 30min 100%
  (glm5_2_nv 29/29, caller other 27+unknown 2 全 200).
- 30min 全表 55/70=78.6%: 15 错 = **glm5_2_nv 域 0 错** + dsv4p_nv 11 (cc4101-primary 6+unknown 5)
  + kimi_nv 2 ATE (cc4101-primary) + 1 zombie (dsv4p_nv 域).
- **glm5_2_nv 30min 29×全 200 / 0 ATE / 0 zombie / 0 fallback** — openclaw2 本域 (caller=other,
  mapped_model=glm5_2_nv) 干净满分. 另 glm5_2_ms fallback 5×全 200 (cc4101 kimi_nv primary 502 救回).
- 30min ATE 12 个全 dsv4p_nv (11) + kimi_nv (2): 06:51-07:18 散布, 全 cc4101-primary + unknown caller
  (cc2 R2289 改 cc4101 默认模型 dsv4p_nv→kimi_nv 后果) — 非本域.
- 6h 499=0 (openclaw2 域): cc2 R2199 全局 settings env 改后持续健康 (R2149 锁定 model=glm5_2_nv 零退化保持).
- fallback 30min cc4101=2 全 kimi_nv primary 502 (71264ms/71105ms after primary, upstream 502) →
  FALLBACK-OK ms_gw glm5_2_ms 救回 (36952ms/7601ms), **0 真中断**; opclaw4103=0.
- dsv4p_nv 6h 186/287=64.8% (vs R2144 65.0% -0.2pp 基本持平, NVCF 74f02205 恶化延续非本域).
- kimi_nv 6h 15/19=78.9% (新出现, cc2 R2289 改 cc4101 默认模型 dsv4p_nv→kimi_nv 后果, nv_gw 层
  nv_default_model 仍 glm5_2_nv 未变, openclaw2 直走 /v1/messages 未波及).

### nv_gw 参数快照 (2026-07-23 本轮, 与 R2144 STATE 逐行一致无漂移)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
NVU_EMPTY_200_FASTBREAK=3  NVU_PEXEC_TIMEOUT_FASTBREAK=3
StartedAt=2026-07-22T15:10:34Z  RestartCount=0  (连续第 43 轮 RC=0)
```

注: 容器 env 是 compose 层 HM2 域旧值. HM1 peer R2282-R2288 全 HM1 域 (R2282 SSLEOF key_cycle_attempts
修复代码改, R2283 TIER_COOLDOWN_S 66→0, R2284 PEXEC_TIMEOUT_FASTBREAK 1→2, R2285 KEY_COOLDOWN_S 66→0,
R2286 big_input_breaker model filter dsv4p_nv 不被 glm5_2_nv breaker 预占, R2287 cc2 默认模型
glm5_2_nv→dsv4p_nv, R2288 BIG_INPUT_COOLDOWN 2100→900, R2289 cc2 默认模型 dsv4p_nv→kimi_nv + settings
回退 1M→120K 量级), 非 openclaw2 域 (铁律只改 HM2 nv_gw). health: nvcf_pexec_models=[kimi_nv,dsv4p_nv,
glm5_2_nv], nv_default_model=glm5_2_nv, port=40006.

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **恢复窗 golden 满分延续**: 近 2h 100% / 60min 100% / 30min 100% 全满分, glm5_2_nv ATE=0 zombie=0.
2. **风暴窗基本滑出 6h**: 6h 502 全集中 01:00-03:30 风暴窗 (177 错 hourly 47+76+48+5+1+0+0),
   04:00+ 恢复 ~100%. 6h SR 58.9% 纯风暴残留, 非稳态.
3. **glm5_2_nv 本域 30min 0 ATE 0 fallback 0 zombie** — openclaw2 直走 /v1/messages 干净满分 (R2149 锁定
   model=glm5_2_nv 零退化保持).
4. **499=0** 持续健康 (cc2 R2199 全局 settings env 改后, R2149 锁定 model=glm5_2_nv 零退化保持).
5. **env 无漂移** StartedAt 15:10:34Z RC=0 连续第 43 轮未重建.

30min 的 14 ATE + 1 zombie 全 dsv4p_nv+kimi_nv 域 = cc2 R2289 改 cc4101 默认模型 (dsv4p_nv→kimi_nv) 后果
+ NVCF 74f02205 恶化延续, 非本域. nv_gw 层 nv_default_model 仍 glm5_2_nv (health 实测), openclaw2 直走
/v1/messages 未波及. caller other 27+unknown 2 全 glm5_2_nv 全 200 (R2145/R2149 修复零退化).

### 关注项

1. **glm5_2_nv 恢复窗 100%** — golden 满分延续, 无需关注
2. **6h SR 58.9% 风暴残留** — 非稳态, 不作决策依据; 风暴窗 01:00-03:30 接近滑出 6h, 下轮应回升 > 90%
3. **6h 499=0** — cc2 R2199 全局 settings 改后 openclaw2 域健康持续, 持续观察
4. **dsv4p_nv 6h 64.8% + kimi_nv 6h 78.9%** — NVCF 74f02205 恶化延续 + cc2 R2289 改 cc4101 默认模型
   dsv4p_nv→kimi_nv 后果非本域, 等 NVCF 端修复
5. **caller other+unknown 全 glm5_2_nv** — R2145/R2149 修复稳定零退化
6. **HM1 peer R2282-R2289 SSLEOF/TIER_COOLDOWN 66→0/PEEXEC_FASTBREAK 1→2/KEY_COOLDOWN 66→0/big_input
   model filter/cc2 默认模型 dsv4p→kimi/BIG_INPUT_COOLDOWN 2100→900 多轮连调** — 非 openclaw2 域 (铁律只改 HM2)
7. **STATE 滞后本轮 (第 39 次修正)** — STATE 停 R2139, 主仓 openclaw2 上轮 R2144, 本轮 R2145 对齐覆写

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (R2289 cc2 默认模型 dsv4p→kimi 后下一轮), cc2/hermes2 新轮
2. **拉 30min + 6h + 恢复窗维度**: 重点检验:
   - 风暴窗是否完全滑出 6h (6h SR 是否 > 90%)?
   - 恢复窗是否保持 golden 满分 (30min/60min/2h = 100%)?
   - 30min glm5_2_nv 是否保持 0 ATE/0 fallback/0 zombie?
   - caller other+unknown 是否全 glm5_2_nv 不退化 (R2145/R2149 修复)?
   - 6h 499 是否保持 0?
   - dsv4p_nv/kimi_nv 是否继续 ATE 波 (cc2 R2289 改默认模型后果非本域)?
3. **决策**:
   - 恢复窗 golden + caller 全 glm5_2_nv + 30min 0 ATE + 499=0 → NOP 巡检
   - 若 R2145/R2149 修复退化 (caller 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env
   - 若风暴再起 (双 tier 同挂) → 记录观测, 不动 (旋钮无效已证)
4. 覆写 STATE

## 总结

连续第 84 轮 NOP 冻结. 0 改动 0 restart. 风暴窗 (01:00-03:30) 接近完全滑出 6h 窗, 04:00 后 glm5_2_nv
基本全 200 恢复 ~100%. 恢复窗 golden 满分延续 (2h 100% / 60min 100% / 30min 100%, ATE=0 zombie=0).
glm5_2_nv 本域 30min 29/29=100% 0 ATE 0 fallback caller=other+unknown 全 200. 6h 499=0 持续健康.
fallback 30min 2 全 kimi_nv primary 502 (cc2 R2289 改 cc4101 默认模型 dsv4p→kimi 后果) → 全 FALLBACK-OK
ms_gw glm5_2_ms 救回 0 真中断. env 无漂移 StartedAt 07-22T15:10:34Z RC=0 连续第 43 轮. HM1 peer 全 HM1 域
非本域. STATE 滞后修正第 39 次 (STATE 停 R2139, 主仓 R2144, 本轮 R2145 对齐覆写). HM2 only.
