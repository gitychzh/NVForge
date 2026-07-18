1|# R1850 (HM2→HM1): NOP — 零 config-fixable, 全 NVCF content-filter zombie
2|
3|## 改前数据 (6h window, HM1 DB)
4|
5|```
6|SR: 33/42 = 78.6% (200:33 / 502:9)
7|```
8|
9|### 502 分类 (9条)
10|| error_type | count | 分析 |
11||---|---|---|
12|| zombie_empty_completion | 9 | NVCF content-filter 行为, non-config-fixable |
13|
14|### 模型维度
15|| mapped_model | total | ok | fail | avg_ms | max_ms |
16||---|---|---|---|---|---|
17|| glm5_2_nv | 19 | 19 | 0 | 6958 | 14181 |
18|| dsv4p_nv | 14 | 14 | 0 | 14718 | 40603 |
19|
20|### tier attempts
21|| tier | error_type | count |
22||---|---|---|
23|| glm5_2_nv | pexec_success | 39 |
24|| dsv4p_nv | 429_nv_rate_limit | 2 |
25|
26|### 30min window
27|```
28|SR: 0/4 = 0% (4条全部 zombie_empty_completion glm5_2_nv)
29|```
30|
31|### 关键观察
32|- 全部9条502 = zombie_empty_completion (glm5_2_nv), NVCF content-filter 行为, 非 config 可修
33|- dsv4p_nv 14/14 OK, avg 14718ms, max 40603ms — 高延迟在 NVCF 侧, 非 config 可修
34|- 2条 dsv4p_nv 429 rate limit (2/14=14% tier attempts, 0 request failure) — 低频, 不构成调参依据
35|- 3条 phantom ATE (all_tiers_exhausted + status=200) — 已 rescue 成功, 非问题
36|- 0 fallback 触发, 0 breaker OPEN, 0 新错误分类
37|- 容器 StartedAt: 2026-07-18T22:25:22Z (R1839 后重启, 无漂移)
38|
39|### env 无漂移
40|```
41|UPSTREAM_TIMEOUT=51 (R1839)
42|TIER_TIMEOUT_BUDGET_S=178 (R1840)
43|KEY_COOLDOWN_S=60 (R1833)
44|TIER_COOLDOWN_S=60 (R1833)
45|NVU_TIER_BUDGET_DSV4P_NV=39 (R1835)
46|NVU_TIER_BUDGET_GLM5_2_NV=60 (R1831)
47|MIN_OUTBOUND_INTERVAL_S=0
48|NVU_PEER_FALLBACK_TIMEOUT=122
49|NVU_MS_GW_FALLBACK_TIMEOUT=120
50|NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
51|```
52|全与 R1843/R1845/R1846 NOP 轮一致, 无漂移.
53|
54|## 决策: NOP — 不改
55|
56|- 全部 502 为 zombie_empty_completion: NVCF 侧 content-filter 行为, 非 HM1 任何 config 参数可修
57|- dsv4p_nv 高延迟: NVCF 侧, 非 config 可修
58|- 429 仅 2 次 tier-level (0 request failure), 不构成调参依据
59|- 无新错误分类, 无 fallback 恶化, 无 breaker OPEN
60|- 硬改违反铁律: 改前必有数据, 聚焦 nv_gw
61|- 0 restart 0 中断
62|
63|## 评判: 更少报错更快请求超低延迟稳定优先
64|- 9 条 zombie NVCF 非可控 → 不触发介入
65|- 链路稳, 无 config 可改依据 → NOP
66|
67|## ⏳ 轮到HM1优化HM2
68|
