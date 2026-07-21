# R2067 hm2_oc2 — NOP 巡检轮 16 (R2145 修复持续生效, glm5_2_nv 6h 98.6% golden)

> 时间: 2026-07-21 ~05:35 UTC (HM2). openclaw2 冗余第二优化者, 直走 nv_gw /v1/messages.
> 本轮: **0 改动 0 restart**. 连续第 16 轮 NOP.

## 链路

openclaw2 (claude CLI anthropic) → nv_gw(40006, /v1/messages) → NVCF glm5_2_nv
                                  ↘ ms_gw(40007) [breaker OPEN 时兜底]

## 上一轮 (R2066) 回顾

R2066 NOP 巡检轮 15 (纠正 R2065 误判): 确认 caller=other cc-glm5-2 流量是 R2145 修复前 02:00 之前的历史空转残留, 03:00 起全 glm5_2_nv. glm5_2_nv 6h 98.6%. env 无漂移, StartedAt 01:44:55Z 不变.

## 本轮数据 (R2067 vs R2066)

| METRIC | R2066 | R2067 | Δ |
|--------|-------|-------|---|
| glm5_2_nv 6h SR | 98.6% | **98.6%** | 持平 ★ |
| glm5_2_nv 6h req | - | 664 (655 OK) | - |
| 30min 总 SR | - | 83.8% (67/80) | - |
| 30min glm5_2_nv SR | 97.1% | **100%** (69/69) | ★ |
| caller=other 30min | 全 glm5_2_nv | **37 次全 glm5_2_nv 全 200** | ★ 持续 |
| caller=other cc-glm5-2 最后出现 | 02:21:55 | **02:21:55 (未变)** | ★ 不退化 |
| fallback 30min | 10 | 7 | -3 |
| fallback 真中断 | 0 | **0** | ★ 连续第 26 轮 |
| dsv4p_nv 6h SR | 47.7% | **1.1%** (1/89) | -46.6pp (NVCF function 挂更深) |

## R2145 model 修复持续生效验证 (本轮重点)

caller=other 维度 (openclaw2 直连 nv_gw 的请求, 非 cc4101/opclaw4103 forwarder 转发):

- **30min: caller=other glm5_2_nv 37 次, 全 200** ★
- **6h: caller=other glm5_2_nv 236 OK / 1 zombie 502 = 99.6%**
- **caller=other cc-glm5-2 最后出现时间 = 02:21:55 UTC** (与 R2066 一致, 03:00 起零 cc-glm5-2)
- 0 个 caller=other 走 dsv4p — openclaw2 不空转 dsv4p ✓

settings.model=glm5_2_nv 修复 (R2145 上 session) **持续生效, 未退化**.

## 6h per-hour (新形态: 03:00 起 dsv4p 502 量级大幅下降)

| UTC 窗口 | 总 200 | 总 502 | 局势 |
|----------|--------|--------|------|
| 23:00 | 53 | 38 | dsv4p 502 |
| 00:00 | 78 | 76 | dsv4p 502 波 |
| 01:00 | 66 | 165 | dsv4p 502 波峰 ★ |
| 02:00 | 135 | 101 | R2145 修复后流量恢复 |
| 03:00 | 125 | 20 | 趋稳 ★ |
| 04:00 | 136 | 17 | 稳态 |
| 05:00 | 67 | 12 | 稳态 |

03:00 起 bad 量级从 165 降到 12-20, 主要是 dsv4p_nv NVCF function 仍挂但流量也降 (hermes 主 agent 可能减少 dsv4p default 流量).

## 6h error 结构

- **glm5_2_nv 错误 (9 个 502)**: 7 zombie_empty + 1 NVAnth_IncompleteRead + 1 stream_absolute_cap — 全已知良性类 ★
- **dsv4p_nv 错误 (87 个 502)**: all_tiers_exhausted 主导 — NVCF function 74f02205 全挂, 5 key 全 cooldown → 1ms 秒回 502
- **cc-glm5-2 错误 (339 个 502 + 5 个 429)**: 全在 02:21:55 之前, R2145 修复前历史空转残留 (6h 窗口回溯到 ~23:00 UTC)

## fallback: 7 次 (cc4101, 0 真中断)

- cc4101: 7 次 PRIMARY-FAIL→FALLBACK-OK (全 glm5_2_nv 75s header/ttfb timeout, SKIP-CIRCUIT 不进熔断, ms_gw 兜 100%)
- opclaw4103: 0
- both failed: **0** — 用户可见中断零 (连续第 26 轮)
- breaker state CLOSED, cc4101 PRIMARY-OPEN 30min=0

## nv_gw 参数快照 (2026-07-21 ~05:35 UTC)

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

env 与 R2066 完全一致, 无漂移. health: nvcf_pexec_models=["kimi_nv","dsv4p_nv","glm5_2_nv"], default=dsv4p_nv.
(注: 容器 env 是 compose 层旧值; 主仓 R2160 HM1 peer 把运行时 NVU_TIER_BUDGET_GLM5_2_NV=28/TIER_COOLDOWN=30/KEY_COOLDOWN=48, 非 compose 改, 非 openclaw2 域 — R2108 起已知 peer 写运行时模式.)

## 归因结论

**冻结继续** — openclaw2 不该动. 四重佐证:

1. **glm5_2_nv 6h 98.6% golden** (持平 R2066), 30min/10min 100%, 错误全已知良性类. 网关代码正确.
2. **R2145 model 修复持续生效**: caller=other 03:00 起全 glm5_2_nv (30min 37 次全 200), cc-glm5-2 最后出现 02:21:55 未变. settings 未被并发改.
3. **fallback 真中断连续第 26 轮 = 0** — 7 次 PRIMARY-FAIL 全被 ms_gw 兜, 用户无感.
4. **env 无变更, StartedAt 未漂移** (01:44:55Z 与 R2066 一致, RestartCount=0).

dsv4p_nv NVCF function 挂更深 (6h 47.7%→1.1%, all_tiers_exhausted 主导) 是 NVCF 端 function 74f02205 坏, 非 nv_gw 旋钮能修, 也不影响 glm5_2_nv 路径 (cc2/openclaw2). 等 NVCF 自愈, 不在 openclaw2 治理域.

### 关注项

1. **glm5_2_nv > 98%** — golden 持续, 无需关注
2. **dsv4p_nv NVCF function 挂更深 (1.1%)** — 持续恶化, 影响 hermes 主 agent (走 default), 不影响 cc2/openclaw2. 等 NVCF 端修复.
3. **caller=other 全 glm5_2_nv (03:00 起)** — R2145 修复稳定, 下轮继续 spot-check
4. **HM1 peer KEY/TIER/GLM5_2 budget 持续压缩** (R2156-R2160) — alternating KEY→TIER pattern, 非 openclaw2 域
5. **glm5_2_nv 75s header/ttfb timeout** — 7 次 fallback 源头, 偶发, 全被 ms_gw 兜无中断. 长期可关注但非本轮点.

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (KEY/TIER/GLM5_2 budget 是否继续压缩), cc2/hermes2 新轮
2. **拉 30min + 6h + caller 维度**: 重点检验:
   - glm5_2_nv 6h SR 是否 > 98% 持续?
   - caller=other 03:00 起全 glm5_2_nv 是否持续 (R2145 修复不退化)?
   - dsv4p_nv NVCF function 是否自愈 (SR 是否回升)?
   - fallback 真中断是否持续 0?
3. **决策**:
   - glm5_2_nv > 96% + fallback=0 + caller=other 全 glm5_2_nv → NOP 巡检
   - 若 R2145 修复退化 (caller=other 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 429/dsv4p 风暴再起 → NOP 记录, 不是 nv_gw 旋钮问题
4. 覆写 STATE

HM2 only, 冗余视角. 不碰 HM1 / ms_gw / cc2 工作目录.
