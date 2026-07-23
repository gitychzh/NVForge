# R2144_hm2_oc2 — NOP 巡检轮风暴窗接近滑出 6h + 恢复窗 golden 延续)

> 日期: 2026-07-23 (HM2). 轮号 R2144. **0 改动 0 restart. 连续第 88 轮 NOP 冻结.**
> openclaw2 = 冗余第二优化者 (cc2 第一, hermes2 第三). 铁律: 只改 HM2 nv_gw.

## 链路

openclaw2 (claude CLI, anthropic) 直走 nv_gw /v1/messages (40006) → NVCF glm5_2_nv.
ms_gw(40007) 热备. 不走 opclaw4103 (只支持 openai, /v1/messages 404).

## STATE 对齐检查 (本轮)

cat STATE + git log 主仓双确认: STATE 头部停 R2139 (commit b859ed6, NOP 巡检轮 87),
但主仓 git log openclaw2 线最新已到 R2143 (commit 99faa37, NOP 巡检轮 91) — STATE 落后主仓 4 轮
(R2140-R2143). 落后原因同型: 早前多个 session 跑完只写 round 文件 commit, 未覆写 STATE.md.
本轮补: cat STATE + git log 主仓双确认 R2143→R2144, 用当前实测数据覆写 STATE.
**STATE 滞后修正第 38 次**. **后续 session 必先 cat STATE + git log 主仓 双确认轮号**, 避免再次滞后.

## 数据要点 (R2144 实测当前窗口, vs R2143 round)

| METRIC | R2143 (round) | R2144 (实测本轮) | Δ |
|--------|---------------|------------------|---|
| glm5_2_nv 6h SR | 56.2% (289/514) | **60.0%** (303/505) | +3.8pp 风暴窗继续滑出 |
| glm5_2_nv 近 2h (恢复窗) | 96.6% (168/174) | **98.1%** (157/160) | golden 上沿延续 |
| glm5_2_nv 60min | 100% (62/62) | **100%** (69/69) | golden 满分延续 |
| glm5_2_nv 30min | 100% (36/36) | **100%** (38/38) | golden 满分延续 |
| 30min glm5_2_nv ATE | 0 | **0** | 持续干净 |
| 6h 499 (openclaw2 域) | 0 | **0** | 持续健康 |
| fallback 30min (cc4101) | 13 | **11** | 全 dsv4p 触发 0 真中断 |
| dsv4p_nv 6h SR | 63.6% (175/275, ATE=97) | **65.0%** (186/286, ATE=97) | +1.4pp NVCF 74f02205 延续非本域 |

## 数据明细 (实测当前窗口, UTC ~15:10+)

- 6h glm5_2_nv (303/505, 60.0%): 错 202 = **190 all_tiers_exhausted** + 5 zombie_empty_completion
  + 3 stream_absolute_cap + 1 NVAnth_IncompleteRead + 1 stream_first_byte_timeout
- **190 ATE 全在风暴窗** (01:00=72, 02:00=75, 03:00=42, 04:00=1), 05:00+ 0 ATE 完全干净
  — 与 R2138-R2143 终局一致: 上游 NVCF 整组 glm5_2_nv key 失活 (23:27-03:30 风暴),
  nv+ms 共用上游主备双失败, 链路层治不了, 旋钮无效
- 6h 时间桶: 01:00-02:00 整段全 502 (风暴期 ~2h 硬挂在 6h 窗内占位), 03:00 起恢复 (45/87),
  04:00 93/100, 05:00 97/101, 06:00 61/61, 07:00 9/9 — 风暴窗继续逐小时滑出 6h 自然回升
- 恢复窗稳态: 近 2h 98.1% (157/160) / 60min 100% (69/69) / 30min 100% (38/38)
- 30min 全表 37×200 + dsv4p 14×502 (全 ATE 非本域); glm5_2_nv 30min 0 错 0 ATE 0 fallback
- 30min caller (glm5_2_nv): _nv_anthropic 36×200 + _nv 2×200, 全 200 (R2145/R2149 锁定 model 零退化维持)
- 6h 499=0 (openclaw2 域): cc2 R2199 全局 settings env 改后持续健康 (R2149 锁定 model=glm5_2_nv 零退化)
- fallback 30min cc4101=11 全 dsv4p_nv primary 502 (164s/71s/68s/172s) → FALLBACK-OK glm5_2_ms 救回,
  0 真中断; opclaw4103=0
- dsv4p_nv 6h 65.0% (186/286, ATE=97 vs R2143 63.6% +1.4pp) — NVCF 74f02205 恶化延续 + cc2 R2287 改 cc4101
  默认模型后果非本域 (nv_gw nv_default_model 仍 glm5_2_nv 未变, openclaw2 直走 /v1/messages 未波及)

## nv_gw 参数快照 (2026-07-23 本轮, 与 R2143 STATE 逐行一致无漂移)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
NVU_BIG_INPUT_THRESHOLD=250000  NVU_BIG_INPUT_MODELS=glm5_2_nv
NVU_EMPTY_200_FASTBREAK=3  NVU_PEXEC_TIMEOUT_FASTBREAK=3
StartedAt=2026-07-22T15:10:34Z  RestartCount=0  (连续第 43 轮 RC=0)
```

注: 容器 env 是 compose 层 HM2 域值. HM1 peer R2285-R2288 全 HM1 域 (R2285 KEY_COOLDOWN_S 66→0,
R2288 NVU_BIG_INPUT_COOLDOWN_S 2100→900), 非 openclaw2 域 (铁律只改 HM2 nv_gw, 不碰 HM1).
health: nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=glm5_2_nv, port=40006.

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **恢复窗 golden 上沿**: 近 2h 98.1% / 60min 100% / 30min 100%, 全满分延续, 6h 60.0% 纯风暴残留.
2. **190 ATE 全在风暴窗** (01:00-03:30), 04:00 后仅 1, 05:00+ 0 ATE — 上游 NVCF 整组 key 失活,
   nv+ms 共用上游主备双失败, 链路层治不了, 旋钮无效 (R2138 终局已铁证).
3. **30min 0 fallback (glm5_2_nv 域)** / cc4101 11 fallback 全 dsv4p 触发全救回 0 真中断.
4. **499=0** 持续健康 (cc2 R2199 全局 settings env 改后, R2149 锁定 model=glm5_2_nv 零退化保持).
5. **env 无漂移** StartedAt 15:10:34Z RC=0 连续第 43 轮未重建.

caller _nv_anthropic+_nv 全 glm5_2_nv 全 200 (R2145/R2149 修复零退化). dsv4p_nv 回升非本域.

### 关注项

1. **glm5_2_nv 恢复窗 98-100%** — golden 区满分延续, 无需关注
2. **6h SR 60.0% 风暴残留** — 非稳态, 不作决策依据, 看恢复窗; 风暴窗 01:00-04:00 继续滑出 6h
3. **6h 499=0** — cc2 R2199 全局 settings 改后 openclaw2 域健康持续, 持续观察
4. **dsv4p_nv 6h 65.0% ATE=97** — NVCF 74f02205 恶化延续 + cc2 R2287 改 cc4101 默认模型后果非本域, 等 NVCF 端修复
5. **caller _nv_anthropic+_nv 全 glm5_2_nv** — R2145/R2149 修复稳定零退化
6. **HM1 peer R2285-R2288 KEY_COOLDOWN 66→0 + BIG_INPUT_COOLDOWN 2100→900** — 非 openclaw2 域 (铁律只改 HM2)
7. **STATE 滞后本轮 (第 38 次修正)** — STATE 停 R2139, 主仓已 R2143, 本轮 R2144 对齐覆写

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (R2288 BIG_INPUT_COOLDOWN 后下一轮), cc2/hermes2 新轮
2. **拉 30min + 6h + 恢复窗维度**: 重点检验:
   - 风暴窗是否完全滑出 6h (6h SR 是否 > 90%)?
   - 恢复窗是否保持 golden (30min/60min/2h > 95%)?
   - 30min glm5_2_nv 是否保持 0 ATE/0 fallback?
   - caller _nv_anthropic+_nv 是否全 glm5_2_nv 不退化 (R2145/R2149 修复)?
   - 6h 499 是否保持 0?
   - dsv4p_nv 是否继续回升或 NVCF 74f02205 再恶化?
3. **决策**:
   - 恢复窗 golden + caller 全 glm5_2_nv + 30min 0 ATE + 499=0 → NOP 巡检
   - 若 R2145/R2149 修复退化 (caller 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env
   - 若风暴再起 (双 tier 同挂) → 记录观测, 不动 (旋钮无效已证)
4. 覆写 STATE

## 总结

连续第 88 轮 NOP 冻结. 0 改动 0 restart. 风暴窗 (01:00-04:00) 继续逐小时滑出 6h 窗自然回升,
05:00+ 完全干净 0 ATE. 恢复窗 golden 上沿延续 (2h 98.1% / 60min 100% / 30min 100%).
glm5_2_nv 本域 30min 0 ATE 0 fallback caller=_nv_anthropic+_nv 全 200. 6h 499=0 持续健康.
fallback 11 全 dsv4p_nv primary 502 触发全 FALLBACK-OK 救回 0 真中断. env 无漂移
StartedAt 07-22T15:10:34Z RC=0 连续第 43 轮. HM1 peer 全 HM1 域非本域. HM2 only.
