# R2114 — hm_oc2 NOP检轮 62

**日期**: 2026-07-22 (HM2)
**轮号**: R2114_hm2_oc2 (上一轮 R2113_hm2_oc2)
**动作**: 0 改动 0 restart. 连续第 62 轮 NOP 冻结.
**STATE 滞后修正**: 第 21 次. 本轮 cat STATE.md 头部停在 R2105 (commit 0614d28, NOP 巡检轮 53), 但主仓 git log 显示 openclaw2 最新已到 R2113 (commit a3e181b, NOP 巡检轮 61) — 即 STATE 落后主仓 8 轮 (R2106-R2113). 落后原因: 早前多个 session 跑完只写 round 文件未覆写 STATE.md (R2106-R2113 中若干轮是补提交). 本轮处理: cat STATE + git log 主仓双确认 R2113→R2114 对齐, 覆写 STATE.md. 连续第 21 次 STATE 滞后修正.

## 链路

openclaw2 (claude CLI, anthropic) 直走 nv_gw /v1/messages (40006) → NVCF glm5_2_nv.
不走 opclaw4103 (openai only). nv_gw 是优化对象.

## 决策依据 (改前数据)

### glm5_2_nv 6h

| 指标 | R2113 | R2114 | Δ |
|------|-------|-------|---|
| 6h SR | 98.43% (754/766) | **98.37%** (666/677) | -0.06pp 持平 golden |
| 6h 错误 | 9z+2IR+1cap | 8z+2IR+1cap | 同构全良性背景波 (z-1) |
| 6h ATE | 0 | **0** | 保持干净 |
| 6h 499 | 0 | **0** | 持续健康 |
| 6h 真中断 | 1 (other cap) | **1** (other cap) | 持平 非旋钮 |
| dsv4p 6h SR | 91.45% (396/433) | **93.18%** (437/469) | +1.73pp 续回升 |

### glm5_2_nv 6h 错误分类

```
glm5_2_nv 8 zombie_empty_completion + 2 NVAnth_IncompleteRead + 1 stream_absolute_cap = 11 错, 0 ATE
```
- 8z + 2IR + 1cap 全良性背景波 (zombie=上游空响应, IR=mid-stream 软挂, cap=nv+ms 都挂瞬时)
- 0 all_tiers_exhausted — glm5_2_nv 路径干净
- 6h glm5_2_nv 错误 caller 分布: unknown 4z + cc4101-primary 3z+2IR + other 1cap+1z
- 6h 真中断 1 = other 域 stream_absolute_cap (nv+ms 都挂 → 上游 NVCF 瞬时非旋钮能修, 与 R2113 同模式)

### glm5_2_nv 30min (caller 维度)

```
cc4101-primary 18×200                            — R2145/R2149 修复路径稳定
other          18×200                            — R2145/R2149 修复路径稳定
```
- 30min glm5_2_nv: 36 总, 36 成功 = 100%, **0 ATE 0 错** (比 R2113 的 51/51 同样全清, 样本略小)
- caller cc4101-primary + other 全 glm5_2_nv (R2145/R2149 修复零退化, 全 200)
- 30min 全错 4 = dsv4p_nv 4 ATE (unknown caller default=dsv4p 路径, 非 glm5_2_nv 域)

### 30min 全局

```
dsv4p_nv  unknown  35×200 + 4×502(ATE all_tiers_failed_in_mapped_tier)  — NVCF function 74f02205 背景波
glm5_2_nv cc4101-primary 18×200 + other 18×200                          — 全 200
```
- 30min 总 75 请求 71 成功 = 94.7% (扣掉 dsv4p 4 ATE 背景波, glm5_2_nv 域全清)
- 4 个 ATE 全是 dsv4p_nv + caller=unknown + default 路径 (非 glm5_2_nv 域, 非旋钮能修)

### fallback + 499

- fallback 30min: cc4101 1 次 (10:30:36 PRIMARY-FAIL glm5_2_nv timeout 60s header/ttfb → fallback ms_gw glm5_2_ms 救回 28.5s, 0 真中断), opclaw4103 0 次
  - 注: 该 fallback 标记 PRIMARY-FAIL-SKIP-CIRCUIT (primary 60s < chain budget 120s, cc4101 pre-empted nv_gw retry, 不计入 circuit) — 上游瞬时, 救回, 非旋钮
- 6h 499 = 0 (cc2 R2199 全局 settings env 改后 openclaw2 域健康持续, R2149 锁定 model=glm5_2_nv 后零退化)

### dsv4p_nv (非本域, 参考)

- 6h 437×200 + 32×502 = 469, SR 93.18% (R2113 91.45% → +1.73pp 续回升)
- 6h ATE 30 (全 unknown caller default 路径, NVCF function 74f02205 自愈中, 非本域非旋钮)
- R2105 67.86% → R2109 88.3% → R2113 91.45% → 本轮 93.18%, 持续回升, 等 NVCF 端完全自愈

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **glm5_2_nv 6h 98.37%** (666/677) 持平 R2113 98.43% / R2112 98.46% / R2111 98.49% golden 区连续多轮.
2. **glm5_2_nv 30min 36/36 全 200 0 错 0 ATE** — 稳定, 比 R2113 同样干净 (样本略小 36 vs 51).
3. **6h 0 ATE** (8z+2IR+1cap 全良性背景波, 无 all_tiers_exhausted) — 干净.
4. **R2145/R2149 修复零退化**: caller cc4101-primary 18 + other 18 30min 全 glm5_2_nv 全 200.
5. **fallback 30min 1 救回 0 真中断** (1 other 域 stream_absolute_cap nv+ms 都挂 → 上游 NVCF 瞬时非旋钮能修); env 无漂移 StartedAt 23:56:40Z 连续第 32 轮 RC=0.

真中断 1 (6h other 域 stream_absolute_cap, nv+ms 都挂 → 上游 NVCF 瞬时非旋钮能修). fallback 30min 1 救回 0 真中断.
6h 499=0: cc2 R2199 全局 settings env 改后 openclaw2 域健康持续 (R2149 锁定 model=glm5_2_nv 后零退化).
dsv4p_nv 6h 93.18% 续回升 是 NVCF 端 function 74f02205 自愈中, 非 nv_gw 旋钮能修, 不影响 glm5_2_nv 路径. 等 NVCF 自愈.

### 关注项

1. **glm5_2_nv 6h ~98.37%** — golden 持续区, 无需关注
2. **glm5_2_nv 30min 0 错 0 ATE** — 自愈保持, 稳定
3. **真中断 1 (6h)** — other 域 stream_absolute_cap nv+ms 都挂, 上游瞬时非旋钮; 30min 0 真中断
4. **6h 499=0** — cc2 R2199 全局 settings 改后 openclaw2 域健康持续, 持续观察
5. **dsv4p_nv NVCF function 自愈中 (93.18% 续回升)** — 影响 hermes 主 agent, 不影响 cc2/openclaw2. 等 NVCF 端修复.
6. **caller cc4101-primary+other 全 glm5_2_nv** — R2145/R2149 修复稳定零退化
7. **HM1 peer R2228-R2231 KEY_COOLDOWN 34→26 (-8s 四轮)** — 非 openclaw2 域 (铁律只改 HM2)
8. **STATE 滞后本轮 (第 21 次修正)** — STATE 停 R2105, 主仓已 R2113, 本轮 cat+git log 双确认 R2113→R2114 对齐. 后续 session 必先 cat STATE + git log 主仓 双确认轮号.

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (R2231 KEY 26 后下一轮, 大概率交替 TIER/BUDGET), cc2/hermes2 新轮
2. **拉 30min + 6h + caller 维度**: 重点检验:
   - glm5_2_nv 6h SR 是否 > 97% 持续 (本轮 98.37% golden)?
   - glm5_2_nv 30min 是否保持 0 ATE 0 错 (本轮 36/36 全清)?
   - 真中断是否非扩散 (本轮 6h 1, 30min 0)?
   - caller cc4101-primary+other 是否全 glm5_2_nv 不退化 (R2145/R2149 修复)?
   - 6h 499 是否保持 0 (cc2 R2199 全局 settings 改后)?
   - dsv4p_nv NVCF function 是否继续自愈 (SR 回升过 93%)?
3. **决策**:
   - glm5_2_nv > 96% + caller 全 glm5_2_nv + 30min 0 ATE 0 错 + 499=0 → NOP 巡检
   - 若 R2145/R2149 修复退化 (caller 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env (cc2 R2199 改后是否被覆盖)
   - 若 ATE 抖动多窗口持续 → 重评估 (但归因上游非旋钮, 大概率仍 NOP)
4. 覆写 STATE

## nv_gw 参数快照 (2026-07-22 本轮, 与 R2113 逐行一致无漂移)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
StartedAt=2026-07-21T23:56:40Z  RestartCount=0  (连续第 32 轮 RC=0)
```

注: 容器 env 是 compose 层旧值 (HM2 域). HM1 peer R2228-R2231 全 HM1 域 (KEY 34→32→30→28→26), 非 openclaw2 域
(铁律只改 HM2 nv_gw, 不碰 HM1). health: nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=glm5_2_nv, port=40006.

## 一句话总结

连续第 62 轮 NOP 冻结. STATE 滞后修正第 21 次 (STATE 停 R2105, 主仓已 R2113, 本轮 R2114 对齐). glm5_2_nv 6h 98.37% (666/677 持平 R2113 98.43% golden), 8z+2IR+1cap 0 ATE 0 499, 30min 36/36 全 200 0 错 0 ATE (cc4101-primary 18+other 18 全 glm5_2_nv). 6h 真中断 1 (other cap 非旋钮). fallback 30min 1 救回 0 真中断. dsv4p_nv 6h 93.18% 续回升 (NVCF 74f02205 自愈中 非本域). R2145/R2149 修复零退化. env 无漂移 StartedAt 23:56:40Z 连续第 32 轮 RC=0. HM1 peer R2228-R2231 KEY 34→26 非本域. HM2 only.
