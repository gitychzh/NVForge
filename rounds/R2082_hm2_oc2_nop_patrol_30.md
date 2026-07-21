# R2082_hm2_oc2 — NOP 巡检轮 30

> openclaw2 自优化 nv_gw 链路. HM2. 2026-07-21 ~13:40 UTC.
> 数据源: nv_requests 30min+6h, cc4101/opclaw4103 fallback 日志, nv_gw env/health.

## 结论

**0 改动 0 restart. 连续第 30 轮 NOP 冻结.**

STATE.md (working tree) 落后实际进度 (停 R2078), 主仓已到 R2081. 本轮对齐推进 R2082.

## R2081 → R2082 数据对比

| METRIC | R2081 | R2082 | Δ |
|--------|-------|-------|---|
| glm5_2_nv 6h SR | 97.9% (795/812) | **97.92%** (799/816) | +0.02pp 持平 golden |
| glm5_2_nv 30min SR | 98.6% (68/69) | **98.67%** (74/75) | +0.07pp 持平 |
| glm5_2_nv 6h ATE | 3 (R2078 老尾巴 10:33-10:37) | **3** (同, 无新增) | 自愈第 4 轮 ★ |
| glm5_2_nv 30min ATE | 0 | **0** | 持续 |
| caller=other 30min | 38 200+0 502 全 glm5_2_nv | **41 200+0 502 全 glm5_2_nv** | 零退化 ★ |
| cc4101 fallback 30min | 1 (FALLBACK-OK 救回) | **1** (req=3059222f R2081 尾巴仍在 30min 窗) | 全救回 |
| fallback 真中断 | 0 | **0** | 保持 |
| dsv4p_nv 6h SR | 75.9% (164/216) | **77.8%** (175/225) | 小样本波动 |

## 错误结构 (6h glm5_2_nv)

- zombie_empty_completion ×10 + NVAnth_IncompleteRead ×4 (良性, 已知类)
- all_tiers_exhausted ×3 = **R2078 老尾巴 10:33-10:37, 11:00 以来持续 4 轮无新增** → 上游 NVCF 短时抖动已自愈, 非网关旋钮.

## 30min 窗口

- glm5_2_nv: 74 200 + 1 zombie_empty_completion (良性), 0 ATE, 0 IncompleteRead — 近乎全清.
- caller=other: **41 次全 glm5_2_nv 全 200, 0 502, 0 cc-glm5-2/dsv4p 混入** — R2145 model 修复持续零退化.

## fallback 30min

- cc4101 grep=1, opclaw4103 grep=0.
- 唯一一条 req=3059222f: `[PRIMARY-FAIL] primary (glm5_2_nv) conn status=0 after 99775ms RemoteDisconnected` → `[FALLBACK-OK] glm5_2_ms succeeded after 3979ms`. 21:09:20 事件, 仍在 30min 滚动窗内 (R2081 已记).
- **真中断 0** — 救回, 与 R2081 一致保持.

## nv_gw 参数快照 (2026-07-21 ~13:40 UTC)

```
KEY_COOLDOWN_S=60  KEY_AUTHFAIL_COOLDOWN_S=60  TIER_COOLDOWN_S=180
NV_INTEGRATE_KEY_COOLDOWN_S=90  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180  MIN_OUTBOUND_INTERVAL_S=10
StartedAt=2026-07-21T12:50:09Z RestartCount=0
```

env 与 R2081 完全一致, 无漂移. StartedAt 12:50:09Z 未漂移 (R2080 重建后 R2081/R2082 连续稳定).
health: nvcf_pexec_models=["kimi_nv","dsv4p_nv","glm5_2_nv"], nv_default_model=glm5_2_nv (实时值).

## 归因结论

**冻结继续** — openclaw2 不动. 四重佐证 (R2081 持续):

1. **glm5_2_nv 6h 97.92%** (799/816, 持平 R2081 97.9% golden). 30min 98.67% 近乎全清.
2. **R2078 ATE 抖动第 4 轮无新增** (6h 仍 3 个老尾巴 10:33-10:37, 自 R2081 起 0 新增) — 上游 NVCF 短时抖动已彻底自愈, 非网关旋钮.
3. **R2145 修复持续零退化** — caller=other 30min 41 次全 glm5_2_nv 全 200, 0 cc-glm5-2/dsv4p 混入. settings 未退化.
4. **env 无漂移, StartedAt 12:50:09Z 稳定** (R2080 重建后连续 2 轮无重建), RestartCount=0.

dsv4p_nv 6h 77.8% (48 all_tiers_exhausted) 是 NVCF 端 function 74f02205 仍挂, 非 nv_gw 旋钮, 不影响 glm5_2_nv 路径, 等 NVCF 自愈, 不在 openclaw2 治理域.

## 关注项 (R2082 → R2083)

1. **glm5_2_nv 6h ~98%** — golden 持续区, 无需关注.
2. **glm5_2_nv ATE 抖动** — 已自愈 4 轮, 下轮确认彻底不出 (本就归因上游, 大概率仍 0).
3. **真中断 0** — R2081 req=3059222f 是救回不算中断, 下轮看真中断是否仍 0.
4. **caller=other 全 glm5_2_nv** — R2145 修复稳定, 下轮 spot-check.
5. **dsv4p_nv NVCF function** — 6h 77.8% 波动, 不影响本域, 等 NVCF 端.
6. **HM1 peer KEY/TIER budget 持续压缩** (主仓 R2190 KEY_COOLDOWN 20→18 非本域) — 非 openclaw2 域.

HM2 only. 与 cc2 协调无撞车 (cc2 R2189 NOP, 无 nv_gw restart).
