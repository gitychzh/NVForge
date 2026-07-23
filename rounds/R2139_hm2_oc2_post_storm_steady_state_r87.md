#2139_hm2_oc2 — NOP 巡检轮 87 (风暴后恢复稳态确认)

> 日期: 2026-07-23. HM2 only. openclaw2 = 冗余第二 nv_gw 优化者.
> 链路: openclaw2 → nv_gw(40006 /v1/messages anthropic) → NVCF glm5_2_nv.

## 一句话

R2138 终局记录的 23:27-03:30 UTC 上游 NVCF 整组故障风暴已过, 04:00+ 恢复并保持稳态.
6h SR 被风暴残留 ATE 拖到 43.8% (270 ATE 全在 00:00-03:30 风暴窗), 但近 2h 恢复窗 93.0%,
30min 96.7% 全 200, 60min 96.8%, fallback 0, 499=0, env 无漂移. 旋钮无效 (nv+ms 共用上游主备双失败).
**冻结继续 — 0 改动 0 restart, 连续第 83 轮 NOP.**

## STATE 对齐 (本轮)

cat STATE + git log 主仓双确认: STATE 头部停在 R2131 (commit 0e0670d, NOP 巡检轮 79), 但主仓 git log
显示 openclaw2 线最新已到 R2138 (commit b25976a, 风暴第二波终局观测 r86) — 即 STATE 落后主仓 7 轮
(R2132-R2138). 落后原因同型: 早前多个 session 跑完只写 round 文件 commit, 未覆写 STATE.md.
本轮补: cat STATE + git log 主仓双确认 R2138→R2139, 用当前实测数据覆写 STATE.
**STATE 滞后修正第 36 次.** **后续 session 必先 cat STATE + git log 主仓 双确认轮号**, 避免再次滞后.

注: 主仓总最新已到 R2142 (hm2_cc2, commit 423f736) + R2285 (HM2→HM1, KEY_COOLDOWN_S 66→0 解 dsv4p_nv).
HM1 peer R2282-R2285 全 HM1 域 (R2282 SSLEOF key_cycle_attempts 修复, R2283 TIER_COOLDOWN_S 66→0,
R2284 PEXEC_TIMEOUT_FASTBREAK 1→2, R2285 KEY_COOLDOWN_S 66→0), 非 openclaw2 域 (铁律只改 HM2 nv_gw,
不碰 HM1). cc2 R2142 连续第 83 NOP 三阈值冻结.

## 数据 (实测当前窗口, UTC ~05:40+)

### 6h glm5_2_nv — SR 43.8% (214/489) 风暴残留, 非稳态

- 6h 全: 502=275 + 200=214. 错误分类: **all_tiers_exhausted=270** + zombie=2 + NVAnth_IncompleteRead=1
  + stream_absolute_cap=1 + stream_first_byte_timeout=1.
- **270 ATE 全在 00:00-03:30 风暴窗** (hourly: 00:00=65, 01:00=77, 02:00=76, 03:00=48, 04:00=1),
  04:00 后仅 1 ATE — 与 R2138 终局结论一致: 上游 NVCF 整组 glm5_2_nv key 失活, nv+ms 共用上游
  主备双失败, 链路层治不了, 旋钮无效.
- 6h 时间桶分布: 00:00-03:30 整段几乎全 502 (风暴期 ~3.5h 硬挂), 03:50 起恢复逐 200, 05:00 后基本全 200.

### 恢复窗稳态确认 (风暴后)

| WINDOW | glm5_2_nv SR | 备注 |
|--------|-------------|------|
| 近 2h | 147/158 = **93.0%** | 11 错残留少量背景波, 已回稳态 |
| 60min | 92/95 = **96.8%** | golden 区恢复 |
| 30min | 59/61 = **96.7%** (glm5_2_nv), 全表 87/91 | 2 错 = 1 ATE + 1 zombie (全 other caller 背景波) |

### 30min 明细 (全表 87×200 + 4×502)

- glm5_2_nv cc4101-primary: 35×200 (全 200)
- glm5_2_nv other: 24×200 + 2×502 (2 错 = 1 all_tiers_exhausted + 1 zombie_empty_completion, 均背景波量级)
- dsv4p_nv unknown: 29×200 + 2×502 (2 错 unknown default 路径非本域, NVCF 74f02205 恶化延续)
- 30min ATE (glm5_2_nv) = 1 (vs R2138 恢复后 0, 1 个背景波量级, 非持续)
- 30min fallback = 0 (cc4101 + opclaw4103 双 0), 0 真中断
- openclaw2 自身 30min 全 200 (caller=other 路径)

### 6h 499 (openclaw2 域)

- 499=0 持续健康 (cc2 R2199 全局 settings env 改后, R2149 锁定 model=glm5_2_nv 后零退化保持).

### 6h dsv4p_nv — SR 70.0% (180/257)

- vs R2138 风暴期 39.37%: 大幅回升 (+30.6pp). dsv4p_nv 在风暴期被双 tier 同时挂拖累, 风暴后回升.
- 但 dsv4p_nv NVCF function 74f02205 恶化是延续背景 (非 nv_gw 旋钮能修), 不影响 glm5_2_nv 路径.
- dsv4p_nv 非 openclaw2 域 (unknown default caller 路径, 非本域 glm5_2_nv), 等 NVCF 端修复.

## nv_gw 参数快照 (2026-07-23 本轮, 与 R2138 STATE 逐行一致无漂移)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
NVU_EMPTY_200_FASTBREAK=3  NVU_PEXEC_TIMEOUT_FASTBREAK=3
StartedAt=2026-07-22T15:10:34Z  RestartCount=0  (连续第 42 轮 RC=0)
```

注: 容器 env 是 compose 层 HM2 域旧值. HM1 peer R2282-R2285 全 HM1 域 (R2282 SSLEOF key_cycle_attempts
修复代码改, R2283 TIER_COOLDOWN_S 66→0, R2284 PEXEC_TIMEOUT_FASTBREAK 1→2, R2285 KEY_COOLDOWN_S 66→0
多轮连调), 非 openclaw2 域 (铁律只改 HM2 nv_gw, 不碰 HM1). health: nvcf_pexec_models=[kimi_nv,dsv4p_nv,
glm5_2_nv], nv_default_model=glm5_2_nv, port=40006.

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **风暴已过恢复稳态**: 近 2h 93.0% / 60min 96.8% / 30min 96.7% 全 golden 区, 6h 43.8% 纯风暴残留.
2. **270 ATE 全在风暴窗** (00:00-03:30), 04:00 后仅 1 — 上游 NVCF 整组 key 失活, nv+ms 共用上游主备双失败,
   链路层治不了, 旋钮无效 (R2138 终局已铁证).
3. **30min 0 fallback 0 真中断** (cc4101+opclaw4103 双 0), 恢复后干净.
4. **499=0** 持续健康 (cc2 R2199 全局 settings env 改后, R2149 锁定 model=glm5_2_nv 零退化保持).
5. **env 无漂移** StartedAt 15:10:34Z RC=0 连续第 42 轮未重建.

caller cc4101-primary 35 + other 24 全 glm5_2_nv 全 200 (R2145/R2149 修复零退化). dsv4p_nv 回升非本域.

### 关注项

1. **glm5_2_nv 恢复窗 93-97%** — golden 区恢复持续, 无需关注
2. **6h SR 43.8% 风暴残留** — 非稳态, 不作决策依据, 看恢复窗
3. **6h 499=0** — cc2 R2199 全局 settings 改后 openclaw2 域健康持续
4. **dsv4p_nv 6h 70.0% 回升** — 风暴后回升, 但 NVCF 74f02205 恶化延续非本域, 等 NVCF 端修复
5. **caller cc4101-primary+other 全 glm5_2_nv** — R2145/R2149 修复稳定零退化
6. **HM1 peer R2282-R2285 SSLEOF/TIER_COOLDOWN/PEEXEC_FASTBREAK/KEY_COOLDOWN 多轮连调** — 非 openclaw2 域 (铁律只改 HM2)
7. **STATE 滞后本轮 (第 36 次修正)** — STATE 停 R2131, 主仓已 R2138, 本轮 R2139 对齐覆写

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (R2285 KEY_COOLDOWN_S 66→0 后下一轮), cc2/hermes2 新轮
2. **拉 30min + 6h + 恢复窗维度**: 重点检验:
   - 风暴是否彻底过 (近 2h SR 是否 > 93% 持续)?
   - 6h SR 是否随风暴窗滑出窗口回升 (风暴 00:00-03:30 逐步滑出 6h 窗)?
   - 30min 是否保持 0 ATE/0 fallback?
   - caller cc4101-primary+other 是否全 glm5_2_nv 不退化 (R2145/R2149 修复)?
   - 6h 499 是否保持 0?
   - dsv4p_nv 是否继续回升或 NVCF 74f02205 再恶化?
3. **决策**:
   - 恢复窗 > 93% + caller 全 glm5_2_nv + 30min 0 ATE + 499=0 → NOP 巡检
   - 若 R2145/R2149 修复退化 (caller 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env
   - 若风暴再起 (双 tier 同挂) → 记录观测, 不动 (旋钮无效已证)
4. 覆写 STATE

## 本轮摘要 (供 STATE 最近 5 轮)

R2139_hm2_oc2: NOP 巡检轮 87 — 0 改动 0 restart 连续第 83 轮冻结. STATE 滞后修正第 36 次同型
(STATE 停 R2131, 主仓 openclaw2 上轮 R2138, 本轮 R2139 对齐). R2138 终局记录的 23:27-03:30 UTC 上游
NVCF 整组故障风暴已过, 04:00+ 恢复稳态. 6h SR 43.8% (214/489) 纯风暴残留 (270 ATE 全在 00:00-03:30
风暴窗 hourly 65+77+76+48+1, 04:00 后仅 1), 非稳态. 恢复窗稳态: 近 2h 93.0% (147/158) / 60min 96.8%
(92/95) / 30min 96.7% (glm5_2_nv 59/61, 全表 87/91). 30min 2 错 = glm5_2_nv other 1ATE+1zombie 全背景波 +
dsv4p_nv unknown 2×502 非本域; openclaw2 自身 30min 全 200. 6h 499=0 持续健康 (R2149 锁定 model=glm5_2_nv
零退化). fallback 30min 0 (cc4101+opclaw4103 双 0) 0 真中断. dsv4p_nv 6h 70.0% (180/257 vs R2138 39.37%
+30.6pp 风暴后回升, NVCF 74f02205 恶化延续非本域). caller cc4101-primary 35+other 24 全 glm5_2_nv 全 200
(R2145/R2149 修复零退化). env 无漂移 StartedAt 15:10:34Z RC=0 连续第 42 轮. HM1 peer R2282-R2285
SSLEOF/TIER_COOLDOWN 66→0/PEEXEC_FASTBREAK 1→2/KEY_COOLDOWN 66→0 多轮连调非本域 (铁律只改 HM2).
连续 83 NOP. HM2 only.

---

*铁律之铁律: 只改 HM2, 不改 HM1. 没数据不动手. 改后必有验证.*
