# R2022 (HM2 cc2): NOP 巡检 R123 — 30min SR100%/6h SR96.53% 0 真中断, 连续冻结第 59 轮

## 数据 (本 session 拉取, 30min/6h 窗口; nv_gw StartedAt 2026-07-19T13:33:43Z 维 R1933 至今未 restart)

### nv_gw 成功率
- 30min: 200:56 / 502:0 → **SR = 56/56 = 100%** (无 502)
- 6h: 200:1002 / 502:36 → **SR = 1002/1038 = 96.53%**
- vs R2021 6h 96.40% (989/1026) → **+0.13pp 区间内偏升非退化** (200 +13 / 502 -1 小样本波动)

### nv_gw 502 错误分类 (6h, 502=36 全已知三类 0 新可配置类)
- zombie_empty_completion: 22 (R2021=23 → -1 小样本波动)
- stream_first_byte_timeout: 8 (R2021=8 持平)
- all_tiers_exhausted: 6 (R2021=6 持平)
- 0 新可配置类 (vs R2021 6h 502=37 → 本轮 36, -1 zombie 减小, 0 重新分布)

### abs_cap (双确认归零)
- 30min: 0; 6h: 0 (DB `error_type like '%abs%' or like '%cap%'` 0 rows)
- 连续多轮归零延续 (R1918 方案0 cap_origin 重置真实生效)

### fallback (30min, 8 条全 FALLBACK-OK 0 真中断)
- **8** FALLBACK-OK (R2021=7 → 本轮 8, +1 区间内波动, 0 fallback 失败)
- 全 8 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (< chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类 cc4101 bug3 preempt 层)
- **120s 跑满类本轮 0** 持续趋稳归零 (R1951 4 → ... → R2021 0 → 本轮 0; 全部 fallback 都在 75s SKIP 层被兜住)
- 全 8 条被 cc4101 在 75s 抢断切 ms, ms 救回 → **0 条 fallback 失败 → CC 收 0 真 502**
- `grep -cE "both failed|ms.*fail|UPSTREAM-ERROR-SEEN"` cc4101 30min = 0 → 确认 0 真中断

### breaker
- cc4101 PRIMARY-BREAKER-OPEN 30min = **0**
- nv_gw 30min `grep -cE "BREAKER-FAIL|BREAKER.*OPEN|NV-ANTH-BREAKER-FAIL"` = **0** (R2015=0 → R2016=0 → R2018=0 → R2019=0 → R2020=0 → R2021=0 → 本轮 0, **连续 8 轮无 recorded 事件, 偏好非恶化**)

### BUG-A 修复 (R1913) 真实生效确认
- 30min 内 `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **7 次** (R2005 3 / R2006 4 / R2007 5 / R2009 5 / R2011 4 / R2013 5 / R2014 7 / R2015 6 / R2016 6 / R2018 6 / R2019 8 / R2020 7 / R2021 8 / 本轮 7, 区间内波动持续触发确认机制长期生效)

### tier 30min error_type (小样本波动非退化)
- pexec_success: 39 (R2021=38 → +1 小样本波动)
- pexec_conn_RemoteDisconnected: 4 (R2021=3 → +1 小样本波动)
- pexec_429: 1 (R2021=1 持平)
- 非新可配置类, 上游 NVCF 抖动, 不需动

### /health + 容器状态
- `curl /health` = ok, passthrough, nv_num_keys=5, nvcf_pexec_models=[kimi_nv, dsv4p_nv, glm5_2_nv], port 40006
- nv_gw StartedAt = **2026-07-19T13:33:43Z** (= R1933 restart NameError 修复后, R1933→R2022 未再 restart, docker inspect 核实)
- cc4101 StartedAt = 2026-07-19T12:10:22Z (= R1926 step2.0 env up-d 后, 0 restart)

## 拟改 / 预期
- **NOP (0 改动 0 restart)**. 全指标满足"稳态": 30min SR100%, 6h SR96.53% (>95%), 502 全 NVCF 上游已知三类 (0 新可配置类), abs_cap 归零, fallback 全 75s SKIP 兜住 (0 fallback 失败 0 真中断), breaker 未 OPEN (连续 8 轮无事件), BUG-A SKIP-PEXEC2 持续触发.
- 冻结理由 (连续第 59 轮) 仍成立: 半成品指数退避 (R1928) env NVU_GLM52_EXP_BACKOFF 不在容器 env 中 = 关, 从未 in-vivo 激活; 激活需同步 chain_budget 120→420 + cc4101 PRIMARY_HEADER_TIMEOUT 60→450 + post-200 软挂换 key 未实现 + 24h 观测窗口. 风险/收益不对等 (当前 6h SR96.53% 0 真中断, abs_cap 连续多轮归零, BUG-A 修复真实生效, 120s 跑满类持续趋零, 边际收益小).

## 验证清单
- [x] 30min SR = 100% (56/56, 502=0) ≥ 94% 阈值 ✓
- [x] 6h SR = 96.53% (1002/1038) ≥ 95% 阈值 ✓ (vs R2021 96.40% +0.13pp 偏升非退化)
- [x] 6h 502 全已知三类 (zombie 22 / stream_first_byte_timeout 8 / all_tiers_exhausted 6), 0 新可配置类 ✓
- [x] abs_cap 30min/6h 双确认归零 ✓
- [x] fallback 8 全 FALLBACK-OK, 0 fallback 失败, `both failed`=0 → 0 真中断 ✓
- [x] 120s 跑满类 0 (全 SKIP 层兜住) ✓
- [x] breaker cc4101 PRIMARY-BREAKER-OPEN=0 / nv_gw BREAKER-FAIL/OPEN=0 (连续 8 轮无事件) ✓
- [x] BUG-A SKIP-PEXEC2 触发 7 次 (机制长期生效) ✓
- [x] /health ok + nv_gw StartedAt 13:33:43Z 维 R1933 未 restart ✓

## 结论
连续第 59 轮 NOP 冻结, 0 改动 0 restart. 数据全部满足"稳态", 无任一指标恶化. 延续 R1928 冻结决定 (半成品未 in-vivo 验证 + 激活需同步 3 组件改动 + 24h 观测窗口, 风险/收益不对等). 用户诉求 (2026-07-19 "可以报错但不能让 cc2 中断") 仍达成: 0 真中断, 8 条 FALLBACK-OK 全被 ms_gw 兜住.

(注: 跳过 R2021 hm2_optimize_hm1 因 peer HM1 已用该前缀; cc2 用 R2022 hm2_cc2 前缀避撞号, 同号不同前缀无冲突. 本轮 peer HM1 未抢 R2022, 号空闲.)
