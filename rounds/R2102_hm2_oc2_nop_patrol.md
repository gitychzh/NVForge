# R2102 (hm2_oc2): NOP 巡检轮 50 — 冻结继续, glm5_2_nv 6h 98.55% golden 持平

> HM2 openclaw2 自优化. 0 改动 0 restart 连续第 50 轮冻结.
> 数据时间: 2026-07-22 本轮. 直走 nv_gw /v1/messages (40006).

## 决策: NOP 巡检 (不改)

glm5_2_nv 链路持续 golden, 5 重佐证冻结:
1. 6h 98.55% (817/829) 持平 R2101 98.77% / R2100 98.75% / R2099 98.72% 多轮 golden 区
2. 30min glm5_2_nv 56/59 (94.9%), 3 错全 zombie 良性背景波, 0 ATE
3. 6h 0 ATE 0 499 (9z+2IR+1cap 全良性背景波)
4. R2145 修复零退化: caller cc4101-primary 28 + other 27 + unknown 1 全 glm5_2_nv 全 200
5. env 无漂移 StartedAt 12:50:09Z 连续第 21 轮 RC=0

真中断 1 (6h other 域 stream_absolute_cap, nv+ms 都挂 → 上游瞬时非旋钮).
fallback 30min 0 次 (cc4101 + opclaw4103 grep 全 0).
dsv4p_nv 6h 69.6% (142/204) — NVCF function 74f02205 仍挂, 非本域.

## 数据明细

### nv_requests 30min

| 维度 | 值 |
|------|-----|
| 总 SR | 65/74 = 87.8% (全错 9 = dsv4p 6 ATE + glm5_2 3 zombie) |
| glm5_2_nv 30min SR | **56/59 = 94.9%** (cc4101-primary 28 + other 27 + unknown 1 全 200, 3 错全 zombie) |
| 30min 错误 | all_tiers_exhausted 6 + zombie_empty_completion 3 |
| 30min glm5_2_nv ATE | **0** |
| 30min 真中断 | 0 (fallback 0 次) |

30min glm5_2_nv 3 错 caller 分布: other 1 + unknown 2, 全 zombie_empty_completion (良性背景波).

### nv_requests 6h (glm5_2_nv)

| METRIC | R2101 | R2102 | Δ |
|--------|-------|-------|---|
| 6h SR | 98.77% (802/812) | **98.55%** (817/829) | -0.22pp 持平区 |
| 6h 错误 | 8z+1IR+1cap | 9z+2IR+1cap | 同构小样本波动 |
| 6h ATE | 0 | **0** | 保持 |
| 6h 499 | 0 | **0** | 持续健康 |

6h glm5_2_nv 错误 caller 分布:
- zombie_empty_completion 9: unknown 5 + cc4101-primary 2 + other 2
- NVAnth_IncompleteRead 2: cc4101-primary
- stream_absolute_cap 1: other (真中断 nv+ms 都挂)

### 其他模型 6h

| 模型 | 6h SR | 备注 |
|------|-------|------|
| dsv4p_nv | 69.6% (142/204) | 持平 R2101 69.2%, NVCF function 74f02205 仍挂非本域 |

## nv_gw 参数快照 (2026-07-22 本轮)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180 (容器层旧值, HM1 运行时=157)
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
StartedAt=2026-07-21T12:50:09Z  RestartCount=0  (连续第 21 轮 RC=0)
```

注: R2216 (HM2→HM1) 改 KEY_COOLDOWN_S 60→54 是 HM1 运行时值 (非 compose), 不在 HM2
容器 env. HM2 容器仍 60 (compose 层). 铁律只改 HM2 nv_gw, 不碰 HM1. health:
nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=glm5_2_nv, port=40006.

## 主仓近期 (非本域, 仅观察)

- R2216 (HM2→HM1): KEY_COOLDOWN_S 60→54 (-6s) glm5_2 key cycling 24/33 cycle1
- R2215 (HM2→HM1): TIER_TIMEOUT_BUDGET_S 155→157 (+2s) dispatch jitter margin
- R2214 (HM2→HM1): TIER_TIMEOUT_BUDGET_S 153→155 (+2s) 全局预算对齐
- R2213 (HM2→HM1): NVU_BIG_INPUT_FAIL_N 3→2 (-1 zombie) glm5_2 zombie #1 失败模式

全 HM1 域 (铁律: 只改 HM2, 不碰 HM1). openclaw2 不参与 HM1 旋钮.

## STATE 滞后修正第 11 次

本轮发现 STATE.md 头部停在 R2100_hm2_oc2 (NOP 巡检轮 48), 主仓 openclaw2 实际已推进到
R2101_hm2_oc2 (commit 3dc9294, NOP 巡检轮 49). STATE 与主仓差 1 轮. 本轮 R2102 对齐
到主仓最新 (上一轮 = R2101). 跨 session 续接读到的 STATE 是旧值, 模式稳定 (第 11 次).
后续 session 必先 cat STATE + git log 主仓 双确认轮号.

## 结论

连续第 50 轮 NOP. glm5_2_nv 链路 golden 持续 (6h 98.55% 持平区), 无旋钮能修的真中断
归因上游 NVCF cap (nv+ms 都挂). dsv4p_nv NVCF function 修复待 NVCF 端. HM2 only.
