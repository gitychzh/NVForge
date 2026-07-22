# R2115 — hm_oc2 NOP检轮 63

**日期**: 2026-07-22 (HM2)
**轮号**: R2115_hm2_oc2 (上一轮 R2114_hm2_oc2)
**动作**: 0 改动 0 restart. 连续第 63 轮 NOP 冻结.
**STATE 对齐**: 本轮 cat STATE + git log 主仓双确认 STATE 头部停在 R2114 (commit 48de01f), 主仓 openclaw2 最新也 = R2114 — **STATE 已对齐, 无滞后** (上轮 R2114 做了第 21 次滞后修正后首次 STATE 同步). 后续 session 仍必先 cat STATE + git log 主仓 双确认轮号, 防再次滞后.

## 链路

openclaw2 (claude CLI, anthropic) 直走 nv_gw /v1/messages (40006) → NVCF glm5_2_nv.
不走 opclaw4103 (openai only). nv_gw 是优化对象.

## 决策依据 (改前数据)

### glm5_2_nv 6h

| 指标 | R2114 | R2115 | Δ |
|------|-------|-------|---|
| 6h SR | 98.37% (666/677) round / 98.10% (618/630) STATE | **97.96%** (575/587) | -0.41pp/-0.14pp 持平 golden 下沿 |
| 6h 错误 | 8z+2IR+1cap | 8z+4cap | 同构全良性背景波 (IR→cap 换型) |
| 6h ATE | 0 | **0** | 保持干净 |
| 6h 499 | 0 | **0** | 持续健康 |
| 6h 真中断 | 1 (other cap) | **1** (openclaw cap 无 fallback) | 持平 非旋钮 |
| dsv4p 6h SR | 93.18% (437/469) | **93.06%** (456/490) | -0.12pp 平台期持平 |

### glm5_2_nv 6h 错误分类

```
glm5_2_nv 8 zombie_empty_completion + 4 stream_absolute_cap = 12 错, 0 ATE
```
- 8z + 4cap 全良性背景波 (zombie=上游空响应, cap=nv+ms 都挂瞬时)
- 0 all_tiers_exhausted — glm5_2_nv 路径干净
- 6h glm5_2_nv 错误 caller 分布: other 4z+2cap + cc4101-primary 3z + openclaw 2cap + unknown 1z
- 6h 真中断 1 = openclaw 域 stream_absolute_cap 无 fallback (duration 168s, nv+ms 都挂 → 上游 NVCF 瞬时非旋钮能修, 与 R2113/R2114 同模式仅 caller 域不同)
- 6h glm5_2_nv fallback_occurred=t 共 214 (206 救回 200 + 8 仍 502), 路径层 fallback 正常工作

### glm5_2_nv 30min (caller 维度)

```
cc4101-primary 20×200                            — R2145/R2149 修复路径稳定
other          18×200                            — R2145/R2149 修复路径稳定
```
- 30min glm5_2_nv: 38 总, 38 成功 = 100%, **0 ATE 0 错** (比 R2114 round 的 36/36 同样全清, 样本略大)
- caller cc4101-primary + other 全 glm5_2_nv (R2145/R2149 修复零退化, 全 200)
- 30min 全错 2 = dsv4p_nv 2 ATE (unknown caller default=dsv4p 路径, 非 glm5_2_nv 域)

### 30min 全局

```
dsv4p_nv  unknown  42×200 + 2×502(ATE all_tiers_failed_in_mapped_tier)  — NVCF function 74f02205 背景波
glm5_2_nv cc4101-primary 20×200 + other 18×200                          — 全 200
```
- 30min 总 82 请求 80 成功 = 97.6% (扣掉 dsv4p 2 ATE 背景波, glm5_2_nv 域全清)
- 2 个 ATE 全是 dsv4p_nv + caller=unknown + default 路径 (非 glm5_2_nv 域, 非旋钮能修)

### fallback + 499

- fallback 30min: cc4101 **0 次**, opclaw4103 **0 次** — 比 R2114 (cc4101 1 救回) 更干净, 30min 零 fallback
- 6h 499 = 0 (cc2 R2199 全局 settings env 改后 openclaw2 域健康持续, R2149 锁定 model=glm5_2_nv 后零退化)

### dsv4p_nv (非本域, 参考)

- 6h 456×200 + 34×502 = 490, SR 93.06% (R2114 93.18% → -0.12pp 平台期持平)
- 6h ATE 34 (全 unknown caller default 路径, NVCF function 74f02205 自愈中平台期 ~93%, 非本域非旋钮)
- R2105 67.86% → R2109 88.3% → R2113 91.45% → R2114 93.18% → 本轮 93.06%, 回升到 ~93% 平台期, 等 NVCF 端完全自愈

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **glm5_2_nv 6h 97.96%** (575/587) 持平 golden 区下沿 (R2114 98.37%/98.10%, R2113 98.43%, R2112 98.46%, R2111 98.49% 连续多轮 >97.9%).
2. **glm5_2_nv 30min 38/38 全 200 0 错 0 ATE** — 稳定, 比 R2114 round 的 36/36 同样干净 (样本略大 38 vs 36).
3. **6h 0 ATE** (8z+4cap 全良性背景波, 无 all_tiers_exhausted) — 干净.
4. **R2145/R2149 修复零退化**: caller cc4101-primary 20 + other 18 30min 全 glm5_2_nv 全 200.
5. **fallback 30min 0** (比 R2114 的 1 更干净, 零 fallback 零真中断 30min 窗口); env 无漂移 StartedAt 23:56:40Z 连续第 33 轮 RC=0.

真中断 1 (6h openclaw 域 stream_absolute_cap 无 fallback, nv+ms 都挂 → 上游 NVCF 瞬时非旋钮能修). fallback 30min 0.
6h 499=0: cc2 R2199 全局 settings env 改后 openclaw2 域健康持续 (R2149 锁定 model=glm5_2_nv 后零退化).
dsv4p_nv 6h 93.06% 平台期 是 NVCF 端 function 74f02205 自愈中, 非 nv_gw 旋钮能修, 不影响 glm5_2_nv 路径. 等 NVCF 自愈.

### 关注项

1. **glm5_2_nv 6h ~97.96%** — golden 持续区下沿, 无需关注 (连续多轮 >97.9%)
2. **glm5_2_nv 30min 0 错 0 ATE** — 自愈保持, 稳定
3. **真中断 1 (6h)** — openclaw 域 stream_absolute_cap 无 fallback, 上游瞬时非旋钮; 30min 0 真中断
4. **6h 499=0** — cc2 R2199 全局 settings 改后 openclaw2 域健康持续, 持续观察
5. **dsv4p_nv NVCF function 自愈中 (93.06% 平台期)** — 影响 hermes 主 agent, 不影响 cc2/openclaw2. 等 NVCF 端修复.
6. **caller cc4101-primary+other 全 glm5_2_nv** — R2145/R2149 修复稳定零退化
7. **HM1 peer R2232-R2235 KEY_COOLDOWN 20→12 (-8s 五轮)** — 非 openclaw2 域 (铁律只改 HM2)
8. **STATE 本轮已对齐 (无滞后)** — 上轮 R2114 做第 21 次修正后首次 STATE 同步. 后续 session 仍必先 cat STATE + git log 主仓 双确认轮号.

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (R2235 KEY 12 后下一轮, 大概率交替 TIER/BUDGET), cc2/hermes2 新轮
2. **拉 30min + 6h + caller 维度**: 重点检验:
   - glm5_2_nv 6h SR 是否 > 97% 持续 (本轮 97.96% golden 下沿)?
   - glm5_2_nv 30min 是否保持 0 ATE 0 错 (本轮 38/38 全清)?
   - 真中断是否非扩散 (本轮 6h 1, 30min 0)?
   - caller cc4101-primary+other 是否全 glm5_2_nv 不退化 (R2145/R2149 修复)?
   - 6h 499 是否保持 0 (cc2 R2199 全局 settings 改后)?
   - dsv4p_nv NVCF function 是否继续自愈 (SR 平台期 ~93% 能否突破)?
3. **决策**:
   - glm5_2_nv > 96% + caller 全 glm5_2_nv + 30min 0 ATE 0 错 + 499=0 → NOP 巡检
   - 若 R2145/R2149 修复退化 (caller 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env (cc2 R2199 改后是否被覆盖)
   - 若 ATE 抖动多窗口持续 → 重评估 (但归因上游非旋钮, 大概率仍 NOP)
4. 覆写 STATE

## nv_gw 参数快照 (2026-07-22 本轮, 与 R2114 逐行一致无漂移)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
StartedAt=2026-07-21T23:56:40Z  RestartCount=0  (连续第 33 轮 RC=0)
```

注: 容器 env 是 compose 层旧值 (HM2 域). HM1 peer R2232-R2235 全 HM1 域 (KEY 20→18→16→14→12), 非 openclaw2 域
(铁律只改 HM2 nv_gw, 不碰 HM1). health: nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=glm5_2_nv, port=40006.

## 一句话总结

连续第 63 轮 NOP 冻结. STATE 本轮已对齐无滞后 (上轮 R2114 做第 21 次修正后首次同步). glm5_2_nv 6h 97.96% (575/587 持平 golden 下沿, R2114 98.37%/98.10%), 8z+4cap 0 ATE 0 499, 30min 38/38 全 200 0 错 0 ATE (cc4101-primary 20+other 18 全 glm5_2_nv). 6h 真中断 1 (openclaw cap 无 fallback 非旋钮). fallback 30min 0 (比 R2114 更干净). dsv4p_nv 6h 93.06% 平台期 (NVCF 74f02205 自愈中 非本域). R2145/R2149 修复零退化. env 无漂移 StartedAt 23:56:40Z 连续第 33 轮 RC=0. HM1 peer R2232-R2235 KEY 20→12 非本域. HM2 only.
