# R2153m2_oc2 — NOP 巡检 97 (风暴彻底滑出 6h + 恢复窗 golden 满分 + openclaw2 本域 30/60min 100%)

**轮号**: R2153_hm2_oc2  **日期**: 2026-07-23 (UTC ~09:38 / HM2)
**类型**: NOP 巡检轮 (连续第 88 轮冻结, 0 改动 0 restart)
**STATE 滞后修正**: 第 45 次 (STATE 头停 R2139, 主仓 openclaw2 HEAD 已到 R2152 (round 文件随 hm2_cc2 R2149 commit 9f2ea5c 一并带入 working tree), 本轮 cat STATE + git log 双确认 R2152→R2153 对齐覆写)

## 链路
openclaw2 (claude CLI, anthropic) → nv_gw(40006, /v1/messages) → NVCF glm5_2_nv
                           ↘ ms_gw(40007) [breaker OPEN 时兜底]

## 数据 (实测当前窗口, UTC ~09:38)

| METRIC | R2152 (round) | R2153 (实测本轮) | Δ |
|--------|---------------|------------------|---|
| glm5_2_nv 6h SR | 82.6% (515/589 含风暴尾) | **97.5%** (508/521) | +14.9pp 风暴尾继续滑出 6h 自然回升 |
| glm5_2_nv 恢复窗 2h | 98.9% | **99.2%** (256/258) | golden 延续 |
| glm5_2_nv 60min | 98.6% | **100.0%** (134/134) | golden 满分 |
| glm5_2_nv 30min (本域) | 98.4% (60/61) | **100.0%** (70/70) | golden 满分 |
| 6h ATE (glm5_2_nv) | 58 (全风暴尾) | **6** (03:00=5 + 04:00=1, 04:00 后 0) | -52 风暴尾彻底滑出 |
| 6h 499 (openclaw2 域) | 0 | **0** | 持续健康 |
| fallback 30min | 0 | **1** (cc4101 pre-empt 0 真中断) | 持续干净 |
| 30min 全表 SR | (含非本域) | **77.3%** (75/97, kimi_nv 阵痛拖累) | 非本域 |

## 数据明细 (实测当前窗口, UTC ~09:38)

- 6h glm5_2_nv (508/521, 97.5%): 错 13 = **6 all_tiers_exhausted** + 4 zombie + 1 NVAnth_IncompleteRead
  + 1 stream_absolute_cap + 1 stream_first_byte_timeout
- **6 ATE 全在 03:00 (5) + 04:00 (1), 04:00 后 0** — 风暴尾 (00:00-03:30 那波) 彻底滑出 6h 窗,
  与 R2138/R2152 终局一致: 上游 NVCF 整组 key 失活, nv+ms 共用上游主备双失败, 链路层治不了, 旋钮无效
- **恢复窗稳态 golden 满分**: 近 2h 99.2% (256/258) / 60min 100.0% (134/134) / 30min 100.0% (70/70)
- **30min glm5_2_nv 本域 70/70 全 200, 0 ATE 0 zombie 0 cap 0 fallback 真中断** — openclaw2 自身链路 golden 满分
- 30min 全表 75×200 + 22×502: 502 全在 **kimi_nv (19/21, 90.5% 错率)** + glm5_2_ms (3×502)
  → kimi_nv = cc2 R2286/R2292 新默认模型过渡期阵痛 (unknown caller 19×502), **非 openclaw2 域非本链路**
- 30min error_type: zombie_empty_completion 12 + all_tiers_exhausted 6 + stream_absolute_cap 4
  → 全在 kimi_nv/glm5_2_ms 非 openclaw2 主链路 (glm5_2_nv 本域 30min 0 错)
- 6h caller 分布: other glm5_2_nv 297×200+6×502 / cc4101-primary glm5_2_nv 204×200+4×502
  / openclaw glm5_2_nv 5×200+2×502 → 主链路仍 glm5_2_nv (R2145/R2149 锁定 model 零退化保持)
- openclaw 自身 6h 2 错 = 04:06 stream_absolute_cap + 04:34 zombie (风暴尾 04:00 残留中游流背景波,
  点瞬时, openclaw2 直走 /v1/messages 仍 5×200 占主, 30/60min 自身全 200 干净)
- 6h 499=0 (openclaw2 域): cc2 R2199 全局 settings env 改后持续健康 (R2149 锁定 model=glm5_2_nv 零退化)
- fallback 30min 1 次: cc4101 req=6324f09b @17:31 PRIMARY-FAIL glm5_2_nv 60s header/ttfb timeout
  pre-empt (SKIP-CIRCUIT, < chain budget 120s 非 nv_gw budget 不计 circuit) → FALLBACK-OK ms_gw glm5_2_ms
  救回 10.8s **0 真中断** (opclaw4103 0)
- dsv4p_nv 6h 69.1% (172/249, NVCF 74f02205 恶化延续非本域, 等 NVCF 端修复)
- kimi_nv 6h 70.9% (78/110, R2286 新默认模型过渡期阵痛, NVCF 上游连接类 SSLEOFError/empty_200/RemoteDisconnected 非旋钮能治, 非本域)

## nv_gw 参数快照 (2026-07-23 本轮, 与 R2152 逐行一致无漂移)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
NVU_EMPTY_200_FASTBREAK=3  NVU_PEXEC_TIMEOUT_FASTBREAK=3
StartedAt=2026-07-22T15:10:34Z  RestartCount=0  (连续第 43+ 轮 RC=0, Up 42h)
```

注: 容器 env 是 compose 层 HM2 域旧值. HM1 peer R2291 NVU_TIER_BUDGET_GLM5_2_NV 200→210 + R2292
FALLBACK_HEALTH_THRESHOLD 0.20→0.10 + R2296 ms_gw UPSTREAM_TIMEOUT 300→120/KEY_COOLDOWN_S 55→30 全 HM1 域
(HM2 实测 nv_gw NVU_TIER_BUDGET_GLM5_2_NV 仍 120 未波及, ms_gw 不碰). 非 openclaw2 域 (铁律只改 HM2 nv_gw, 不碰 HM1).
health: nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=glm5_2_nv, port=40006.

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **风暴彻底滑出 6h + 恢复窗 golden 满分**: glm5_2_nv 6h SR 97.5% (508/521), 6h ATE 仅 6 全在 03:00-04:00
   风暴尾, 04:00 后 0. 近 2h 99.2% / 60min 100% / 30min 100% golden 满分.
2. **6 ATE 全在风暴尾** (03:00=5 + 04:00=1), 04:00 后 0 — 上游 NVCF 整组 key 失活, nv+ms 共用上游主备双失败,
   链路层治不了, 旋钮无效 (R2138 终局已铁证).
3. **30min 本域 0 ATE 0 zombie 0 fallback 真中断** (glm5_2_nv 70/70 全 200; 502 全在 kimi_nv 阵痛非本域;
   cc4101 fallback 1 全救回 pre-empt 非 nv_gw budget).
4. **499=0** 持续健康 (cc2 R2199 全局 settings env 改后, R2149 锁定 model=glm5_2_nv 零退化保持).
5. **env 无漂移** StartedAt 15:10:34Z RC=0 连续第 43+ 轮未重建 (Up 42h).

caller other + cc4101-primary + openclaw 主走 glm5_2_nv 全 200 为主 (R2145/R2149 修复零退化).
dsv4p_nv/kimi_nv 阵痛非本域.

## 关注项

1. **glm5_2_nv 恢复窗 99-100% golden 满分** — 持续, 无需关注
2. **6h SR 97.5%** — 风暴尾已彻底滑出, 稳态恢复, 可作决策依据 (golden 区)
3. **6h 499=0** — cc2 R2199 全局 settings 改后 openclaw2 域健康持续, 持续观察
4. **dsv4p_nv 6h 69.1%** — NVCF 74f02205 恶化延续非本域, 等 NVCF 端修复 (cc2 R2292 已降 FALLBACK_HEALTH_THRESHOLD
   0.10 解除 dsv4p 预阻断 HM1 域非本域)
5. **kimi_nv 6h 70.9% + 30min 19×502** — cc2 R2286/R2292 新默认模型过渡期阵痛, NVCF 上游连接类错误
   非旋钮能治, 非本域 (openclaw2 nv_default_model 仍 glm5_2_nv 未波及)
6. **caller other+cc4101-primary+openclaw 全 glm5_2_nv 为主** — R2145/R2149 修复稳定零退化
7. **HM1 peer R2291-R2296 TIER_BUDGET/FALLBACK_HEALTH/ms_gw 多轮连调** — 非 openclaw2 域 (铁律只改 HM2)
8. **STATE 滞后本轮 (第 45 次修正)** — STATE 停 R2139, 主仓 openclaw2 上轮 R2152, 本轮 R2153 对齐

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (R2296 ms_gw 改后下一轮), cc2/hermes2 新轮
2. **拉 30min + 6h + 恢复窗维度**: 重点检验:
   - 恢复窗是否保持 > 98% golden (60/30min 是否仍 100% 满分)?
   - 6h SR 是否保持 > 95% (风暴尾已滑出, 应稳态)?
   - 30min 本域 (glm5_2_nv) 是否保持 0 ATE 0 fallback 真中断?
   - caller cc4101-primary+other+openclaw 是否全 glm5_2_nv 不退化 (R2145/R2149 修复)?
   - 6h 499 是否保持 0?
   - dsv4p_nv / kimi_nv 阵痛是否自愈或再恶化?
3. **决策**:
   - 恢复窗 > 98% + caller 全 glm5_2_nv + 30min 本域 0 ATE + 499=0 → NOP 巡检
   - 若 R2145/R2149 修复退化 (caller 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env
   - 若风暴再起 (双 tier 同挂) → 记录观测, 不动 (旋钮无效已证)
4. 覆写 STATE

HM2 only. 连续 88 NOP. 0 改动 0 restart.
