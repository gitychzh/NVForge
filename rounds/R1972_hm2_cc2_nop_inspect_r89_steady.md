# R1972 (HM2 cc2) — NOP 巡检 R89, 连续第 26 轮冻结指数退避

> 轮号基线: 上一轮 cc2 R1971 (d9bbd48). peer HM1 agent 已占 R1971 (f78d5bb, hm2_optimize_hm1 前缀).
> 本轮 cc2 = R1972 (git pull 后确认 R1972 未被 peer 占). 0 改动 0 restart, NOP 巡检 R89.

## 数据 (本 session 拉取, nv_gw StartedAt 2026-07-19T13:33:43Z 维 R1933, elapsed ~43h+)

### nv_gw 30min 窗口
- SR = 53/55 = **94.7%** (200:53 / 502:2). 小样本偏稳 (R1971 96.6% / R1970 98.2% / R1967 98.2% / R1966 97.1% / R1964 96.6% 区间稳态非退化, 本轮与 R1961 96.0% 区间内偏低端, 非介入线).
- 502=2 全已知类: **zombie_empty_completion×1** (glm5_2_nv 出口 IP 段 134.195.101.0/24 同源快回空) + **all_tiers_exhausted×1** (NVCF 上游 tier 全失败).
- 30min 502=2 与 R1971 完全一致 (同 ATE×1 + zombie×1), 非新可配置类, 小样本波动.

### nv_gw 6h 窗口 (大样本稳态)
- SR = 632/667 = **94.8%** (200:632 / 502:35). 与 R1971 94.8% **完全一致 0 漂移**, 大样本稳态区间 (R1960-1971 94.0-95.0% 内 0 抖动).
- 502=35 全已知类: zombie×23 (R1971 23, 一致) + ATE×8 (R1971 8, 一致) + first_byte_timeout×4 (R1971 4, 一致). 与 R1971 **0 漂移完全一致**.

### abs_cap (DB 双重确认)
- 30min = **0** (`error_type like '%abs%'` 0 rows)
- 6h = **0** (0 rows)
- R1918 方案0 cap_origin 重置持续归零, 连续多轮: R1931=4 → R1942=2 → R1943=2 → R1946=0 → ... → R1967=0 → R1970=0 → R1971=0 → **R1972=0**.
- 日志中 NV-PEEK-CAP-RESET 是方案0 reset 事件非真 abs_cap 502.

### fallback (cc4101 日志 30min)
- **7** FALLBACK-OK (0 真中断, 0 fallback 失败): 全 7 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (< chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类 cc4101 bug3 preempt 层).
- R1971 fallback 6×75s SKIP, 本轮 7×75s SKIP 微升 1 无恶化 (R1967 8 / R1970 7 / R1971 6 / R1972 7 区间内波动). **120s 跑满类本轮 0** 持续趋稳归零 (R1951 4 → R1953 2 → R1954 0 → R1956 0 → R1957 0 → R1967 0 → R1970 0 → R1971 0 → R1972 0).
- 日志中 6 条 "saves ~120s" 全是 `NV-GLM52-CHAIN-SKIP-PEXEC2 ... go all_keys_exhausted -> ms_fb` (BUG-A 修复路径省约 120s/请求), **非 120s 跑满类**, 不要混淆.
- ms 救回时间 2.2/4.0/2.2/2.7/3.0/13.1/4.0s, 全部成功 → CC 收 0 真 502.
- `grep -cE "both failed|ms.*fail|UPSTREAM-ERROR-SEEN"` = **0** → 确认 0 真中断.
- 注: 日志见 6 条 `NV-MS-FB-SERVED ms_gw served glm5_2_nv fallback (state=CLOSED)` — nv_gw 内部 ms_fb 路径记 breaker failure, state 仍 CLOSED (计数未达 5/300s), 非 NV-ANTH-BREAKER-FAIL 事件, 与 breaker OPEN 无关.

### breaker
- cc4101 `PRIMARY-BREAKER-OPEN` 30min = **0**
- nv_gw `NV-ANTH-BREAKER-FAIL` 30min = **0**
- R1957 抖到 2, R1967/R1970/R1971/R1972 均 0, 连续多轮 CLOSED 不 OPEN.

### BUG-A 修复 (R1913) 真实生效确认
- 30min `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **6 次**, skip _try_tier_keys 第二轮省约 ~120s/fallback 请求.
- R1913 阶段1.5 补全 `_chain_failed=True` + `if _chain_failed:` 跳过 pexec 第二轮机制持续触发.
- 历史: R1952 6 / R1951 1 / R1953 5 / R1954 4 / R1956 2 / R1957 1 / R1967 2 / R1970 4 / R1971 5 / **R1972 6**.

## 验证
- env 无漂移: UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_GLM5_2_NV=120, NVU_STREAM_ABSOLUTE_CAP_S=150, MIN_OUTBOUND_INTERVAL_S=0, KEY_COOLDOWN_S=25, NVU_BIG_INPUT_FAIL_N=1, NVU_BIG_INPUT_COOLDOWN_S=180. 与 R1971 完全一致.
- `NVU_GLM52_EXP_BACKOFF` **不在容器 env 中** → 半成品代码从未激活, 冻结物理成立.
- /health: ok (nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv, nv_default_model=dsv4p_nv).
- docker ps: nv_gw/cc4101/ms_gw/logs_db 全 Up.
- StartedAt: nv_gw 13:33:43Z (维 R1933, 0 restart, ~43h+); cc4101 12:10:22Z (维 R1926, 0 restart, ~44h+).

## 决策: NOP 无据不改
介入四条全不满足:
1. 6h SR94.8% 大样本稳态 (与 R1971 0 漂移), 30min 94.7% 小样本偏稳, 非"连续 3+ 轮跌破 80%"介入线.
2. 502 全 zombie+ATE+first_byte_timeout 已知类 (与 R1971 完全一致 0 漂移), 非新可配置类. abs_cap 30min=0/6h=0 双重确认.
3. breaker OPEN 30min=0 连续多轮, nv_gw BREAKER-FAIL 30min=0 全 CLOSED 不 OPEN.
4. fallback 7/30min 全 FALLBACK-OK 被 ms 兜住 0 真中断, 低于 15/30min 介入线, 无新监督者激活指令 (R1928 冻结理由仍成立).

**连续第 26 轮冻结指数退避** (R1928 冻结 → R1929/R1930/R1931/R1933-1971 NOP → R1972 NOP).
冻结理由仍成立: 半成品未 in-vivo 验证 (env 开关从未激活, NVU_GLM52_EXP_BACKOFF 根本不在 env 中) + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测. 风险/收益不对等 (当前 6h SR94.8% 0 真中断, abs_cap 连续多轮归零, BUG-A 修复真实生效 6 次/30min, 120s 跑满类持续趋零, 边际收益小).

## 用户诉求 (2026-07-19 01:40) "可以报错但不能让 cc2 中断" 仍达成
R1972 0 真中断; 7 条 FALLBACK-OK 全被 ms_gw 兜住, 0 fallback 失败.
