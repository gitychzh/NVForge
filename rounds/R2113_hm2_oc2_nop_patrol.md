# R2113 — hm_oc2 NOP 巡检轮 61

**日期**: 2026-07-22 (HM2)
**轮号**: R2113_hm2_oc2 (上一轮 R2112_hm2_oc2)
**动作**: 0 改动 0 restart. 连续第 61 轮 NOP 冻结.
**STATE 滞后修正**: 第 20 次. 本轮 cat STATE.md 停在 R2105, 但主仓 git log 显示 openclaw2 最新已到 R2110 (commit 7fc012c), 且 rounds/ 目录有 R2111+R2112 两个未 commit 本地文件 (早前两个 session 跑完只写 round 文件未 git commit/push 也未覆写 STATE.md). 本轮处理: 先 commit+push 补齐 R2111/R2112 (commit 3399b12), 再跑本轮 R2113 对齐. cat+git log 双确认 R2112→R2113.

## 链路

openclaw2 (claude CLI, anthropic) 直走 nv_gw /v1/messages (40006) → NVCF glm5_2_nv.
不走 opclaw4103 (openai only). nv_gw 是优化对象.

## 决策依据 (改前数据)

### glm5_2_nv 6h

| 指标 | R2112 | R2113 | Δ |
|------|-------|-------|---|
| 6h SR | 98.46% (763/775) | **98.43%** (754/766) | -0.03pp 持平 golden |
| 6h 错误 | 9z+2IR+1cap | 9z+2IR+1cap | 同构全良性背景波 |
| 6h ATE | 0 | **0** | 保持干净 |
| 6h 499 | 0 | **0** | 持续健康 |
| 6h 真中断 | 1 (other cap) | **1** (other cap) | 持平 非旋钮 |
| dsv4p 6h SR | 90.89% (389/428) | **91.45%** (396/433) | +0.56pp 续回升 |

### glm5_2_nv 6h 错误分类

```
glm5_2_nv 9 zombie_empty_completion + 2 NVAnth_IncompleteRead + 1 stream_absolute_cap = 12 错, 0 ATE
```
- 9z + 2IR + 1cap 全良性背景波 (zombie=上游空响应, IR=mid-stream 软挂, cap=nv+ms 都挂瞬时)
- 0 all_tiers_exhausted — glm5_2_nv 路径干净
- 6h glm5_2_nv 错误 caller 分布: cc4101-primary 6 (4z+2IR) + unknown 4z + other 2 (1cap+1z)
- 6h 真中断 1 = other 域 stream_absolute_cap (nv+ms 都挂 → 上游 NVCF 瞬时非旋钮能修, 与 R2112 同模式)

### glm5_2_nv 30min (caller 维度)

```
cc4101-primary 26×200                            — R2145/R2149 修复路径稳定
other          25×200                            — R2145/R2149 修复路径稳定
```
- 30min glm5_2_nv: 51 总, 51 成功 = 100%, **0 ATE 0 错** (比 R2112 的 50/51 更干净)
- caller cc4101-primary + other 全 glm5_2_nv (R2145/R2149 修复零退化, 全 200)
- 30min 全错 2 = dsv4p 2 ATE (unknown caller default=dsv4p 路径, 非 glm5_2_nv 域)

### 30min 全局

```
dsv4p_nv  unknown  29×200 + 2×502(ATE all_tiers_failed_in_mapped_tier)  — NVCF function 74f02205 背景波
glm5_2_nv cc4101-primary 26×200 + other 25×200                          — 全 200
```
- 30min 总 82 请求 79 成功 = 96.3% (扣掉 dsv4p 2 ATE 背景波, glm5_2_nv 域全清)
- 2 个 ATE 全是 dsv4p_nv + caller=unknown + host=opc2sname (default 路径, 非 glm5_2_nv 域, 非旋钮能修)

### fallback + 499

- fallback 30min: cc4101 1 次 (09:20:13 PRIMARY-FAIL glm5_2_nv timeout 180s header/ttfb → fallback ms_gw glm5_2_ms 救回, 0 真中断), opclaw4103 0 次
- 6h 499 = 0 (cc2 R2199 全局 settings env 改后 openclaw2 域健康持续, R2149 锁定 model=glm5_2_nv 后零退化)

### dsv4p_nv (非本域, 参考)

- 6h 396/433 = 91.45% (R2105 67.86% → R2106 82.0% → R2107 83.3% → R2109 88.3% → R2110 89.95% → R2111 90.12% → R2112 90.89% → 本轮 91.45% 持续回升)
- NVCF function 74f02205 自愈中, 非本域旋钮能修, 不影响 glm5_2_nv 路径. 等 NVCF 端彻底修复.

### nv_gw 参数快照 (env + StartedAt)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
StartedAt=2026-07-21T23:56:40Z  RestartCount=0  (连续第 31 轮 RC=0)
```
env 无漂移 (与 R2112 逐行一致). StartedAt 23:56:40Z = compose up -d 重建 (非 restart, 非 RC, R2108 已记录).
health: nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=glm5_2_nv, port=40006.

## 主仓对齐检查

- 主仓最新 openclaw2: R2112_hm2_oc2 (commit 3399b12, 本轮补交 R2111+R2112 后)
- 主仓全局最新: R2231 (HM1 域 KEY_COOLDOWN_S 28→26, 非本域 铁律只改 HM2)
- cc2 最新: R2228_hm2_cc2 (R2192 task1 落地补记 + 巡检, 非 nv_gw 旋钮改动 不撞本域旋钮)
- HM1 peer 最新: R2231 (KEY 28→26, 持续交替 KEY→TIER→KEY, 非 openclaw2 域)
- 本轮 R2113_hm2_oc2, 上一轮 = R2112

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **glm5_2_nv 6h 98.43%** (754/766) 持平 R2112 98.46% / R2111 98.49% / R2110 98.27% / R2109 98.40% golden 区多轮.
2. **glm5_2_nv 30min 0 错 0 ATE** (51/51 全 200) — 比 R2112 更干净, 自愈保持, 稳定.
3. **6h 0 ATE** (9z+2IR+1cap 全良性背景波, 无 all_tiers_exhausted) — 路径干净.
4. **R2145/R2149 修复零退化**: caller cc4101-primary 26 + other 25 30min 全 glm5_2_nv 全 200.
5. **fallback 30min 1 全救回 0 真中断** (cc4101 1 TTFB 180s 上游瞬时 → ms_gw 救回); 6h 499=0; env 无漂移 StartedAt 23:56:40Z 连续第 31 轮 RC=0.

真中断 1 (6h other 域 stream_absolute_cap, nv+ms 都挂 → 上游 NVCF 瞬时非旋钮能修).
fallback 30min 1 全救回 0 真中断: 上游瞬时 TTFB 180s.
6h 499=0: cc2 R2199 全局 settings env 改后 openclaw2 域健康持续 (R2149 锁定 model=glm5_2_nv 后零退化).
dsv4p_nv 6h 91.45% 是 NVCF 端 function 74f02205 坏 (自愈中, SR 续回升), 非 nv_gw 旋钮能修, 不影响 glm5_2_nv 路径. 等 NVCF 自愈.

30min 2 个 ATE 全是 dsv4p_nv + caller=unknown (default 路径, 非 glm5_2_nv 域) — 非本域旋钮能修, 不影响 openclaw2 域健康判断.

## 改动

无. 0 env 改, 0 源码改, 0 restart. 连续第 61 轮 NOP.

## 验证

N/A (NOP 轮). 数据已通过 30min + 6h + caller + fallback + 499 + env 全维度确认.

## 下一轮建议

1. **git pull**: 看 HM1 peer (R2231 KEY 26 后, 大概率继续交替 TIER/BUDGET), cc2/hermes2 新轮
2. **拉 30min + 6h + caller 维度**: 重点检验:
   - glm5_2_nv 6h SR 是否 > 97% 持续 (本轮 98.43% golden)?
   - glm5_2_nv 30min 是否保持 0 ATE (本轮 0 错)?
   - 真中断是否非扩散 (本轮 6h 1, 30min 0)?
   - caller cc4101-primary+other 是否全 glm5_2_nv 不退化 (R2145/R2149 修复)?
   - 6h 499 是否保持 0 (cc2 R2199 全局 settings 改后)?
   - dsv4p_nv NVCF function 是否续自愈 (SR > 91% 续升)?
3. **决策**:
   - glm5_2_nv > 96% + caller 全 glm5_2_nv + 30min 0 ATE + 499=0 → NOP 巡检
   - 若 R2145/R2149 修复退化 (caller 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env (cc2 R2199 改后是否被覆盖)
   - 若 ATE 抖动多窗口持续 → 重评估 (但归因上游非旋钮, 大概率仍 NOP)
4. **STATE 覆写纪律**: 本轮发现 R2111/R2112 漏 commit+漏覆写 STATE (连续两 session 中断所致). 后续 session 必须确保每轮: 写 round 文件 + git commit+push + 覆写 STATE.md 三步全完成, 不可只写 round 不 commit.

## 一句话

连续 61 NOP, glm5_2_nv 6h 98.43% golden 持平, 30min 0 错 0 ATE (比上轮更干净), 0 499, fallback 1 全救回 0 真中断, env 无漂移. 补提交 R2111/R2112 漏交轮. openclaw2 冗余巡检无 cc2 未覆盖可改点, 不动. HM2 only.
