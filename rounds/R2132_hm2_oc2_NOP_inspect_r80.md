# R2132_hm2_oc2 — NOP 巡检轮 80 (连续第 76 轮冻结)

> openclaw2 冗余第二优化者. 0 改动 0 restart. STATE 已对齐 (上轮 R2131 修正到位, 本轮
> 直接 R2131→R2132 覆写, 无滞后). 主仓 HM1 peer 新出 R2275 (FALLBACK_HEALTH_THRESHOLD
> 0.05→0.20, HM1 域非 openclaw2 域, 铁律不碰 HM1).

## 时间

2026-07-23 (HM2, UTC 22:00 实测窗口)

## 链路

openclaw2 (claude CLI, anthropic) 直走 nv_gw /v1/messages (40006) → NVCF glm5_2_nv.
不走 opclaw4103 (openai-only). 优化对象 = nv_gw(40006). openclaw2 = 冗余第二优化者
(cc2 第一, hermes2 第三).

## 数据 (本轮实测 vs R2131 round)

| METRIC | R2131 (round) | R2132 (实测本轮) | Δ |
|--------|---------------|------------------|---|
| glm5_2_nv 6h SR | 96.08% (637/664) | **96.14%** (648/674) | +0.06pp 逐点持平 golden 上沿 |
| glm5_2_nv 30min | 57/59 全 200 2错 0 ATE | **66/68** 全 200 2错 0 ATE | 样本增 0 ATE 保持 |
| 30min ATE (glm5_2_nv) | 0 | **0** | 自愈保持 |
| 6h glm5_2_nv ATE | 0 | **0** | 改善保持 (连续 0) |
| 6h 499 (openclaw2 域) | 0 | **0** | 持续健康 |
| fallback 30min | 0 (双 0) | **0** (cc4101+opclaw4103 双 0) | 持平 0 真中断 |
| dsv4p_nv 6h SR | 39.37% (50/127) | **39.06%** (50/128) | -0.31pp 续跌非本域 |

## 数据明细 (实测当前窗口, UTC 22:00)

- glm5_2_nv 6h (648/674, 96.14%): 错 26 = 17zombie + 6stream_absolute_cap + 2stream_no_content_gap + 1NVAnth_IncompleteRead
- glm5_2_nv 6h ATE=0: all_tiers_exhausted count=0 (连续保持, vs R2131 的 0 ATE 持平改善态)
- glm5_2_nv 30min (66/68 全 200, 2错 0 ATE): caller cc4101-primary 30×200+2×502 + other 33×200 + unknown 1×200 全 glm5_2_nv
- 30min 2 错明细 (全 cc4101-primary): 1 stream_absolute_cap + 1 stream_no_content_gap (均 mid-stream 上游瞬时, 首字节已收未触发 fallback, 背景波量级, 与 R2131 同型)
- 30min 全错 = glm5_2_nv 2 (cap+no_content_gap 全背景波); openclaw2 自身 30min 全 200
- 6h 499=0 (openclaw2 域 caller=other/cc4101-primary/unknown 无 499): cc2 R2199 全局 settings env 改后持续健康 (R2149 锁定 model=glm5_2_nv 后零退化)
- fallback 30min 0 次: cc4101+opclaw4103 双 0, **0 真中断** (持平 R2131 的 0)
- 6h 真中断: stream_absolute_cap 6 + zombie 17 + IR 1 全上游非旋钮 (30min 0 真中断, 2 错全背景波)

## nv_gw 参数快照 (2026-07-23 本轮, 与 R2131 STATE 逐行一致无漂移)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
NVU_EMPTY_200_FASTBREAK=3
StartedAt=2026-07-22T15:10:34Z  RestartCount=0  (连续第 42 轮 RC=0)
```

注: 容器 env 是 compose 层 HM2 域旧值. HM1 peer R2271-R2275 全 HM1 域 (TIER_TIMEOUT_BUDGET
192→222→234, dsv4p TIER_BUDGET 150→160, glm5_2_nv TIER_BUDGET 110→160, EMPTY_200_FASTBREAK
1→2→3 多轮连调, R2275 FALLBACK_HEALTH_THRESHOLD 0.05→0.20; 均运行时改非 compose), 非 openclaw2
域 (铁律只改 HM2 nv_gw, 不碰 HM1). health: nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv],
nv_default_model=glm5_2_nv, port=40006.

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **glm5_2_nv 6h 96.14%** (648/674) 逐点持平 R2131 96.08% golden 上沿区 (R2126-R2132
   94.39→95.07→95.46→95.69→95.71→96.08→96.14 区间企稳上沿).
2. **glm5_2_nv 30min 66/68 全 200 0 ATE** — 2 错全背景波 (1 cap + 1 no_content_gap 上游瞬时),
   0 all_tiers_exhausted, 与 R2131 同型.
3. **6h ATE=0** 连续保持 (vs R2131 0 ATE 持平改善态, 连续 0).
4. **R2145/R2149 修复零退化**: caller cc4101-primary 30 + other 33 + unknown 1 30min 全
   glm5_2_nv 全 200, 无 cc-glm5-2/dsv4p 串入.
5. **fallback 30min 0 救回 0 真中断** (cc4101+opclaw4103 双 0); env 无漂移 StartedAt 15:10:34Z
   连续第 42 轮 RC=0.

真中断全上游 zombie/cap/IR/stream_no_content_gap 瞬时非旋钮能修 (stream_absolute_cap
nv+ms 都挂 → 上游 NVCF 瞬时). fallback 30min 0. 6h 499=0: cc2 R2199 全局 settings env 改后
openclaw2 域健康持续 (R2149 锁定 model=glm5_2_nv 后零退化). dsv4p_nv 6h 39.06% 续跌 是 NVCF 端
function 74f02205 恶化延续, 非 nv_gw 旋钮能修, 不影响 glm5_2_nv 路径. 等 NVCF 自愈.

## 关注项

1. **glm5_2_nv 6h ~96.14%** — golden 上沿持续区, 无需关注
2. **glm5_2_nv 30min 66/68 0 ATE** — 自愈保持, 稳定
3. **6h ATE=0** — 连续保持改善态, 30min 0 ATE
4. **6h 499=0** — cc2 R2199 全局 settings 改后 openclaw2 域健康持续, 持续观察
5. **dsv4p_nv NVCF function 恶化延续 (39.06% 续跌)** — 影响 hermes 主 agent, 不影响 cc2/openclaw2.
   等 NVCF 端修复.
6. **caller cc4101-primary+other+unknown 全 glm5_2_nv** — R2145/R2149 修复稳定零退化
7. **HM1 peer R2271-R2275 多轮连调** (TIER_TIMEOUT_BUDGET 192→234 + dsv4p TIER_BUDGET 150→160 +
   glm5_2_nv TIER_BUDGET 110→160 + EMPTY_200_FASTBREAK 1→2→3 + R2275 FALLBACK_HEALTH_THRESHOLD
   0.05→0.20) — 非 openclaw2 域 (铁律只改 HM2)
8. **STATE 对齐本轮 (无滞后)** — 上轮 R2131 第 35 次修正生效, STATE 头部 = R2131 = 主仓 openclaw2
   最新, 本轮 R2132 直接覆写无滞后修正.

## 结论

连续第 76 轮 NOP 冻结. openclaw2 = 冗余第二优化者, nv_gw 框架层已稳 (glm5_2_nv 6h 96.14%
golden 上沿 + 30min 0 ATE + 6h 0 499 + fallback 0), 无 cc2 未覆盖的可改点. 真中断全上游瞬时
非旋钮. dsv4p_nv 续跌非本域. HM2 only.
