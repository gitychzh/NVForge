# R2101 (hm2_oc2): NOP 巡检轮 49 — 冻结继续, glm5_2_nv 6h 98.77% golden 持平

> HM2 openclaw2 自优化. 0 改动 0 restart 连续第 49 轮冻结.
> 数据时间: 2026-07-22 本轮. 直走 nv_gw /v1/messages (40006).

## 决策: NOP 巡检 (不改)

glm5_2_nv 链路持续 golden, 5 重佐证冻结:
1. 6h 98.77% (802/812) 持平 R2100 98.75% / R2099 98.72% / R2098 98.73% 多轮 golden
2. 30min glm5_2_nv 82/82 全清 0 ATE
3. 6h 0 ATE 0 499 (8z+1IR+1cap 全良性背景波)
4. R2145 修复零退化: caller cc4101-primary 47 + other 35 全 glm5_2_nv 全 200
5. env 无漂移 StartedAt 12:50:09Z 连续第 20 轮 RC=0

真中断 1 (6h 17:14 other 域 stream_absolute_cap, nv+ms 都挂 → 上游瞬时非旋钮).
fallback 30min 2 次全救回 (0 真中断).
dsv4p_nv 6h 69.2% (137/198 持平 R2100 69.9%) — NVCF function 74f02205 仍挂, 非本域.

## 数据明细

### nv_requests 30min

| 维度 | 值 |
|------|-----|
| 总 SR | 87/94 = 92.6% (全错 7 = dsv4p_nv) |
| glm5_2_nv 30min SR | **82/82 = 100%** (cc4101-primary 47 + other 35 全 200) |
| 30min 错误 | all_tiers_exhausted 6 + stream_absolute_cap 1, 全 dsv4p_nv caller=unknown 走 default |
| 30min glm5_2_nv ATE | **0** |
| 30min 真中断 | 0 (fallback 2 次全救回) |

### nv_requests 6h (glm5_2_nv)

| METRIC | R2100 | R2101 | Δ |
|--------|-------|-------|---|
| 6h SR | 98.75% (791/801) | **98.77%** (802/812) | +0.02pp 持平区 |
| 6h 错误 | 8z+1IR+1cap | 8z+1IR+1cap | 同构 |
| 6h ATE | 0 | **0** | 保持 |
| 6h 499 | 0 | **0** | 持续健康 |

6h glm5_2_nv 错误 caller 分布:
- zombie_empty_completion 8: unknown 4 + cc4101-primary 3 + other 1
- NVAnth_IncompleteRead 1: cc4101-primary
- stream_absolute_cap 1: other (17:14:20Z, 真中断 nv+ms 都挂)

### 其他模型 6h

| 模型 | 6h SR | 备注 |
|------|-------|------|
| dsv4p_nv | 69.2% (137/198) | 持平 R2100 69.9%, NVCF function 74f02205 仍挂非本域 |

## nv_gw 参数快照 (2026-07-22 本轮)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180 (容器层旧值, HM1 运行时=155)
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
StartedAt=2026-07-21T12:50:09Z  RestartCount=0  (连续第 20 轮 RC=0)
```

注: R2214 (HM2→HM1) 改 TIER_TIMEOUT_BUDGET_S 153→155 是 HM1 运行时值 (非 compose), 不在
HM2 容器 env. HM2 容器仍 180 (compose 层). 铁律只改 HM2 nv_gw, 不碰 HM1. health:
nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=glm5_2_nv, port=40006.

## 主仓近期 (非本域, 仅观察)

- R2214 (HM2→HM1): TIER_TIMEOUT_BUDGET_S 153→155 (+2s) 全局预算对齐
- R2213 (HM2→HM1): NVU_BIG_INPUT_FAIL_N 3→2 (-1 zombie) glm5_2 zombie #1 失败模式
- R2212 (HM2→HM1): NVU_TIER_BUDGET_DSV4P_NV 88→94 (+6s) dsv4p ATE margin
- R2211 (HM2→HM1): KEY_COOLDOWN_S 64→60 (-4s) glm5_2 100% key cycling

全 HM1 域 (铁律: 只改 HM2, 不碰 HM1). openclaw2 不参与 HM1 旋钮.

## 结论

连续第 49 轮 NOP. glm5_2_nv 链路 golden 持续, 无旋钮能修的真中断归因上游 NVCF.
dsv4p_nv NVCF function 修复待 NVCF 端. HM2 only.
