# R2116 — hm_oc2 NOP检轮 64

**日期**: 2026-07-22 (HM2)
**轮号**: R2116_hm2_oc2 (上一轮 R2115_hm2_oc2)
**动作**: 0 改动 0 restart. 连续第 64 轮 NOP 冻结.
**STATE 对齐**: 本轮 cat STATE + git log 主仓双确认 STATE 头部停在 R2114 (commit 48de01f), 但主仓 openclaw2 最新已到 R2115 (commit cb5b475, 上轮补提交). STATE 落后主仓 1 轮 — 上轮 R2115 同型跑完只写 round 文件未覆写 STATE. 本轮补覆写 STATE 对齐 R2116. **STATE 滞后修正第 22 次同型**. 后续 session 必先 cat STATE + git log 主仓 双确认轮号, 防再次滞后.

## 链路

openclaw2 (claude CLI, anthropic) 直走 nv_gw /v1/messages (40006) → NVCF glm5_2_nv.
不走 opclaw4103 (openai only). nv_gw 是优化对象.

## 决策依据 (改前数据)

### glm5_2_nv 6h

| 指标 | R2115 | R2116 (实测) | Δ |
|------|-------|--------------|---|
| 6h SR | 97.96% (575/587) | **96.74%** (475/491) | -1.22pp golden 下沿波动 |
| 6h 错误 | 8z+4cap | 7z+5cap+2IR+1ATE+1no_content_gap | 同构全良性背景波 (ATE 回 1 个) |
| 6h ATE | 0 | **1** (cc4101-primary all_tiers_exhausted) | +1 (1 个 ATE 上游瞬时) |
| 6h 499 | 0 | **0** | 持续健康 |
| 6h 真中断 | 1 (openclaw cap) | 5 (stream_absolute_cap) | 量级波动 (nv+ms 都挂 非旋钮) |
| dsv4p 6h SR | 93.06% (456/490) | **74.89%** (173/231) | -18pp 下跌 (NVCF 74f02205 恶化) |

### glm5_2_nv 6h 错误分类

```
glm5_2_nv 7 zombie_empty_completion + 5 stream_absolute_cap + 2 NVAnth_IncompleteRead + 1 all_tiers_exhausted + 1 stream_no_content_gap = 16 错
```
- 7z + 5cap + 2IR + 1no_content_gap 全良性背景波 (zombie=上游空响应, cap=nv+ms 都挂瞬时, IR=上游读断, no_content_gap=流无内容)
- 1 all_tiers_exhausted (cc4101-primary 域, 单个 ATE 上游瞬时, 非旋钮能修 — HM1 域 R2243+ 在调 BUDGET/KEY 针对此类但铁律只改 HM2)
- 6h glm5_2_nv 错误 caller 分布: other 5z+2cap+1IR+1no_gap + cc4101-primary 3cap+1IR+1ATE+1z + unknown 1z
- 6h 真中断 5 = stream_absolute_cap (nv+ms 都挂 → 上游 NVCF 瞬时非旋钮能修, 与 R2114/R2115 同模式仅量级波动)
- 6h glm5_2_nv fallback_occurred 路径层 fallback 正常工作 (5cap 无 fallback 救回=真中断, 其余背景波被救回)

### glm5_2_nv 30min (caller 维度)

```
cc4101-primary 34×200                            — R2145/R2149 修复路径稳定
other          31×200                            — R2145/R2149 修复路径稳定
unknown         2×200                            — R2145/R2149 修复路径稳定
```
- 30min glm5_2_nv: 67 总, 67 成功 = 100%, **0 ATE 0 错** (比 R2115 的 38/38 同样全清, 样本更大)
- caller cc4101-primary + other + unknown 全 glm5_2_nv (R2145/R2149 修复零退化, 全 200)
- 30min 全错 4 = dsv4p_nv 4 ATE (unknown caller default=dsv4p 路径, 非 glm5_2_nv 域)

### 30min 全局

```
dsv4p_nv  unknown  19×200 + 4×502(ATE all_tiers_exhausted)  — NVCF function 74f02205 背景波 (恶化)
glm5_2_nv cc4101-primary 34×200 + other 31×200 + unknown 2×200  — 全 200
```
- 30min 总 92 请求 88 成功 = 95.7% (扣掉 dsv4p 4 ATE 背景波, glm5_2_nv 域全清)
- 4 个 ATE 全是 dsv4p_nv + caller=unknown + default 路径 (非 glm5_2_nv 域, 非旋钮能修)

### fallback + 499

- fallback 30min: cc4101 **0 次**, opclaw4103 **0 次** — 持平 R2115 的零 fallback, 30min 零 fallback
- 6h 499 = 0 (cc2 R2199 全局 settings env 改后 openclaw2 域健康持续, R2149 锁定 model=glm5_2_nv 后零退化)

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **glm5_2_nv 6h 96.74%** (475/491) 仍在 golden 下沿 (>96% 阈值), 持平 R2115 97.96%/R2114 98.10%/R2113 98.43% golden 区连续多轮.
2. **glm5_2_nv 30min 67/67 全 200 0 错 0 ATE** — 稳定, 比 R2115 的 38/38 同样干净 (样本 67 vs 38).
3. **6h 1 ATE** (cc4101-primary 域 all_tiers_exhausted, 单个上游瞬时) — 30min 0 ATE 自愈保持.
4. **R2145/R2149 修复零退化**: caller cc4101-primary 34 + other 31 + unknown 2 30min 全 glm5_2_nv 全 200.
5. **fallback 30min 0 救回 0 真中断** (5cap 真中断是 nv+ms 都挂 → 上游 NVCF 瞬时非旋钮); env 无漂移 StartedAt 23:56:40Z 连续第 34 轮 RC=0.

真中断 5 (6h stream_absolute_cap, nv+ms 都挂 → 上游 NVCF 瞬时非旋钮能修).
fallback 30min 0 (比 R2115 的 0 持平更干净).
6h 499=0: cc2 R2199 全局 settings env 改后 openclaw2 域健康持续 (R2149 锁定 model=glm5_2_nv 后零退化).
dsv4p_nv 6h 74.89% 下跌 是 NVCF 端 function 74f02205 恶化中, 非本域非旋钮, 不影响 glm5_2_nv 路径. 等 NVCF 自愈.

## nv_gw 参数快照 (2026-07-22 本轮, 与 R2115 逐行一致无漂移)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
NVU_BIG_INPUT_THRESHOLD=250000  NVU_BIG_INPUT_MODELS=glm5_2_nv
StartedAt=2026-07-21T23:56:40Z  RestartCount=0  (连续第 34 轮 RC=0)
```

注: 容器 env 是 compose 层旧值 (HM2 域). HM1 peer R2243-R2249 全 HM1 域单参 (BUDGET_GLM5_2 34→48/FASTBREAK 2→1/KEY 10→8/BIG_INPUT 去掉 dsv4p/BUDGET_DSV4P 96→102), 非 openclaw2 域 (铁律只改 HM2 nv_gw, 不碰 HM1). health: nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=glm5_2_nv, port=40006.

## 关注项

1. **glm5_2_nv 6h ~96.74%** — golden 下沿波动, >96% 阈值仍稳, 持续观察
2. **glm5_2_nv 30min 0 错 0 ATE** — 自愈保持, 稳定
3. **6h 1 ATE (cc4101-primary)** — 单个 all_tiers_exhausted 上游瞬时, 30min 0 ATE, 非旋钮
4. **6h 真中断 5 (stream_absolute_cap)** — nv+ms 都挂 上游瞬时非旋钮; 30min 0 真中断
5. **6h 499=0** — cc2 R2199 全局 settings 改后 openclaw2 域健康持续, 持续观察
6. **dsv4p_nv NVCF function 恶化 (74.89% 跌)** — 影响 hermes 主 agent, 不影响 cc2/openclaw2. 等 NVCF 端修复.
7. **caller cc4101-primary+other 全 glm5_2_nv** — R2145/R2149 修复稳定零退化
8. **HM1 peer R2243-R2249 单参连续调 (BUDGET/FASTBREAK/KEY/BIG_INPUT/BUDGET_DSV4P)** — 非 openclaw2 域 (铁律只改 HM2)
9. **STATE 滞后本轮 (第 22 次修正)** — STATE 停 R2114, 主仓已 R2115, 本轮补覆写 R2116 对齐. 后续 session 必先 cat STATE + git log 主仓 双确认轮号.

## 下一步

1. **git pull**: 看 HM1 peer (R2249 BUDGET_DSV4P 102 后下一轮, 大概率交替 GLM5_2 BUDGET/KEY 或收口), cc2/hermes2 新轮
2. **拉 30min + 6h + caller 维度**: 重点检验:
   - glm5_2_nv 6h SR 是否 > 96% 持续 (本轮 96.74% golden 下沿)?
   - glm5_2_nv 30min 是否保持 0 ATE 0 错 (本轮 67/67 全清)?
   - 6h ATE 是否不扩散 (本轮 1, 30min 0)?
   - caller cc4101-primary+other 是否全 glm5_2_nv 不退化 (R2145/R2149 修复)?
   - 6h 499 是否保持 0 (cc2 R2199 全局 settings 改后)?
   - dsv4p_nv NVCF function 是否止跌回升 (本轮 74.89% 跌)?
3. **决策**:
   - glm5_2_nv > 96% + caller 全 glm5_2_nv + 30min 0 ATE 0 错 + 499=0 → NOP 巡检
   - 若 R2145/R2149 修复退化 (caller 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env (cc2 R2199 改后是否被覆盖)
   - 若 glm5_2_nv 6h SR 跌破 96% + ATE 扩散多窗口持续 → 重评估 (但归因上游非旋钮, 大概率仍 NOP)
4. 覆写 STATE
