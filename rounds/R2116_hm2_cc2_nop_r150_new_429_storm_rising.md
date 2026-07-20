# R2116 (hm2_cc2): NOP R150 连续第 86 轮冻结 — 新一轮 NVCF 429 风暴再起记录

> 本轮 = NOP 巡检 R150, 连续第 86 轮冻结指数退避方案. 0 改动 0 restart.
> HM2 only. 只改 HM2 不改 HM1. 不碰 ms_gw (40007 热备).
>
> ⚠ 本轮核心事件: R2113 刚判定"R2111 风暴完全自愈"后约 40min, **新一轮 NVCF 429 rate limit
> 风暴再起**, 模式与 R2111 完全一致 (tier 429 爆发 → 20:00 桶 502×19 峰值上浮). 本轮拉数据时
> CST 04:06 踩在风暴进行中 (19:45-20:00 UTC 高峰), 30min 大窗被污染. 但 0 真中断, 502 全 NVCF
> 已知类 0 新可配, breaker 未恶化 — 仍是 NVCF 上游抖动非网关逻辑缺陷, 解冻不对症.

## 数据 (本 session 拉取, 当前 CST 04:06-04:08; UTC 20:06-20:08)

### 30min nv_gw 成功率 + 错误分类
- 30min SR = 100/133 = **75.2%** (200:100 / 502:32 / 429:1)
  - vs R2113 拉时 (CST 03:25) 30min SR 90.4% → **-15.2pp 恶化**
  - 但 30min 大窗被 19:45-20:00 UTC 风暴高峰污染 (见时间分布)
- 30min 502=32 全 **all_tiers_exhausted×31 + zombie_empty_completion×2** (全 NVCF 上游已知类, **0 新可配置类**) ✅
- 30min 429=1

### 小窗 SR (风暴进行中, 从峰值回落尾期)
- last5 = 8/28 = 28.6% (含 20:00 桶峰值 502×19 主导)
- last10 = 16/44 = 36.4%
- last15 = 42/70 = 60.0%
- last20 = 63/92 = 68.5%
- **last3 = 7/9 = 77.8%** (200:7 / 502:2) — 比 20:00 峰值 (SR 29.6%) 回升, 但 502 仍零星出现 (1-2min 一条), **风暴正处回落尾期, 未完全平息**

### 502 时间分布 (5min 桶, UTC)
| 桶(UTC) | CST | ok | e502 | e429 | total | 备注 |
|---|---|---|---|---|---|---|
| 19:20 | 03:20 | 12 | 1 | 0 | 13 | 稳态 |
| 19:25 | 03:25 | 20 | 2 | 0 | 22 | 稳态 |
| 19:30 | 03:30 | 13 | 2 | 0 | 15 | 稳态 |
| 19:35 | 03:35 | 20 | 2 | 0 | 22 | 稳态 |
| 19:40 | 03:40 | 18 | 2 | 0 | 20 | 稳态 |
| 19:45 | 03:45 | 23 | 1 | 0 | 24 | **tier 429×5 首现** |
| 19:50 | 03:50 | 23 | 1 | 0 | 24 | **tier 429×15 峰值** (tier retry 吸收, 502 仍×1) |
| 19:55 | 03:55 | 8 | 7 | 1 | 16 | **tier 429×8 + 502×7 爆发上浮** |
| 20:00 | 04:00 | 8 | 19 | 0 | 27 | **502×19 峰值** (SR 29.6%, all_tiers 主导) |
| 20:05 | 04:05 | 4 | 0 | 0 | 4 | 部分桶 (到 04:06), 可能回落中 (样本小) |

### tier 30min 错误明细 (严重恶化)
- **429_nv_rate_limit×28** (vs R2113 拉时 30min 429=0, **0→28 爆发!**) — NVCF 上游 429 rate limit 风暴再起
  - vs R2111 风暴期 tier 429×10, 本轮 28 更猛
- pexec_success×24
- NVCFPexecRemoteDisconnected×9
- pexec_conn_RemoteDisconnected×4
- empty_200×2
- **0 pexec_SSLEOFError** (vs R2111 风暴期×4, 本轮 SSL 类 0 — 本次纯 429 风暴, 非 SSL 抖动)

### fallback (30min)
- **11 FALLBACK-OK** (0 真中断, 0 fallback 失败)
- 全 11 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (header/ttfb timeout 75s < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类 cc4101 bug3 preempt 层)
- **0 条 120s 跑满类** (持平 R2113)
- req 样本: 3c252111 / 14179a06 / acb018eb / 3b06341f ... (全被 ms_gw 兜住)
- cc4101 `grep -cE "both failed|ms.*fail|UPSTREAM-ERROR-SEEN"` 30min = **0** → 0 真中断确认 ✅

### breaker
- cc4101 PRIMARY-BREAKER-OPEN 30min = **0**
- nv_gw `grep -cE "BREAKER-FAIL|BREAKER.*OPEN|NV-ANTH-BREAKER-FAIL"` 30min = **0**
- **state CLOSED 未达 OPEN 阈值 = 连续第 21 轮验证未恶化** (符合 CLAUDE.md "recorded 但 CLOSED 是机制正常吸收, 不是恶化")

### BUG-A 修复 (R1913) 生效确认
- 30min 内 `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **7 次** (vs R2113 5 次 +2, 持续复活触发中, 机制真实生效) ✅

### abs_cap (R1918 方案0)
- 30min=0 ✅ / 6h=0 ✅ (6h 窗口起点 14:08 UTC, 含 R2111 + 本轮风暴, 但 R1918 cap 类 0 条, 非失效)

### 6h 窗口 (仍含远古风暴, 失真不采信)
- 6h 502=1216 / 200=448 / 429=99 (含 R2111 风暴 + 本轮新风暴 + R2107 重启前远古风暴, 失真不采信)
- 6h 窗口起点 14:08 UTC = CST 22:08 昨晚

### nv_gw 健康 + 参数
- /health = ok (proxy_role=passthrough, nv_num_keys=5, nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=dsv4p_nv, port=40006) ✅
- docker inspect StartedAt: nv_gw=**2026-07-20T18:10:28Z** (R2107 后未再漂移, 连续第 7 轮核实 18:10 稳定) / cc4101=2026-07-19T12:10:22Z (0 restart)
- env 仍 peer R2108 改后值 (KEY60/TIER180/MIN_OUTBOUND10), 非 cc2 改, 本轮 0 改动

## 本轮发生了什么 (决策)

**NOP 巡检 R150, 连续第 86 轮冻结指数退避, 0 改动 0 restart.**

核心事件: R2113 刚判定"R2111 风暴完全自愈"后约 40min, **新一轮 NVCF 429 rate limit 风暴再起**
(19:45-20:00 UTC = 03:45-04:00 CST), 模式与 R2111 完全一致:
1. 19:45 tier 429×5 首现 → 19:50 tier 429×15 峰值 (tier retry 吸收, 502 仍只×1)
2. 19:55 tier 429×8 + 502×7 爆发上浮 (tier retry 撑不住)
3. 20:00 502×19 峰值 (SR 29.6%, all_tiers_exhausted 主导)
4. last3min (20:05-20:07) SR 77.8% 回升, 但 502 仍零星 — 风暴正处回落尾期

**本轮 30min SR 75.2% < 90% 阈值, 但判定为 NOP 仍正确**:
1. **正处风暴进行中** (非"持续<90% 非风暴污染"): 30min 大窗被 19:45-20:00 风暴高峰污染, 小窗
   已显示回落 (last3 77.8% > 20:00 桶 29.6%)
2. **502 全 NVCF 已知类** (all_tiers_exhausted×31 + zombie×2), **0 新可配置类** → 不满足 STATE
   里"502 出新可配置类才需重新评估解冻"的触发条件
3. **根因 NVCF 上游 429 rate limit**, 非网关逻辑缺陷 — 解冻指数退避不对症 (429 风暴延长
   chain_budget 反拖 SR, R2111/R2112/R2113 三轮已论证)
4. **0 真中断**: fallback 11 条全 75s SKIP-CIRCUIT 被 ms_gw 兜住, 0 fallback 失败, 用户诉求
   "可以报错但不能让 cc2 中断"仍达成 ✅
5. **breaker/BUG-A/abs_cap 全部未恶化**: breaker 30min=0 连续第 21 轮 CLOSED / BUG-A 触发
   7 次 / abs_cap 30min=0
6. NVCF 429 旋钮: peer R2108 已调 KEY60/TIER180, **cc2 不碰 peer 改的旋钮**

**冻结理由 (连续第 86 轮) 仍成立**:
- 半成品 (NVU_GLM52_EXP_BACKOFF) 未经 in-vivo 验证 (env 开关从未激活, 不在容器 env 中)
- 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测窗口
- 风险/收益不对等 (当前 last3min 77.8% 0 真中断, abs_cap 30min 归零, BUG-A 修复真实生效; 边际收益小; 本轮风暴同 R2111 模式, 非逻辑缺陷, 预期自愈)

## 验证结果

本轮 0 改动 0 restart, 无需验证 (无改动). 健康检查通过:
- nv_gw /health = ok
- docker inspect StartedAt nv_gw=18:10:28Z (连续第 7 轮未漂移) / cc4101=12:10:22Z
- docker ps: nv_gw Up 2 hours / cc4101 Up 32 hours / ms_gw Up 7 hours / logs_db Up 4 days

## 状态变化 (cc2 视角)

- nv_gw StartedAt 仍 18:10:28Z (连续第 7 轮核实未漂移)
- env 仍 peer R2108 改后值 (KEY60/TIER180/MIN_OUTBOUND10), cc2 0 改动 0 restart
- 本轮需记录的变化:
  1. **新一轮 NVCF 429 风暴再起** (19:45-20:00 UTC), 30min SR 75.2% (-15.2pp vs R2113 90.4%)
  2. tier 30min 429_nv_rate_limit 0→28 爆发 (vs R2113 0, 比 R2111 风暴期×10 更猛)
  3. 502 全 all_tiers_exhausted×31+zombie×2 NVCF 已知类 0 新可配 (vs R2113 502=11)
  4. fallback 7→11 全兜 0 真中断 0 失败 0 条 120s 跑满 (75s SKIP-CIRCUIT)
  5. breaker/BUG-A(7次)/abs_cap(0) 全部未恶化持平

## 下一轮该做什么

- **继续 NOP 巡检 (R151, 连续第 87 轮冻结)**: 确认本轮 429 风暴是否如 R2111 一样自愈 (R2111
  风暴 02:45-03:00 CST, R2112/R2113 确认 30min 内自愈). 重点看:
  1. 30min SR 是否完全回到 94-96% 稳态 (风暴完全滚出 30min 窗口需 CST 04:30 后, 即 30min
     窗口起点 >= 04:00 才不含 19:55-20:00 高峰)
  2. tier 429_nv_rate_limit 是否回落到 0 (本轮 28)
  3. 502 分类是否仍全 NVCF 已知类 0 新可配置类
  4. fallback 是否仍全 75s SKIP-CIRCUIT 被兜住 0 失败; **关注 120s 跑满类是否再现增多** (本轮 0 条)
  5. breaker 30min recorded 是否仍 0 (连续第 22 轮); nv_gw StartedAt 是否仍 18:10:28Z (连续第 8 轮)
- **若持续恶化才考虑动**: 任一指标恶化 (30min SR 持续<90% **非风暴污染** 且 502 出新可配置类
  或 fallback 失败或 breaker 真 OPEN 切流) 才考虑重新评估解冻. 本轮不满足 (风暴进行中 + 0 新可配类)
- **6h SR 仍失真不采信**: 等 CST 08:10 后 6h 窗口完全滚出 R2111+本轮风暴期 (即 6h 前是 02:10
  重启点) 才采信 6h SR
- **轮号**: peer hm2_optimize_hm1 已到 R2115; cc2 用 R2117 或更大 hm2_cc2 前缀不撞号
- **若未来要解冻**: 需先 in-vivo 验证 NVU_GLM52_EXP_BACKOFF (env 激活 + chain_budget 120→420
  + cc4101 PRIMARY_HEADER_TIMEOUT 60→450 同步), 且实现 post-200 软挂换 key, 再 24h 观测. 当前不动

## HM2 only. 不碰 HM1. 不碰 ms_gw. 0 改动 0 restart.
