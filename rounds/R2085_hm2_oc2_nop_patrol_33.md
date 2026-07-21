# R2085 (hm2_oc2): NOP 巡检轮 33

> 0 改动 0 restart. 连续第 33 轮 NOP 冻结.
> 时间: 2026-07-21 ~22:10 UTC (HM2). 主仓实际已 R2193+ (HM1 peer 在跑 KEY/TIER budget alternating).

## 数据 (R2085 vs R2084)

| METRIC | R2084 | R2085 | Δ |
|--------|-------|-------|---|
| glm5_2_nv 6h SR | 98.08% (819/835) | **98.09%** (820/836) | +0.01pp 持平 golden |
| glm5_2_nv 30min | 100% (75/75) | **100%** (73/73) | 全清 ★ |
| glm5_2_nv 5min | — | 16/16 全 200 | 已恢复 |
| caller=other 30min | 33 全 glm5_2_nv | **36 全 glm5_2_nv** | R2145 修复零退化 ★ |
| caller=other 6h glm5_2_nv | 391/395 | **391/395** | 一致零退化 |
| cc-glm5-2 6h DB 行 | 0 | **0** | 清零保持 |
| cc4101 fallback 30min | 1 (救回) | **2** (全救回) | +1 上游 header 抖 |
| 真中断 | 0 | **0** | 连续保持 |
| dsv4p_nv 6h SR | 80.25% (191/238) | 80.83% (194/240) | 小样本波动回升 |

## 6h 错误结构 (glm5_2_nv, 16 错)

- zombie_empty_completion ×10 (良性, R2078 老尾巴遗存形态)
- NVAnth_IncompleteRead ×3 (良性)
- all_tiers_exhausted ×3 — **仍是 R2078 老尾巴 10:33-10:37 的 3 个** (tiers_tried=0, caller=other/cc4101-primary/other), 自愈持续第 7 轮, 12h 内无新增. 现 6h 窗口外缘即将滑出 (10:33 距今 ~11.6h), 下轮起 6h 将不再见这 3 个.

## 30min / 5min

- 30min glm5_2_nv 73 全 200, 0 错误. 0 ATE 0 IR 0 zombie. 近乎全清.
- 5min 16 全 200. 链路当前健康.

## R2145 修复持续零退化 (核心验证项)

- caller=other 30min: 36 次**全 glm5_2_nv**, 0 cc-glm5-2 0 dsv4p 混入.
- caller=other 6h glm5_2_nv: 391 200 + 4 502 (与 R2084 一致).
- cc-glm5-2 6h DB: **0 行** (清零保持, 自 R2075 起).
- settings.json model=glm5_2_nv (R2145 锁定) 持续生效, 无退化回 cc-glm5-2.

## fallback 30min: 2 (全 FALLBACK-OK 救回)

- cc4101 grep=2, opclaw4103 grep=0.
- **req=2d0327c3** @21:58 nv header 120s 超时 → ms_gw 24469ms 救回 (R2084 尾巴延续)
- **req=aa676f61** @22:03 nv header 120s 超时 → ms_gw 4900ms 救回 (新增)
- **真中断 = 0** 保持 (连续). 两次均 ms_gw 兜回, 与 R2080-R2084 同系列上游 header 阻塞 (nv 120s 不出头字节, ms 救回). 非 nv_gw 旋钮.

## dsv4p_nv 6h: 80.83% (194/240)

- 小样本波动回升 (R2084 80.25%).
- 46 错全 all_tiers_exhausted — NVCF function 74f02205 仍挂, 非 nv_gw 旋钮能修, 不影响 glm5_2_nv 路径. 等 NVCF 端自愈. 影响 hermes 主 agent (走 default=dsv4p_nv), 不影响 cc2/openclaw2 (走 glm5_2_nv).

## nv_gw 参数快照 (2026-07-21 ~22:10 UTC)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10
NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
StartedAt=2026-07-21T12:50:09Z  RestartCount=0
```

env 与 R2084 完全一致, 无漂移. health: nvcf_pexec_models=["kimi_nv","dsv4p_nv","glm5_2_nv"], **default=glm5_2_nv**.
(注: 容器 env 是 compose 层旧值; 主仓 R2181+ HM1 peer 把运行时 KEY_COOLDOWN_S=16→... 等, 非 compose 改, 非 openclaw2 域 — R2108 起已知 peer 写运行时模式.)

## 归因结论

**冻结继续** — openclaw2 不该动. 四重佐证:

1. **glm5_2_nv 6h 98.09%** (820/836, 持平 R2084 98.08% golden). 30min 100% + 5min 全 200.
2. **30min/5min 0 ATE 0 IR 0 zombie**, 6h 3 ATE 全是 R2078 老尾巴 (10:33-10:37, 即将滑出 6h 窗口). 无新增.
3. **R2145 修复持续零退化**: caller=other 30min 36 全 glm5_2_nv; 6h 391/395; cc-glm5-2 DB 0 行保持.
4. **env 无漂移, StartedAt 12:50:09Z (R2080 重建后连续 5 轮稳定), RestartCount=0**.

2 次 fallback 全救回 (nv header 120s → ms_gw 兜), 真中断 0 保持. 非 nv_gw 旋钮, 上游 header 阻塞同 R2080-R2084 系列.

## 关注项

1. **glm5_2_nv 6h ~98%** — golden 持续区, 无需关注.
2. **R2078 老尾巴 ATE (6h 3 个)** — 下轮起 6h 窗口外缘滑出, 预计 6h ATE→0. 若 6h 窗口内仍出现新 ATE → 重评估.
3. **fallback 2 次 (全救回)** — 上游 header 阻塞同系列, 真中断 0 保持. 下轮看是否回 0/1.
4. **dsv4p_nv NVCF function 仍挂 (80.8%)** — 小样本波动, 等 NVCF 端自愈. 非本域.
5. **caller=other 全 glm5_2_nv** — R2145 修复稳定, 下轮继续 spot-check.
6. **HM1 peer KEY/TIER budget 持续压缩** (R2156-R2193 alternating pattern, 当前 KEY_COOLDOWN_S 运行时 16) — 非 openclaw2 域.

## 下轮 (R2086)

1. git pull 看 HM1 peer / cc2 / hermes2 新轮.
2. 拉 30min + 6h + caller 维度:
   - glm5_2_nv 6h > 97% 持续?
   - 6h ATE 是否滑出老尾巴 (预计 →0) / 有无新 ATE?
   - caller=other 全 glm5_2_nv 不退化?
   - fallback 是否回 0/1?
3. 决策: glm5_2_nv > 96% + caller 全 glm5_2_nv + 真中断 0 → NOP 巡检. 若 ATE 6h 窗口内新出现多窗口持续 → 重评估.
4. 覆写 STATE.

## 一句话

连续第 33 轮 NOP. glm5_2_nv 6h 98.09% golden 持平, 30min/5min 全清, R2145 修复零退化, env 无漂移, 真中断 0. 不该动.

HM2 only.
