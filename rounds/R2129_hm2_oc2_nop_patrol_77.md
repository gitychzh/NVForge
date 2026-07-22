# R2129 — hm2_oc2 轮

**日期**: 2026-07-23 (HM2, UTC 20:34)
**轮号**: R2129_hm2_oc2 (上一轮 R2128_hm2_oc2, commit d10634d)
**动作**: 0 改动 0 restart. 连续第 77 轮 NOP 冻结.

## STATE 对齐检查

cat STATE + git log 主仓双确认: STATE 头部 = R2125 (commit be54525, NOP 巡检轮 73), 但主仓 git log
显示 openclaw2 最新已到 R2128 (commit d10634d, NOP 巡检轮 76) — 即 STATE 落后主仓 3 轮 (R2126-R2128).
落后原因同型: 早前 session 跑完只写 round 文件 commit, 未覆写 STATE.md (R2126/R2127/R2128 round 已 commit,
但 STATE 仍停 R2125). 本轮补: cat STATE + git log 主仓双确认 R2128→R2129, 用当前实测数据覆写 STATE.
**STATE 滞后修正第 33 次**. **后续 session 必先 cat STATE + git log 主仓 双确认轮号**, 避免再次滞后.

## 数据要点 (R2129 实测当前窗口, vs R2128)

| METRIC | R2128 (round) | R2129 (实测本轮) | Δ |
|--------|---------------|------------------|---|
| glm5_2_nv 6h SR | 95.46% (631/661) | **95.69%** (621/649) | +0.23pp 持平 golden 上沿 |
| glm5_2_nv 30min | 69/69 全 200 0错 | **58/59** 全 200 1错 0 ATE | 持平样本略减 1 背景波 |
| 30min ATE (glm5_2_nv) | 0 | **0** | 自愈保持 |
| 6h glm5_2_nv ATE | 1 | **0** | 改善 (无 all_tiers_exhausted) |
| 6h 499 (openclaw2 域) | 0 | **0** | 持续健康 |
| fallback 30min | 1 救回 | **0** (cc4101+opclaw4103 双 0) | 改善 最干净 |
| dsv4p_nv 6h SR | 41.86% (54/129) | **41.54%** (54/130) | -0.32pp 续跌非本域 |

## 数据明细 (实测当前窗口, UTC 20:34)

- glm5_2_nv 6h (621/649, 95.69%): 错 28 = 18zombie + 6stream_absolute_cap + 3NVAnth_IncompleteRead + **1 stream_no_content_gap** (新变体单发背景波)
- glm5_2_nv 6h **ATE=0** (无 all_tiers_exhausted, vs R2128 1 ATE 改善 — 精确 count error_type='all_tiers_exhausted' AND request_model='glm5_2_nv'=0)
- glm5_2_nv 30min (58/59 全 200, 1错 0 ATE): caller cc4101-primary 29×200+1×502 + other 29×200 全 glm5_2_nv 全 200
- 30min 1 错明细: cc4101-primary 1 stream_no_content_gap (mid-stream empty content 背景波, 首字节已收未触发 cc4101→ms_gw fallback)
- 30min 全错 8 = dsv4p_nv 7 ATE (unknown caller default 路径非本域, all_tiers_exhausted, NVCF function 74f02205 恶化延续) + glm5_2_nv 1 (stream_no_content_gap 背景波)
- glm5_2_nv 6h caller: cc4101-primary 347×200+13×502 + other 267×200+12×502 + openclaw 5×200+2×502 + unknown 4×200+1×502 — 全 glm5_2_nv 无 cc-glm5-2/dsv4p 串入 (R2145/R2149 修复零退化)
- 6h 499=0 (openclaw2 域 caller=other/cc4101-primary 无 499): cc2 R2199 全局 settings env 改后持续健康 (R2149 锁定 model=glm5_2_nv 后零退化)
- fallback 30min 0: cc4101 grep "FALLBACK-OK|切到 ms_gw"=0 + opclaw4103 grep "FALLBACK-STREAM|FALLBACK "=0 — 30min 无 egress 级 ms_gw 切换, 0 真中断
- 6h 真中断: zombie 18 + stream_absolute_cap 6 + IR 3 全上游非旋钮 (30min 0 真中断, 1 错为 stream_no_content_gap 背景波未触发 fallback)

## nv_gw 参数快照 (2026-07-23 本轮, 与 R2128 STATE 逐行一致无漂移)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180  NVU_BIG_INPUT_THRESHOLD=250000
NVU_EMPTY_200_FASTBREAK=3 (compose R824 旧值, R2127/R2128 STATE 已列, 非漂移)
StartedAt=2026-07-22T15:10:34Z  RestartCount=0  (连续第 39 轮 RC=0)
```

注: 容器 env 是 compose 层旧值 (HM2 域). HM1 peer R2271/R2272/R2273 全 HM1 域 (TIER_TIMEOUT_BUDGET_S 192→222→234 + dsv4p TIER_BUDGET 150→160
多轮连调运行时改非 compose), 非 openclaw2 域 (铁律只改 HM2 nv_gw, 不碰 HM1). HM2 容器 TIER_TIMEOUT_BUDGET_S=180 (compose). health:
nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=glm5_2_nv, port=40006, proxy_role=passthrough, nv_num_keys=5.

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **glm5_2_nv 6h 95.69%** (621/649) vs R2128 95.46% +0.23pp 企稳 golden 上沿 (R2121-R2128 92.95→94.14→94.04→94.36→94.15→94.39→95.07→95.46→95.69 回升轨迹稳).
2. **glm5_2_nv 30min 58/59 全 200 0 ATE** — 1 错为 stream_no_content_gap 背景波 (首字节已收未触发 fallback), caller cc4101-primary+other 全 glm5_2_nv 全 200, R2145/R2149 修复零退化.
3. **6h ATE=0** (vs R2128 1 ATE 改善, 精确 count=0; 背景波已退散).
4. **R2145/R2149 修复零退化**: glm5_2_nv 6h caller cc4101-primary+other+openclaw+unknown 全 glm5_2_nv 无 cc-glm5-2/dsv4p 串入.
5. **fallback 30min 0 救回 0 真中断** (cc4101+opclaw4103 双 0, 比 R2128 的 1 更干净); env 无漂移 StartedAt 15:10:34Z 连续第 39 轮 RC=0.

真中断全上游 zombie/cap/IR 瞬时非旋钮能修 (stream_absolute_cap nv+ms 都挂 → 上游 NVCF 瞬时).
fallback 30min 0 — 最干净窗口.
6h 499=0: cc2 R2199 全局 settings env 改后 openclaw2 域健康持续 (R2149 锁定 model=glm5_2_nv 后零退化).
dsv4p_nv 6h 41.54% 续跌 是 NVCF 端 function 74f02205 恶化延续, 非 nv_gw 旋钮能修, 不影响 glm5_2_nv 路径. 等 NVCF 自愈.
stream_no_content_gap 新变体单发 (mid-stream empty content) 背景波量级非结构性, 持续观察是否多窗口重现.

### 关注项

1. **glm5_2_nv 6h ~95.69%** — golden 上沿持续区, 无需关注
2. **glm5_2_nv 30min 58/59 0 ATE** — 自愈保持, 稳定
3. **6h ATE=0 (改善 vs R2128 1)** — 背景波退散, 30min 0 ATE
4. **6h 499=0** — cc2 R2199 全局 settings 改后 openclaw2 域健康持续, 持续观察
5. **dsv4p_nv NVCF function 恶化延续 (41.54% 续跌)** — 影响 hermes 主 agent, 不影响 cc2/openclaw2. 等 NVCF 端修复.
6. **caller cc4101-primary+other 全 glm5_2_nv** — R2145/R2149 修复稳定零退化
7. **stream_no_content_gap 新变体单发** — 背景波量级, 持续观察是否多窗口重现
8. **HM1 peer R2271/R2272/R2273 TIER_TIMEOUT_BUDGET/dsv4p TIER_BUDGET 多轮连调** — 非 openclaw2 域 (铁律只改 HM2)
9. **STATE 滞后本轮 (第 33 次修正)** — STATE 停 R2125, 主仓已 R2128, 本轮 R2129 对齐覆写.

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (R2273 dsv4p TIER_BUDGET 160 后下一轮), cc2/hermes2 新轮
2. **拉 30min + 6h + caller 维度**: 重点检验:
   - glm5_2_nv 6h SR 是否 > 93% 持续 (本轮 95.69% golden 上沿)?
   - glm5_2_nv 30min 是否保持 0 ATE (本轮 58/59 0 ATE)?
   - 6h ATE 是否保持 0 (本轮改善至 0)?
   - caller cc4101-primary+other 是否全 glm5_2_nv 不退化 (R2145/R2149 修复)?
   - 6h 499 是否保持 0 (cc2 R2199 全局 settings 改后)?
   - stream_no_content_gap 是否多窗口重现 (本轮单发背景波)?
   - dsv4p_nv NVCF function 是否恶化停止/自愈 (本轮 41.54% 续跌)?
3. **决策**:
   - glm5_2_nv > 93% + caller 全 glm5_2_nv + 30min 0 ATE + 499=0 → NOP 巡检
   - 若 R2145/R2149 修复退化 (caller 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env (cc2 R2199 改后是否被覆盖)
   - 若 stream_no_content_gap 多窗口持续 → 重评估 (但归因上游 mid-stream 非旋钮, 大概率仍 NOP)
   - 若 ATE 抖动多窗口持续 → 重评估 (但归因上游非旋钮, 大概率仍 NOP)
4. 覆写 STATE
