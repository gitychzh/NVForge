# R2111 — hm2_oc2 NOP 巡检轮 59

**日期**: 2026-07-22 (HM2)
**轮号**: R2111_hm2_oc2 (上一轮 R2110_hm2_oc2)
**动作**: 0 改动 0 restart. 连续第 59 轮 NOP 冻结.
**STATE 滞后修正**: 第 18 次 (STATE.md 停 R2105, 主仓 openclaw2 上轮 R2110 commit 7fc012c, 本轮 cat+git log 双确认 R2110→R2111 对齐).

## 链路

openclaw2 (claude CLI, anthropic) 直走 nv_gw /v1/messages (40006) → NVCF glm5_2_nv.
不走 opclaw4103 (openai only). nv_gw 是优化对象.

## 决策依据 (改前数据)

### glm5_2_nv 6h

| 指标 | R2110 | R2111 | Δ |
|------|-------|-------|---|
| 6h SR | 98.27% (799/813) | **98.49%** (782/794) | +0.22pp golden 略升 |
| 6h 错误 | 11z+2IR+1cap | 9z+2IR+1cap | zombie 11→9 更干净 |
| 6h ATE | 0 | **0** | 保持干净 |
| 6h 499 | 0 | **0** | 持续健康 |
| 6h 真中断 | 1 (other cap) | **1** (other cap) | 持平 非旋钮 |
| dsv4p 6h SR | 89.95% (366/407) | **90.12%** (374/415) | +0.17pp 续回升 |

### glm5_2_nv 6h 错误分类

```
glm5_2_nv 9 zombie_empty_completion + 2 NVAnth_IncompleteRead + 1 stream_absolute_cap = 12 错, 0 ATE
```
- 9z + 2IR + 1cap 全良性背景波 (zombie=上游空响应, IR=mid-stream 软挂, cap=nv+ms 都挂瞬时)
- 0 all_tiers_exhausted — glm5_2_nv 路径干净
- 6h 真中断 1 = other 域 stream_absolute_cap (nv+ms 都挂 → 上游 NVCF 瞬时非旋钮能修, 与 R2110 同模式)

### glm5_2_nv 30min (caller 维度)

```
other       34×200 + 1×502(stream_absolute_cap)   — 背景波
cc4101-primary 18×200                            — R2145/R2149 修复路径稳定
unknown      1×200 + 1×502(zombie)                — 良性背景波
```
- 30min glm5_2_nv: 54 总, 52 成功 = 96.3%, **0 ATE**
- caller cc4101-primary + other 全 glm5_2_nv (R2145/R2149 修复零退化, 全 200)
- 30min 全错 2 = dsv4p 1 ATE (unknown caller default=dsv4p 路径) + glm5_2 1 zombie (unknown 良性背景波)

### fallback + 499

- fallback 30min: cc4101 5 次 (全 FALLBACK-OK 救回, 0 真中断: 4 TTFB 上游瞬时 + 1 unknown), opclaw4103 0
- 6h 499 = 0 (cc2 R2199 全局 settings env 改后 openclaw2 域健康持续, R2149 锁定 model=glm5_2_nv 后零退化)

### dsv4p_nv (非本域, 参考)

- 6h 374/415 = 90.12% (R2105 67.86% → R2106 82.0% → R2107 83.3% → R2109 88.3% → R2110 89.95% → 本轮 90.12% 持续回升)
- NVCF function 74f02205 自愈中, 非本域旋钮能修, 不影响 glm5_2_nv 路径. 等 NVCF 端彻底修复.

### nv_gw 参数快照 (env + StartedAt)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
StartedAt=2026-07-21T23:56:40Z  RestartCount=0  (连续第 29 轮 RC=0)
```
env 无漂移 (与 R2110 逐行一致). StartedAt 23:56:40Z = compose up -d 重建 (非 restart, 非 RC, R2108 已记录).

## 主仓对齐检查

- 主仓最新: R2230 (HM1 域 KEY_COOLDOWN_S 30→28, 非本域 铁律只改 HM2)
- openclaw2 上轮: R2110_hm2_oc2 (commit 7fc012c)
- cc2 最新: R2228_hm2_cc2 (R2192 task1 落地补记 + 巡检, 非 nv_gw 旋钮改动 不撞本域旋钮)
- HM1 peer 最新: R2230 (KEY 30→28, 持续交替 KEY→TIER→KEY, 非 openclaw2 域)
- 本轮 R2111_hm2_oc2, 上一轮 = R2110

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **glm5_2_nv 6h 98.49%** (782/794) 持平 R2110 98.27% / R2109 98.40% / R2108 98.49% / R2107 98.58% golden 区多轮.
2. **glm5_2_nv 30min 0 ATE** (52/54 全 200 除 2 背景波) — 自愈保持, 稳定.
3. **6h 0 ATE** (9z+2IR+1cap 全良性背景波, 无 all_tiers_exhausted) — 路径干净.
4. **R2145/R2149 修复零退化**: caller cc4101-primary 18 + other 34 30min 全 glm5_2_nv 全 200.
5. **fallback 30min 5 全救回 0 真中断** (0 真中断); 6h 499=0; env 无漂移 StartedAt 23:56:40Z 连续第 29 轮 RC=0.

真中断 1 (6h other 域 stream_absolute_cap, nv+ms 都挂 → 上游 NVCF 瞬时非旋钮能修).
fallback 30min 5 全救回 0 真中断: 4 TTFB 180s 上游瞬时 + 1 unknown, 全 FALLBACK-OK.
6h 499=0: cc2 R2199 全局 settings env 改后 openclaw2 域健康持续 (R2149 锁定 model=glm5_2_nv 后零退化).
dsv4p_nv 6h 90.12% 是 NVCF 端 function 74f02205 坏 (自愈中), 非 nv_gw 旋钮能修, 不影响 glm5_2_nv 路径. 等 NVCF 自愈.

## 改动

无. 0 env 改, 0 源码改, 0 restart. 连续第 59 轮 NOP.

## 验证

N/A (NOP 轮). 数据已通过 30min + 6h + caller + fallback + 499 + env 全维度确认.

## 下一轮建议

1. **git pull**: 看 HM1 peer (R2230 KEY 28 后, 大概率继续交替 TIER/BUDGET), cc2/hermes2 新轮
2. **拉 30min + 6h + caller 维度**: 重点检验:
   - glm5_2_nv 6h SR 是否 > 97% 持续 (本轮 98.49% golden)?
   - glm5_2_nv 30min 是否保持 0 ATE (本轮 0)?
   - 真中断是否非扩散 (本轮 6h 1, 30min 0)?
   - caller cc4101-primary+other 是否全 glm5_2_nv 不退化 (R2145/R2149 修复)?
   - 6h 499 是否保持 0 (cc2 R2199 全局 settings 改后)?
   - dsv4p_nv NVCF function 是否续自愈 (SR > 90% 续升)?
3. **决策**:
   - glm5_2_nv > 96% + caller 全 glm5_2_nv + 30min 0 ATE + 499=0 → NOP 巡检
   - 若 R2145/R2149 修复退化 (caller 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env (cc2 R2199 改后是否被覆盖)
   - 若 ATE 抖动多窗口持续 → 重评估 (但归因上游非旋钮, 大概��仍 NOP)

## 一句话

连续 59 NOP, glm5_2_nv 6h 98.49% golden 持平, 0 ATE 0 499, fallback 全救回 0 真中断, env 无漂移. openclaw2 冗余巡检无 cc2 未覆盖可改点, 不动. HM2 only.
