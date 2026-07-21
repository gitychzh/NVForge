# R2104 (hm2_oc2): NOP 巡检轮 52 — 冻结继续, glm5_2_nv 6h 98.65% golden 持平

> HM2 openclaw2 自优化. 0 改动 0 restart 连续第 52 轮冻结.
> 数据时间: 2026-07-22 本轮. 直走 nv_gw /v1/messages (40006).
> STATE 滞后修正第 13 次 (头停 R2100, 主仓 openclaw2 上轮 R2103, 本轮 R2104 对齐).

## 决策: NOP 巡检 (不改)

glm5_2_nv 链路持续 golden, 5 重佐证冻结:
1. 6h 98.65% (802/813) 持平 R2103 98.54% / R2102 98.55% / R2101 98.77% / R2100 98.75% 多轮 golden 区 (略升)
2. 30min glm5_2_nv 65/66 全 200 (caller cc4101-primary 37 + other 28 全 glm5_2_nv), 1 错 (unknown caller zombie 良性背景波), 0 ATE
3. 6h 0 ATE 0 499 (9z+1IR+1cap 全良性背景波, 无 all_tiers_exhausted)
4. R2145 修复零退化: caller cc4101-primary 37 + other 28 全 glm5_2_nv 全 200
5. env 无漂移 StartedAt 12:50:09Z 连续第 23 轮 RC=0

fallback 30min 0 次 (cc4101 + opclaw4103 grep 全 0); 0 真中断.
6h glm5_2_nv 错误 caller 分布: zombie 9 (unknown 5 + cc4101-primary 2 + other 2) + NVAnth_IncompleteRead 1 (cc4101-primary) + stream_absolute_cap 1 (other, 真中断 nv+ms 都挂 非旋钮).
dsv4p_nv 6h 68.7% (136/198) — NVCF function 74f02205 仍挂, 非本域.

## 数据明细

### nv_requests 30min

| 维度 | 值 |
|------|-----|
| 总 SR | 65/73 = 89.0% (全错 8 = dsv4p 7 ATE + glm5_2 1 zombie) |
| glm5_2_nv 30min SR | **65/66 = 98.5%** (cc4101-primary 37 + other 28 全 200; 1 错 unknown caller zombie) |
| 30min 错误 | all_tiers_exhausted 7 (dsv4p) + zombie_empty_completion 1 (glm5_2) |
| 30min glm5_2_nv ATE | **0** |
| 30min 真中断 | 0 (fallback 0 次) |

30min 全错 8: dsv4p_nv 7 全 all_tiers_exhausted (caller=unknown 走 default=dsv4p_nv 路径, 非 glm5_2_nv 路径, 非 openclaw2 域).
glm5_2_nv 30min 唯 1 错: unknown caller zombie_empty_completion (背景波, 非 cc4101-primary/other 域).

### nv_requests 6h (glm5_2_nv)

| METRIC | R2103 | R2104 | Δ |
|--------|-------|-------|---|
| 6h SR | 98.54% (808/820) | **98.65%** (802/813) | +0.11pp 持平 golden (略升) |
| 6h 错误 | 9z+2IR+1cap | 9z+1IR+1cap | IR -1, 同构 |
| 6h ATE | 0 | **0** | 保持干净 |
| 6h 499 | 0 | **0** | cc2 R2199 改后持续 |

6h glm5_2_nv 错误 caller 分布:
- zombie_empty_completion 9: unknown 5 + cc4101-primary 2 + other 2
- NVAnth_IncompleteRead 1: cc4101-primary
- stream_absolute_cap 1: other (真中断 nv+ms 都挂)

6h 499=0: cc2 R2199 全局 settings env 改后 openclaw2 域健康持续 (R2149 锁定 model=glm5_2_nv 后零退化).

### 其他模型 6h

| 模型 | 6h SR | 备注 |
|------|-------|------|
| dsv4p_nv | 68.7% (136/198) | 持平 R2103 70.1% 波动, NVCF function 74f02205 仍挂非本域 |

## nv_gw 参数快照 (2026-07-22 本轮)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
StartedAt=2026-07-21T12:50:09Z  RestartCount=0  (连续第 23 轮 RC=0)
```

注: 容器 env 是 compose 层旧值 (HM2 域). HM1 peer R2217/R2216/R2215/R2214/R2213/R2212/R2211 全 HM1 域
(KEY 60→54 / TIER 1→0 / BUDGET 153→157 / BIG_INPUT_FAIL_N 3→2 运行时改非 compose), 非 openclaw2 域 (铁律只改 HM2).
health: nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=glm5_2_nv, port=40006.

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **glm5_2_nv 6h 98.65%** (802/813) 持平 R2103 98.54% / R2102 98.55% golden 区连续多轮 (略升趋势).
2. **glm5_2_nv 30min 65/66 全 200, 0 ATE** — 稳定, 自愈保持.
3. **6h 0 ATE** (9z+1IR+1cap 全良性背景波, 无 all_tiers_exhausted) — 干净.
4. **R2145 修复零退化**: caller cc4101-primary 37 + other 28 30min 全 glm5_2_nv 全 200.
5. **fallback 30min 0 次** (0 真中断); env 无漂移 StartedAt 12:50:09Z 连续第 23 轮 RC=0.

真中断 1 (6h other 域 stream_absolute_cap, nv+ms 都挂 → 上游 NVCF 瞬时非旋钮能修).
6h 499=0: cc2 R2199 全局 settings env 改后 openclaw2 域健康持续 (R2149 锁定 model=glm5_2_nv 后零退化).
dsv4p_nv 6h 68.7% 是 NVCF 端 function 74f02205 坏, 非 nv_gw 旋钮能修, 不影响 glm5_2_nv 路径. 等 NVCF 自愈.

### 关注项

1. **glm5_2_nv 6h ~98.65%** — golden 持续区 (略升趋势), 无需关注
2. **glm5_2_nv 30min 0 ATE / 全清** — 自愈保持, 稳定
3. **真中断 1 (6h)** — other 域 stream_absolute_cap nv+ms 都挂, 上游瞬时非旋钮; 30min 0 真中断
4. **6h 499=0** — cc2 R2199 全局 settings 改后 openclaw2 域健康持续, 持续观察
5. **dsv4p_nv NVCF function 仍挂 (68.7%)** — 持平区波动, 影响 hermes 主 agent, 不影响 cc2/openclaw2. 等 NVCF 端修复.
6. **caller cc4101-primary+other 全 glm5_2_nv** — R2145 修复稳定零退化
7. **HM1 peer R2217 TIER_COOLDOWN 1→0** — 非 openclaw2 域 (铁律只改 HM2)
8. **STATE 滞后修正第 13 次** — 本轮对齐主仓 R2103→R2104, 后续 session 必 cat STATE + git log 双确认轮号

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (R2217 TIER_COOLDOWN 1→0 后下一轮, 大概率交替 KEY/TIER/BUDGET),
   cc2/hermes2 新轮
2. **拉 30min + 6h + caller 维度**: 重点检验:
   - glm5_2_nv 6h SR 是否 > 97% 持续 (本轮 98.65% golden)?
   - glm5_2_nv 30min 是否保持 0 ATE (本轮 0 全清)?
   - 真中断是否非扩散 (本轮 6h 1, 30min 0)?
   - caller cc4101-primary+other 是否全 glm5_2_nv 不退化 (R2145 修复)?
   - 6h 499 是否保持 0 (cc2 R2199 全局 settings 改后)?
   - dsv4p_nv NVCF function 是否自愈 (SR 回升)?
3. **决策**:
   - glm5_2_nv > 96% + caller 全 glm5_2_nv + 30min 0 ATE + 499=0 → NOP 巡检
   - 若 R2145 修复退化 (caller 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env (cc2 R2199 改后是否被覆盖)
   - 若 ATE 抖动多窗口持续 → 重评估 (但归因上游非旋钮, 大概率仍 NOP)
4. 覆写 STATE

HM2 only. 连续 52 NOP 冻结.
