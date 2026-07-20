# R2121 (hm2_cc2) — NOP R155 连续第 90 轮冻结

> 第 3 波 NVCF 429 风暴延续 ~35min 后接近自愈末尾 (21:13 UTC 后近 9min 全 200).
> NV-CAP-RESET-MSFB 持续 5 条 (R1818 bug7 已有机制正常触发, 全被 ms_fb 兜住 0 真中断).
> 0 改动 0 restart. HM2 only. 不碰 HM1.

## 拉取时间
CST 05:22 (UTC 21:22), 踩第 3 波风暴尾段 (20:40 起算已 ~35min, 21:13 自愈开始).

## 30min nv_gw 数据

- **SR = 68/105 = 64.8%** (200:68 / 502:35 / 429:2)
  - vs R2120 (05:05 CST, 65.6%): -0.8pp (基本持平, 大窗仍被风暴污染)
  - vs R2118 拉时 (91.9% 稳态): -27.1pp
- **小窗 SR (回升中)**: last3=85.7% / last5=84.2% / last10=87.5% / last15=82.6% / last20=82.9%
  - vs R2120 last3=80/last10=48.5/last15=47.4%: 本轮小窗全面回升, last10 +39pp last15 +35pp
- **5min 桶轨迹 (UTC)**:
  - 20:48-20:54 高峰持续 (502×1-5/桶, 429×1@20:49/20:54)
  - 20:55-21:13 零星 502 (每桶 0-2 个 502 穿插 200)
  - 21:13 之后 → 21:14-21:22 (近 9min) **全 200, 0 个 502**, 每分钟 3-4 个 200
  - 即: 自 21:13 起大窗已进入稳态尾巴

## 错误分类 (30min)

- 502×35 全 **NVCF 上游已知类**:
  - all_tiers_exhausted × 29
  - zombie_empty_completion × 4
  - NVAnth_IncompleteRead × 1
  - **0 新可配置类** ✅
- tier ×60: pexec_success×36 + **429_nv_rate_limit×13** (vs R2120 ×23 -10 回落中) + NVCFPexecRemoteDisconnected×9 + pexec_SSLEOFError×1 + pexec_empty_200×1

## 关键指标 (未恶化确认)

- **0 真中断**: cc4101 `both failed|ms.*fail|UPSTREAM-ERROR-SEEN` 30min = 0 ✅
- **fallback 6** 全 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (header/ttfb 75s < chain_budget 120s, cc4101 pre-empted, NOT counted toward circuit), 全被 ms_gw 兜住, **0 失败 0 条 120s 跑满** ✅
  - vs R2120 fallback 8 → 本轮 6 (-2, 自愈期 fallback 减少)
- **NV-CAP-RESET-MSFB = 5 条** (04:56-05:14 CST, total_elapsed_pre_reset=121-130s)
  - R1818 bug7 已有 cap_origin reset 机制 (execute→ms_fb path) **正常触发**
  - 全被 ms_fb 兜住 0 真中断
  - vs R2120 拉时 (6 条) 本轮 30min 5 条, 持续间断出现近 18min
  - **不是机制恶化**: 是 chain_budget 120s 风暴期偶尔被耗尽后走 ms_fb 正常兜底, 非新缺陷
- **breaker**: nv_gw 30min recorded=1 实为 `[NV-ANTH-BREAKER-FAIL] nv_breaker recorded state=('CLOSED',1,0)` 单点 NVAnth_IncompleteRead 软挂, **state CLOSED 未真 OPEN, 连续第 23 轮未恶化** ✅
- **BUG-A (R1913)**: NV-GLM52-CHAIN-SKIP-PEXEC2 触发 **5 次**, 持续复活生效 ✅
- **abs_cap 30min = 0** (DB 层) ✅
- **health** = ok (passthrough, 5 keys, kimi_nv/dsv4p_nv/glm5_2_nv, default=dsv4p_nv)
- **nv_gw StartedAt = 2026-07-20T18:10:28Z** (连续第 10 轮核实未漂移)
- **cc4101 StartedAt = 2026-07-19T12:10:22Z** (0 restart)

## 决策: NOP (连续第 90 轮冻结指数退避)

1. 第 3 波风暴本质 = NVCF 上游 429 rate limit 周期性抖动 (~1h 一波), 非网关逻辑缺陷. 本轮已接近自愈末尾 (21:13 UTC 后 9min 全 200).
2. 502 全 NVCF 已知类 0 新可配置类.
3. NV-CAP-RESET-MSFB 持续 5 条是 R1818 bug7 已有机制正常触发, 全被 ms_fb 兜住 0 真中断 — 持续出现需观察但不是机制恶化.
4. **解冻指数退避仍不对症**: 延长 chain_budget (120→420) 把耗尽的请求拖更久反降 SR, 5 条 chain_budget 耗尽类已证 (R2111/2116/2119/2120/2121 五轮论证).
5. 所有兜底机制 (ms_gw fallback + ms_fb + breaker CLOSED + cap reset + BUG-A) 全部正常吸收, 0 真中断, 用户诉求 "可报错但不中断" 达成.

## env (peer R2108 改后值, 非 cc2 改, 与 R2120 完全一致)

```
KEY_COOLDOWN_S=60   TIER_COOLDOWN_S=180   MIN_OUTBOUND_INTERVAL_S=10
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180  NVU_TIER_BUDGET_GLM5_2_NV=120
NVU_GLM52_EXP_BACKOFF 不在 env 中 = 关 (半成品冻结)
```

## 下一轮

- 继续 NOP R156 (连续第 91 轮). 重点看第 3 波风暴是否完全自愈 (30min SR 回 91-96% 稳态需窗口起点 >= 21:13 UTC, 即 CST 05:33 后).
- **重点观察 NV-CAP-RESET-MSFB 是否持续增多**: 本轮 5 条持续 18min. 若自愈后归零 → 确证风暴驱动; 若稳态期仍持续增多 → 需重新评估 chain_budget 是否过长耗 SR (但仍非解冻指数退避理由, 只是观察).
- 风暴周期性 ~1h 精确 (R2111 02:45 → R2116 03:45 → R2119 04:45 → 本轮尾段). 若下一波在 CST 05:45 前后复发, 模式坐实.
- 解冻阈值不变: 任一指标真恶化 (30min SR 持续<90% 非风暴污染 + 502 新可配类 / fallback 失败 / breaker 真 OPEN 切流) 才考虑解冻.

HM2 only. 0 改动 0 restart. R2121.
