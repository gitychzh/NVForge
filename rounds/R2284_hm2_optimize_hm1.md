# R2284: HM2优化HM1 — PEXEC_TIMEOUT_FASTBREAK 1→2 消除单次超时触发全tier失败

## 数据采集 (6h窗口: ~2026-07-23 06:35-12:35 UTC)

| 指标 | 数值 |
|---|---|
| 总请求 | 43 |
| 成功 | 14 |
| 失败 | 29 |
| 成功率 | 32.6% |

### 错误分布

| 错误类型 | dsv4p_nv | glm5_2_nv |
|---|---|---|
| ATE (all_tiers_exhausted) | 21 | 8 |

### 每模型SR

| 模型 | 总请求 | 成功 | 成功率 | 平均延迟(ms) |
|---|---|---|---|---|
| dsv4p_nv | 23 | 2 | 8.7% | 20518 |
| glm5_2_nv | 20 | 12 | 60.0% | 34665 |

### 429 Key Cycling
- glm5_2_nv: 1次 (极低)

## 根因分析

**日志证据 (12:33-12:35 UTC):**
```
[NV-TIMEOUT] tier=glm5_2_nv k5 NVCF pexec timeout: attempt=24810ms total=24823ms
[NV-PEXEC-FASTBREAK] tier=glm5_2_nv 1 consecutive NVCFPexecTimeout -> fast-break (saved remaining keys)
[NV-TIER-FAIL] tier=glm5_2_nv all 5 keys failed: 429=0, empty200=0, timeout=1, other=0
[NV-ALL-TIERS-FAIL] All 1 tiers failed, ABORT-NO-FALLBACK
```

**`NVU_PEXEC_TIMEOUT_FASTBREAK=1`** → 单个上游 NVCFPexecTimeout 立即终止整个tier，浪费其余4个未尝试的key。与R2270的EMPTY_200_FASTBREAK问题同根同源：上游偶发超时是正常现象，不应导致整个tier废弃。

**实际影响**：glm5_2_nv的8个ATE中，每个都只尝试了1个key就被fast-break，剩余4个key从未被使用。

## 参数变更

| 参数 | 旧值 | 新值 | 变更 |
|---|---|---|---|
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 2 | +1 |

**Single param**: 只有 `NVU_PEXEC_TIMEOUT_FASTBREAK` 一个参数变更。

**逻辑**: 需要2次连续NVCFPexecTimeout才fast-break，第一次超时后切换key继续尝试。给第二个key一次机会。

## 验证

```
$ docker exec nv_gw env | grep NVU_PEXEC_TIMEOUT_FASTBREAK
NVU_PEXEC_TIMEOUT_FASTBREAK=2
$ curl -s -o /dev/null -w "%{http_code}" http://localhost:40006/health
200
```

## 约束检查

- [x] Single param: 只改 NVU_PEXEC_TIMEOUT_FASTBREAK
- [x] 与R2270 (EMPTY_200_FASTBREAK 1→2) 对称 — 两者都是"单次失败不应终止整个tier"
- [x] TIER_COOLDOWN_S=0 保持 (R2283)
- [x] KEY_COOLDOWN_S=66 保持 (≥60, 不在1-59 anti-pattern)
- [x] Iron law: 只改HM1参数

## ⏳ 轮到HM1优化HM2