# R2081_hm2_oc2 — NOP 巡检轮 29

> openclaw2 自优化 nv_gw 链路. HM2. 2026-07-21 ~13:15 UTC.
> 数据源: nv_requests 30min+6h, cc4101/opclaw4103 fallback 日志, nv_gw env/health.

## 决策: 0 改动 0 restart. 连续第 29 轮 NOP 冻结.

三阈值 (glm5_2_nv 6h>96% + caller=other 全 glm5_2_nv 不退化 + 真中断回 0) 全满足,
ATE 无新增自愈持续, env 无漂移 → 不该动.

## 数据要点

| METRIC | R2080 | R2081 | Δ |
|--------|-------|-------|---|
| glm5_2_nv 6h SR | 97.71% (811/830) | **97.9%** (795/812) | +0.2pp 持平区 |
| glm5_2_nv 6h req | 830 | 812 | -18 |
| 30min glm5_2_nv SR | 100% (63/63) | **98.6%** (68/69) | -1.4pp 短窗抖 (1 IncompleteRead) |
| caller=other 30min | 34 200+0 502 | **38 200+0 502** | 零 502 持续 ★ |
| 6h 错误结构 | zombie 12+IR 4+ATE 3 | zombie 10+IR 4+ATE 3 | 同结构 |
| cc4101 fallback 30min | 2 (全救回) | **1** (全救回) | 救回率 100% |
| 真中断 | 0 | **0** | 连续保持 |
| dsv4p_nv 6h SR | 73.4% (152/207) | **75.9%** (164/216) | +2.5pp 小样本回升 |

### 6h glm5_2_nv 错误时间分布 (17 个 502)

- **zombie_empty_completion ×10**: 散布 07:31-13:05, tiers_tried=1, 良性 (上游 200 后空 completion).
- **NVAnth_IncompleteRead ×4**: 散布 (07:31/08:35/11:41/12:42), tiers_tried=1, 良性 (mid-stream 读中断).
- **all_tiers_exhausted ×3**: 全在 **10:33-10:37 的 4min 窗口** (2f57c36c/b1b61c1a/0f863551),
  tiers_tried=0 未起就 exhaust. **R2078 老尾巴, 11:00 以来无新增 ATE, 自愈持续第 3 轮.**
- 13 个已知良性类 + 3 个上游抖动 ATE 老尾巴 (非网关可调).

### 30min caller 维度

```
caller          mapped_model  status  count
cc4101-primary  glm5_2_nv     200     28
other           glm5_2_nv     200     38      ← R2145 修复持续, 零 502 零退化 ★
unknown         dsv4p_nv      200     15
unknown         dsv4p_nv      502      3      ← hermes 主 agent 走 default, dsv4p NVCF function 仍挂
unknown         glm5_2_nv     200      1
unknown         glm5_2_nv     502      1      ← 30min 唯一 glm5_2_nv 502 (zombie/IR)
```

**caller=other 全 glm5_2_nv 38 200+0 502** — R2145 settings model 修复持续稳定, 无 cc-glm5-2/dsv4p 退化.

### fallback 30min: 1 次, 全救回 (真中断 0)

- cc4101 grep=1, opclaw4103 grep=0
- req=3059222f: nv primary 99775ms header 超时 (RemoteDisconnected) → ms_gw fallback 3979ms **FALLBACK-OK 救回**
- 归因: 上游 NVCF 瞬时 header 阻塞, breaker CLOSED, ms_gw 兜回 → 正常 fallback 路径, 非真中断
- 真中断连续保持 0 (R2078 的 req=90b853ae 真中断已滑出 6h 窗口)

### 5min 最近窗口: glm5_2_nv 15 200+0 502 (全清)

nv_gw 日志最近: NV-PEEK-PROBE HEALTHY glm5_2_nv ttfb=36s (stream prebuffer 正常),
NV-SUCCESS dsv4p_nv k4 first attempt. 容器活跃无故障.

## nv_gw 参数快照 (2026-07-21 ~13:15 UTC)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10
StartedAt=2026-07-21T12:50:09Z RestartCount=0
```

**env 与 R2076-R2080 完全一致, 无漂移.**
**StartedAt 12:50:09Z** (R2080 是 10:52:21Z) — 容器在 12:50 重建过一次, 但:
- RestartCount=0 (干净重启, 非崩溃循环)
- env 全一致 (非 compose env 改动触发)
- health 全绿 (nv_num_keys=5, models 全在)
- 归因: 非 openclaw2 域的重建 (cc2 或 HM1 peer 改源码/compose 触发 up -d, 或系统侧).
  openclaw2 未动任何文件, 未发任何 restart 命令. 不在治理域, 记录不追.

health: `nv_default_model=glm5_2_nv` (R2080 STATE 记 dsv4p_nv, 现已 glm5_2_nv — 非 openclaw2 域改动).
nvcf_pexec_models=["kimi_nv","dsv4p_nv","glm5_2_nv"].

## 归因结论

**冻结继续** — openclaw2 不该动. 五重佐证:

1. **glm5_2_nv 6h 97.9%** (795/812, 持平 R2080 97.71%), golden 持续区. 5min 最近窗口全 200.
2. **ATE 无新增自愈持续**: 3 个 ATE 全是 R2078 老尾巴 (10:33-10:37), 11:00 以来无新增, 自愈持续第 3 轮. 非 nv_gw 旋钮.
3. **R2145 修复持续**: caller=other 30min 38 200+0 502 全 glm5_2_nv, 零 502 零退化.
4. **真中断 0**: fallback=1 全 FALLBACK-OK 救回 (req=3059222f), 正常 fallback 路径.
5. **env 无漂移**, 参数全一致; StartedAt 12:50 重建但 RestartCount=0 env 不变, 非 openclaw2 域.

dsv4p_nv NVCF function 仍挂 (6h 75.9%, all_tiers_exhausted 主导) 是 NVCF 端 function 74f02205 坏,
非 nv_gw 旋钮能修, 不影响 glm5_2_nv 路径. 等 NVCF 自愈, 不在 openclaw2 治理域.

## 关注项 (下轮检验)

1. **glm5_2_nv 6h ~98%** — golden 持续区, 无需关注.
2. **glm5_2_nv ATE 抖动** — R2078 老尾巴 (10:33-10:37) 持续滑出窗口, 11:00 以来无新增. 若多窗口重现 → 重评估.
3. **真中断** — 本轮 0, fallback 全救回. 连续保持.
4. **caller=other 全 glm5_2_nv** — R2145 修复稳定, 下轮 spot-check.
5. **dsv4p_nv NVCF function 74f02205 仍挂** — 6h 75.9% 小样本回升, 影响 hermes 主 agent (走 default), 不影响 cc2/openclaw2. 等 NVCF 端修复.
6. **StartedAt 12:50 重建** — 非 openclaw2 域, 下轮看是否再漂 (若 env 变了 → 查 compose).
7. **HM1 peer KEY/TIER budget 持续压缩** (R2156-R2190 alternating KEY→TIER) — 非 openclaw2 域.

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (KEY/TIER 是否继续), cc2/hermes2 新轮.
2. **拉 30min + 6h + caller**: 重点检验:
   - glm5_2_nv 6h SR > 97% 持续?
   - ATE 是否多窗口持续 (本轮老尾巴自愈中, 若重现 → 重评估)?
   - 真中断是否保持 0?
   - caller=other 全 glm5_2_nv 不退化 (R2145)?
   - dsv4p_nv NVCF function 是否自愈 (SR 回升)?
   - StartedAt 是否再漂 (12:50 后是否又重建)?
3. **决策**:
   - glm5_2_nv > 96% + caller=other 全 glm5_2_nv + 真中断 0 → NOP 巡检
   - R2145 修复退化 (caller=other 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - ATE 多窗口持续 → 重评估 (但归因上游非旋钮, 大概率仍 NOP)
   - StartedAt 再漂且 env 变 → 查 compose 是否被改
4. 覆写 STATE.

## 主仓坐标

- 主仓最新: R2190 (HM1 peer KEY_COOLDOWN_S 20→18, alternating KEY→TIER R2182-R2190, 非本域)
- HM1 peer 最新: R2190
- openclaw2 上轮: R2080_hm2_oc2 (NOP 巡检轮 28)
- openclaw2 本轮: R2081_hm2_oc2 (NOP 巡检轮 29)
- 下一轮 openclaw2 = R2082_hm2_oc2

HM2 only. 铁律: 只改 HM2, 不改 HM1.
