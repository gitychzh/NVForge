# R2021 (HM2 cc2): NOP 巡检 R122 — 30min SR100%/6h SR96.40% 0 真中断, 连续冻结第 58 轮

## 数据 (本 session 拉取, 30min/6h 窗口; nv_gw StartedAt 2026-07-19T13:33:43Z 维 R1933 至今未 restart)

### nv_gw 成功率
- 30min: 200:46 / 502:0 → **SR = 46/46 = 100%** (无 502)
- 6h: 200:989 / 502:37 → **SR = 989/1026 = 96.40%**
- vs R2020 6h 96.39% (988/1025) → **+0.01pp 区间内持平非退化** (200 +1 / 502 +1 小样本波动)

### nv_gw 502 错误分类 (6h, 502=37 全已知三类 0 新可配置类)
- zombie_empty_completion: 23 (R2020=23 持平)
- stream_first_byte_timeout: 8 (R2020=8 持平)
- all_tiers_exhausted: 6 (R2020=6 持平)
- 0 新可配置类 (vs R2020 6h 502=37 完全持平 0 重新分布)

### abs_cap (双确认归零)
- 30min: 0; 6h: 0 (DB `error_type like '%abs%' or like '%cap%'` 0 rows)
- 连续多轮归零延续 (R1918 方案0 cap_origin 重置真实生效)

### fallback (30min, 7 条全 FALLBACK-OK 0 真中断)
- **7** FALLBACK-OK (R2020=7 → 本轮 7, 持平, 0 fallback 失败)
- 全 7 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (< chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类 cc4101 bug3 preempt 层)
- **120s 跑满类本轮 0** 持续趋稳归零 (R1951 4 → ... → R2020 0 → 本轮 0; 全部 fallback 都在 75s SKIP 层被兜住)
- 全 7 条被 cc4101 在 75s 抢断切 ms, ms 救回 → **0 条 fallback 失败 → CC 收 0 真 502**
- `grep -cE "both failed|ms.*fail|UPSTREAM-ERROR-SEEN"` cc4101 30min = 0 → 确认 0 真中断

### breaker
- cc4101 PRIMARY-BREAKER-OPEN 30min = **0**
- nv_gw 30min `grep -cE "BREAKER-FAIL|BREAKER.*OPEN|NV-ANTH-BREAKER-FAIL"` = **0** (R2015=0 → R2016=0 → R2018=0 → R2019=0 → R2020=0 → 本轮 0, **连续 7 轮无 recorded 事件, 偏好非恶化**)

### BUG-A 修复 (R1913) 真实生效确认
- 30min 内 `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **8 次** (R2005 3 / R2006 4 / R2007 5 / R2009 5 / R2011 4 / R2013 5 / R2014 7 / R2015 6 / R2016 6 / R2018 6 / R2019 8 / R2020 7 / 本轮 8, 区间内波动持续触发确认机制长期生效)

### tier 30min error_type (小样本波动非退化)
- pexec_success: 38 (R2020=42 → -4)
- pexec_conn_RemoteDisconnected: 3 (R2020=3 持平)
- pexec_429: 1 (R2020=1 持平)
- 非新可配置类, 上游 NVCF 抖动, 不需动

### /health + 容器状态
- nv_gw /health: ok, 5 keys, port 40006, nv_default_model dsv4p_nv
- nv_gw StartedAt = **2026-07-19T13:33:43Z** (R1933→R2021 未再 restart, docker inspect 核实)
- cc4101 StartedAt = 2026-07-19T12:10:22Z (R1926 step2.0 env up-d 后 0 restart)

## 拟改 / 决策

**NOP 巡检, 0 改动 0 restart, 连续冻结第 58 轮延续 (HM2 cc2 侧)**。

依据: 数据全部满足"稳态" (30min SR100%, 6h SR96.40%, 502 全 NVCF 上游已知三类 0 新可配置类, abs_cap 归零, fallback 全 75s SKIP 兜住 0 真中断, breaker 连续 7 轮未 OPEN, BUG-A 持续触发).

冻结理由 (连续第 58 轮) 仍成立: 半成品 (NVU_GLM52_EXP_BACKOFF) 未经 in-vivo 验证 (env 开关从未激活, 根本不在容器 env 中) + 激活需同步 chain_budget 120→420 + cc4101 PRIMARY_HEADER_TIMEOUT 60→450 + post-200 软挂换 key 未实现 + 24h 观测窗口. 风险/收益不对等 (当前 6h SR96.40% 0 真中断, abs_cap 连续多轮归零, BUG-A 修复真实生效, 120s 跑满类持续趋零, 边际收益小).

## 验证清单 (本轮 0 改动, 仅数据巡检)

- [x] nv_gw 30min SR 100% ≥ 94% 阈值 — 达标
- [x] nv_gw 6h SR 96.40% ≥ 95% 阈值 — 达标
- [x] 502 分类全已知三类, 0 新可配置类 — 达标
- [x] abs_cap 30min/6h 双确认归零 — 达标
- [x] fallback 全兜住 0 真中断 (7 条 FALLBACK-OK) — 达标
- [x] breaker 未 OPEN (cc4101 0 / nv_gw 0) — 达标
- [x] BUG-A SKIP-PEXEC2 持续触发 (8 次) — 达标
- [x] nv_gw StartedAt 仍 13:33:43Z (未 restart) — 达标
- [x] /health ok + 5 keys — 达标

## 下一轮

- 继续 NOP 巡检 (R123): 拉数据确认趋势, 重点看 6h SR 仍在 94-96.5% 区间非退化, 502 仍已知三类 0 新可配置类, fallback 全 75s SKIP 兜住 0 真中断, BUG-A 持续触发. 任一指标恶化 (6h SR<94% 或 502 新类或 fallback 失败或 breaker 真 OPEN) 才考虑动.
- 轮号: 下一轮 git pull 看最新, peer HM1 可能已抢 R2021+ hm2_optimize_hm1 前缀; cc2 用 R2022 或更大 hm2_cc2 前缀不撞号.
- 若未来要解冻: 需先 in-vivo 验证 NVU_GLM52_EXP_BACKOFF (env 激活 + chain_budget 120→420 + cc4101 PRIMARY_HEADER_TIMEOUT 60→450 同步) + 实现 post-200 软挂换 key + 24h 观测. 当前不动.

## 参数快照 (与 R2020/R2019/R2018/R2016/R2015/R2014 完全一致)

```
KEY_COOLDOWN_S=25
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_BIG_INPUT_FAIL_N=1
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=180
NV_INTEGRATE_KEY_COOLDOWN_S=90
TIER_COOLDOWN_S=25
NVU_BIG_INPUT_COOLDOWN_S=180
MIN_OUTBOUND_INTERVAL_S=0
```
(NVU_GLM52_EXP_BACKOFF 不在 env 中 = 关, 半成品冻结中. chain_budget 仍 120s, 未升 420. 本轮 0 改动.)
