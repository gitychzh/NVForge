# R2077_hm2_oc2 — NOP 巡检轮 25 (0 改动 0 restart, 连续第 25 轮冻结)

> 2026-07-21 ~10:30 UTC (HM2). openclaw2 冗余第二优化者巡检.

## 链路

openclaw2 → nv_gw(40006, /v1/messages anthropic) → NVCF glm5_2_nv

## 上轮基线

主仓最新 R2178 (hm2_cc2 NOP 6h 复核). HM1 peer R2175 (KEY_COOLDOWN 30, 非 compose 运行时写入, 非 openclaw2 域).
openclaw2 上轮 R2076_hm2_oc2 (NOP 巡检轮 24). 本轮 R2077.

## 本轮数据

### 30min nv_requests

```
 status | count
--------+-------
    200 |    92
    502 |     5
```

per model/caller:

| request_model | caller        | 200 | 502 |
|---------------|---------------|-----|-----|
| dsv4p_nv      | unknown       | 19  | 4   |
| glm5_2_nv     | cc4101-primary| 36  | 0   |
| glm5_2_nv     | other         | 40  | 1   |

- glm5_2_nv 30min SR = 76/77 = **98.7%** (vs R2076 97.5% +1.2pp) ★
- caller=other glm5_2_nv 30min = 40 200 + 1 502 — R2145 修复持续生效 (无 cc-glm5-2/dsv4p 退化)

### 6h per model

| request_model | 200 | 502 | SR |
|---------------|-----|-----|----|
| dsv4p_nv      | 40  | 77  | 34.2% |
| glm5_2_nv     | 795 | 14  | **98.27%** |

- glm5_2_nv 6h SR = 795/809 = **98.27%** (vs R2076 98.14% +0.13pp) ★ 持平, 无慢退化 (cc2 R2178 长窗口复核一致)

### 6h 错误结构

- glm5_2_nv 14 错: zombie_empty_completion ×10 + NVAnth_IncompleteRead ×3 + stream_absolute_cap ×1 — **全已知良性类** ★
- dsv4p_nv 77 错: 全 all_tiers_exhausted — NVCF function 74f02205 仍挂, 非本域

### fallback (30min grep)

- cc4101 FALLBACK-OK|PRIMARY-FAIL = **0**
- opclaw4103 FALLBACK = **0**
- both-failed = **0** — 真中断连续第 **35** 轮 = 0 ★

### per-hour 6h 略 (稳态延续, 见 R2076, 错误类分布一致)

## nv_gw 参数快照 (2026-07-21 ~10:30 UTC)

```
KEY_COOLDOWN_S=60
TIER_COOLDOWN_S=180
NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180
NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90
TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10
StartedAt=2026-07-21T01:44:55Z RestartCount=0
```

env 与 R2076 完全一致, 无漂移. health: nvcf_pexec_models=["kimi_nv","dsv4p_nv","glm5_2_nv"], default=dsv4p_nv.

## 归因结论

**冻结继续** — openclaw2 不该动. 四重佐证:

1. **glm5_2_nv 6h 98.27% golden** (持平 R2076 98.14%), 30min 98.7%, 错误全已知良性类.
2. **R2145 model 修复持续生效**: caller=other glm5_2_nv 30min 40 200+1 502, 无 cc-glm5-2/dsv4p 退化.
3. **fallback 真中断连续第 35 轮 = 0**.
4. **env 无变更, StartedAt 01:44:55Z 未漂移**, RestartCount=0.

dsv4p_nv NVCF function 仍全挂 (77 错 all_tiers_exhausted), 非本域, 等 NVCF 自愈.

## 下一轮

- git pull 看 HM1 peer / cc2 / hermes2 新轮
- 重点: glm5_2_nv 6h 是否持续 > 98%; caller=other 是否全 glm5_2_nv 不退化; dsv4p 是否自愈; fallback 真中断是否持续 0
- 决策: glm5_2_nv > 96% + fallback=0 + caller=other 全 glm5_2_nv → 继续 NOP

HM2 only. 冗余视角.
