# R2023 (HM2 cc2): NOP 巡检 R124 — 连续第 60 轮冻结指数退避

## 数据 (本 session 拉取, nv_gw StartedAt 13:33:43Z 维 R1933)

### nv_gw 30min 窗口
- SR = 64/65 = **98.46%** (200:64 / 502:1)
- 502=1: all_tiers_exhausted×1 (已知类, NVCF 上游抖动)
- vs R2022 30min 502=0 → 本轮 502=1 (+1 小样本波动, 类别仍是已知类 all_tiers_exhausted 非新可配置类)

### nv_gw 6h 窗口
- SR = 999/1035 = **96.52%** (200:999 / 502:36)
- vs R2022 6h 96.53% (1002/1038) **-0.01pp 区间内完全持平非退化** (200 -3 / 502 持平)
- 502=36 全已知三类 (vs R2022 6h 502=36 完全持平 0 重新分布):
  - zombie_empty_completion×22 (持平)
  - stream_first_byte_timeout×8 (持平)
  - all_tiers_exhausted×6 (持平)
- **0 新可配置类**

### abs_cap
- 30min=0 / 6h=0 (DB `error_type ilike '%abs%' or ilike '%cap%'` 0 rows 双重确认)
- R1918 方案0 cap_origin 重置持续归零, 连续多轮 (R1946=0 → ... → R2022=0 → 本轮=0)

### fallback (cc4101 30min)
- **7 条 FALLBACK-OK** (0 真中断, 0 fallback 失败)
- 全 7 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (< chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类 cc4101 bug3 preempt 层)
- vs R2022 fallback 8 → 本轮 7 (-1 区间内波动持平 0 失败)
- **120s 跑满类本轮 0 持续趋稳归零** (R1951 4 → R1954 0 → ... → R2022 0 → 本轮 0; 全部 fallback 都在 75s SKIP 层被兜住, 无任何跑满 120s chain budget)
- 全 7 条被 cc4101 在 75s 抢断切 ms, ms 救回 → **0 条 fallback 失败 → CC 收 0 真 502**
- `grep -cE "both failed|ms.*fail|UPSTREAM-ERROR-SEEN"` cc4101 30min = 0 → 确认 0 真中断

### breaker
- cc4101 PRIMARY-BREAKER-OPEN 30min = **0**
- nv_gw 30min `grep -cE "BREAKER-FAIL|BREAKER.*OPEN|NV-ANTH-BREAKER-FAIL"` = **0**
- (R2015=0 → R2016=0 → R2018=0 → R2019=0 → R2020=0 → R2021=0 → R2022=0 → 本轮 0, 连续 9 轮无 recorded 事件, 偏好非恶化)

### BUG-A 修复 (R1913) 真实生效
- 30min 内 `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **7 次**
- (R2005 3 / R2006 4 / R2007 5 / R2009 5 / R2011 4 / R2013 5 / R2014 7 / R2015 6 / R2016 6 / R2018 6 / R2019 8 / R2020 7 / R2021 8 / R2022 7 / 本轮 7, 区间内波动持续触发确认机制长期生效)

### tier 30min error_type
- pexec_success×39 / pexec_conn_RemoteDisconnected×3
- (注: R2022 pexec_success=39/pexec_conn=4/pexec_429=1 → 本轮 pexec_success=39 持平/pexec_conn=4→3 -1/pexec_429 1→0 偏好, 小样本波动; 上游 NVCF 抖动; 非新可配置类, 不需动)

## 决策: NOP (0 改动 0 restart)

数据全部满足"稳态":
- 30min SR>94% 实际 98.46%, 6h SR>95% 实际 96.52%
- 502 全 NVCF 上游已知三类 (zombie / stream_first_byte_timeout / all_tiers_exhausted), 0 新可配置类
- abs_cap 30min/6h 双确认归零
- fallback 全 75s SKIP 被兜住, 0 fallback 失败 0 真中断
- breaker 未 OPEN (cc4101/nv_gw 30min 全 0)
- BUG-A SKIP-PEXEC2 持续触发 7 次

冻结理由 (连续第 60 轮) 仍成立:
- 半成品未 in-vivo 验证 (env NVU_GLM52_EXP_BACKOFF 不在容器 env 中 = 从未激活)
- 激活需同步 chain_budget 120→420 + cc4101 PRIMARY_HEADER_TIMEOUT 60→450 + post-200 软挂换 key 未实现
- 24h 观测窗口
- 风险/收益不对等 (当前 6h SR96.52% 0 真中断, abs_cap 连续多轮归零, BUG-A 修复真实生效, 120s 跑满类持续趋零, 边际收益小)

## 验证

本轮 NOP, 0 改动 0 restart, 无需验证 (nv_gw StartedAt 仍 2026-07-19T13:33:43Z = R1933, R1933→R2023 未再 restart)。
参数快照与 R2022/R2021/R2020/R2019/R2018 完全一致。

## 用户诉求达成

(2026-07-19 01:40) "可以报错但不能让 cc2 中断" 仍达成 (R2023 0 真中断; 7 条 FALLBACK-OK 全被 ms_gw 兜住, 0 fallback 失败)。

## commit
R2023 (HM2 cc2): NOP 巡检 R124 — 连续第 60 轮冻结指数退避 (env NVU_GLM52_EXP_BACKOFF 从未激活), 0 改动 0 restart. 数据: 30min SR98.46% (64/65, 502=1 all_tiers_exhausted 已知类) / 6h SR96.52% (999/1035, 502=36 全已知三类 0 新可配置类完全持平 R2022) / abs_cap 30min=0,6h=0 双确认归零 / fallback 7 条全 75s SKIP-CIRCUIT 被兜住 0 真中断 0 失败 (120s 跑满类持续归零) / breaker cc4101+nv_gw 30min 全 0 连续 9 轮无事件 / BUG-A SKIP-PEXEC2 持续触发 7 次. vs R2022 6h -0.01pp 区间内完全持平非退化 (200 -3 / 502 36→36 持平 0 重新分布). 冻结理由仍成立 (半成品未 in-vivo 验证 + 激活需同步 3 组件 + 24h 观测窗口 + 风险收益不对等). (注: 跳过 R2022 hm2_optimize_hm1 因 peer HM1 前缀取走 R2022 commit a851e12 改 HM1 KEY/TIER_COOLDOWN 54→50 不碰 HM2; cc2 用 R2023 hm2_cc2 前缀避撞号, 同号不同前缀无冲突)
