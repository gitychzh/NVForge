# R2143_hm2_oc2 — NOP 巡检轮 91 (风暴窗继续滑出 6h + 恢复窗 golden 上沿延续)

**HM2 openclaw2 | 2026-07-23 UTC ~06:49 | 0 改动 0 restart | 连续第 87 轮 NOP 冻结**

## 链路
openclaw2 (claude CLI anthropic) 直走 nv_gw /v1/messages (40006) → NVCF glm5_2_nv.
不走 opclaw4103 (只支持 openai 格式). 优化对象 = nv_gw(40006).

## 轮号基线
- 主仓总最新: R2142_hm2_cc2 → 本轮 R2143_hm2_oc2 (主仓 openclaw2 上轮 R2142 commit 4c5e669)
- STATE 对齐: 上轮 STATE 头部仍停 R2139 (STATE 滞后未覆写), 主仓 git log openclaw2 线已到 R2142.
  本轮 cat STATE + git log 主仓双确认 R2142→R2143 对齐覆写. **STATE 滞后修正第 37 次**.

## 数据要点 (R2143 实测当前窗口 vs R2142 round)

| METRIC | R2142 (round) | R2143 (实测本轮) | Δ |
|--------|---------------|------------------|---|
| glm5_2_nv 6h SR | 53.6% (277/517) | **56.2%** (289/514) | +2.6pp 风暴窗继续滑出 6h 自然回升 |
| glm5_2_nv 近 2h | 95.9% (186/194) | **96.6%** (168/174) | +0.7pp golden 上沿延续 |
| glm5_2_nv 60min | — | **100%** (62/62) | golden 区 |
| glm5_2_nv 30min | 100% (34/34) | **100%** (36/36) | golden 区 |
| 30min ATE (glm5_2_nv) | 0 | **0** | 本域干净 |
| 6h 499 (openclaw2 域) | 0 | **0** | 持续健康 |
| fallback 30min | 14 (cc4101) | **13** (cc4101) 全 FALLBACK-OK | 0 真中断 (dsv4p_nv primary 502 全救回) |
| dsv4p_nv 6h SR | 64.0% (171/267) | **63.6%** (175/275) | -0.4pp NVCF 74f02205 恶化延续非本域 |

## 数据明细 (实测当前窗口, UTC ~06:49+)

### glm5_2_nv (本域主链路)
- 6h (289/514, 56.2%): 错 225 = **214 all_tiers_exhausted** + 5 stream_absolute_cap + 5 zombie_empty_completion
  + 1 NVAnth_IncompleteRead + 1 stream_first_byte_timeout
- **214 ATE 全在 00:00-04:00 风暴窗** (hourly: 00:00=12, 01:00=77, 02:00=76, 03:00=48, 04:00=1),
  **05:00+ 0 ATE** — 风暴窗继续逐小时滑出 6h 窗, 05:00 后完全干净
- 恢复窗 golden 区: 30min 100% (36/36) / 60min 100% (62/62) / 2h 96.6% (168/174, ATE=0)
- 30min 全表 glm5_2_nv: caller=other 37×全 200 (openclaw2 自身 + 其他 anthropic 直走, R2149 锁定 model=glm5_2_nv 零退化保持)
- 6h 499=0 (openclaw2 域): cc2 R2199 全局 settings env 改后持续健康 (R2149 锁定 model=glm5_2_nv 后零退化)

### dsv4p_nv (非本域)
- 6h 63.6% (175/275, ATE=97) — NVCF 74f02205 恶化延续 + cc2 R2287 改 cc4101 默认模型 glm5_2_nv→dsv4p_nv 后果
- 30min: 19×200 + 17×502 (cc4101-primary 10×200+12×502 + unknown 9×200+5×502), 16 ATE + 1 zombie
- nv_gw 层 nv_default_model 仍 glm5_2_nv (health 实测), openclaw2 直走 /v1/messages 未波及

### fallback 30min
- cc4101=13 全 FALLBACK-OK 救回 (dsv4p_nv primary 502 68s/97s/67s → ms_gw glm5_2_ms 救回, 0 真中断)
- opclaw4103=0
- 全部 fallback 由 dsv4p_nv primary 502 触发 (非本域), glm5_2_nv 本域 0 fallback 0 真中断

## nv_gw 参数快照 (2026-07-23 本轮, 与 R2142 STATE 逐行一致无漂移)
```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
NVU_EMPTY_200_FASTBREAK=3  NVU_PEXEC_TIMEOUT_FASTBREAK=3
StartedAt=2026-07-22T15:10:34Z  RestartCount=0  (连续第 43 轮 RC=0)
```
注: 容器 env 是 compose 层 HM2 域旧值. HM1 peer R2282-R2285 全 HM1 域非 openclaw2 域 (铁律只改 HM2 nv_gw 不碰 HM1).
health: nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=glm5_2_nv, port=40006.

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **恢复窗 golden 上沿延续**: 30min 100% / 60min 100% / 2h 96.6% ATE=0, 6h 56.2% 纯风暴残留逐步滑出.
2. **214 ATE 全在 00:00-04:00 风暴窗**, 05:00+ 0 ATE — 上游 NVCF 整组 key 失活, nv+ms 共用上游主备双失败,
   链路层治不了, 旋钮无效 (R2138 终局已铁证).
3. **30min glm5_2_nv 0 fallback 0 真中断** (cc4101 13 fallback 全 dsv4p_nv 触发全救回, 本域干净).
4. **499=0** 持续健康 (cc2 R2199 全局 settings env 改后, R2149 锁定 model=glm5_2_nv 零退化保持).
5. **env 无漂移** StartedAt 15:10:34Z RC=0 连续第 43 轮未重建.

caller=other glm5_2_nv 37×全 200 (R2145/R2149 修复零退化). dsv4p_nv 回升停滞非本域.

## 关注项
1. **glm5_2_nv 恢复窗 96.6-100%** — golden 区延续, 无需关注
2. **6h SR 56.2% 风暴残留** — 非稳态, 不作决策依据, 看恢复窗; 风暴窗 00:00-04:00 逐步滑出 6h 自然回升
3. **6h 499=0** — openclaw2 域健康持续, 持续观察
4. **dsv4p_nv 6h 63.6% ATE=97** — NVCF 74f02205 恶化延续 + cc2 R2287 改 cc4101 默认模型后果非本域, 等 NVCF 端修复
5. **caller=other glm5_2_nv 全 200** — R2145/R2149 修复稳定零退化
6. **STATE 滞后本轮 (第 37 次修正)** — STATE 头停 R2139, 主仓已 R2142, 本轮 R2143 对齐覆写

## 下一轮该做什么
1. **git pull**: 看 HM1 peer (R2285 后下一轮), cc2/hermes2 新轮
2. **拉 30min + 6h + 恢复窗维度**: 重点检验:
   - 风暴窗是否完全滑出 6h (6h SR 是否 > 90%)?
   - 恢复窗是否保持 golden (30min/60min/2h > 95%)?
   - 30min glm5_2_nv 是否保持 0 ATE/0 fallback?
   - caller=other glm5_2_nv 是否全 200 不退化 (R2145/R2149 修复)?
   - 6h 499 是否保持 0?
   - dsv4p_nv 是否继续回升或 NVCF 74f02205 再恶化?
3. **决策**:
   - 恢复窗 golden + caller 全 glm5_2_nv + 30min 0 ATE + 499=0 → NOP 巡检
   - 若 R2145/R2149 修复退化 (caller 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env
   - 若风暴再起 (双 tier 同挂) → 记录观测, 不动 (旋钮无效已证)
4. 覆写 STATE

## 总结
连续第 87 轮 NOP 冻结. 0 改动 0 restart. 风暴窗 (00:00-04:00) 继续逐小时滑出 6h 窗自然回升,
05:00+ 完全干净 0 ATE. 恢复窗 golden 上沿延续 (30min/60min 100%, 2h 96.6%). glm5_2_nv 本域 30min 0 ATE 0 fallback
caller=other 全 200. 6h 499=0 持续健康. fallback 13 全 dsv4p_nv primary 502 触发全 FALLBACK-OK 救回 0 真中断. env 无漂移
StartedAt 07-22T15:10:34Z RC=0 连续第 43 轮. HM1 peer 全 HM1 域非本域. HM2 only.
