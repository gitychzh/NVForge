# R1960 (HM2 cc2): NOP 巡检 R81 — 30min SR94.7%/6h SR94.0% 0 真中断, 连续冻结第 18 轮延续

> 轮号: R1960 (cc2 自优化, HM2 only)
> 前序: R1958 (c03103d, 连续冻结第 17 轮 NOP R80; R1959 被 peer HM1 agent 占用改 NVU_BIG_INPUT_COOLDOWN_S 21600->86400 仅动 round file 不碰 HM2 nv_gw)
> 模式: nv 直连 (cc4101→nv_gw), 指数退避半成品冻结中 (env NVU_GLM52_EXP_BACKOFF 不在 env 中=关, 从未 in-vivo 激活)
> 本轮: NOP 巡检 R81, 连续第 18 轮冻结指数退避, 0 改动 0 restart

## 改前数据 (本 session 18:37Z UTC 拉取, nv_gw 已起 elapsed ~29h, cc4101 elapsed ~30h)

### 30min 窗口
- nv_gw 30min SR = 54/57 = **94.7%** (200:54 / 502:3), 小样本抖动区间 (R1958 97.5 / R1957 96.8 / R1956 97.7, 本轮 94.7 偏低但样本 57 中等非退化)
- 30min 502=3 全 NVCF 上游侧已知类: **zombie_empty_completion×2** (全 glm5_2_nv, 出口 IP 段 134.195.101.0/24 同源快回空) + **stream_first_byte_timeout×1**
- abs_cap 30min=0 (DB `error_type like '%abs%'` 0 rows 双重确认; R1918 方案0 cap_origin 重置持续归零连续多轮)
- fallback **5** FALLBACK-OK (0 真中断, 0 fallback 失败):
  - 4×75s `PRIMARY-FAIL-SKIP-CIRCUIT` (< chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类 cc4101 bug3 preempt 层)
  - **1×120s** chain budget 跑满 (req=7ea872ed @02:30:12, 120099ms; nv_gw chain 跑满 120s 触发 cc4101 PRIMARY-FAIL → ms_fb)
  - 全 5 条被 cc4101 切 ms, ms 救回 3.9-6.7s → 0 条 fallback 失败 → CC 收 0 真 502
  - `grep 502` / `both failed` / `ms.*fail` 搜索结果为空 → 确认 0 真中断
  - R1958 fallback 4 条全 75s SKIP, 本轮 5 条微升 (+1) + 出现 1 条 120s 跑满类; **120s 跑满类趋势**: R1951 4 → R1953 2 → R1954 0 → R1956 0 → R1957 0 → R1958 0 → R1960 1, 仍是趋稳区间内微抖 (+1 远未达 >15/30min 介入线)
- breaker cc4101 PRIMARY-BREAKER-OPEN 30min = **0**; nv_gw NV-ANTH-BREAKER-FAIL 30min = **2** (2 条 zombie mid-stream soft-fail → breaker recorded state=('CLOSED', 2, 0); **breaker state 仍 CLOSED** 计数 2 未达阈值 5/300s)
  - R1957 计数 1 / R1958 计数 1 / 本轮计数 2, 升 1 仍 CLOSED 不 OPEN, 符合已知 pattern
- BUG-A 修复 (R1913) 真实生效确认: 30min `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **1 次** (skip _try_tier_keys 第二轮省约 ~120s/fallback 请求)
- NV-PEEK-CAP-RESET 30min = 4 条 (方案0 reset 事件非真 502)

### 6h 窗口
- nv_gw 6h SR = 584/621 = **94.0%** (200:584 / 502:37), 大样本稳态区间 (R1942-1958 93.0-95.2% 内, 与 R1958 93.9% 几乎一致微升 0.1pp)
- 6h 502=37 全已知类: **zombie×22** + **all_tiers_exhausted×10** + **stream_first_byte_timeout×5**
  - zombie×22 (R1957/R1958 22, 本轮 22, 完全一致)
  - all_tiers_exhausted×10 (R1957/R1958 12, 本轮 10, -2 微降无恶化; 全 dsv4p_nv all_tiers_failed_in_mapped_tier 子类)
  - first_byte_timeout×5 (R1957/R1958 5, 本轮 5, 完全一致; 全 dsv4p_nv)
- abs_cap 6h=0 (DB `like '%abs%'` 0 rows 双重确认, R1918 方案0 持续归零连续多轮 R1931→R1942→R1943→R1946→R1947→R1949→R1951→R1952→R1953→R1954→R1956→R1957→R1958→R1960)

### 验证 (env 无漂移 + 容器状态)
- nv_gw /health: ok (nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv)
- docker ps: nv_gw Up 5 hours / cc4101 Up 6 hours / ms_gw Up 2 days / logs_db Up 3 days, 全 Up
- nv_gw StartedAt = 2026-07-19T13:33:43Z (0 restart, 维 R1933, elapsed ~29h @ 18:37Z UTC)
- cc4101 StartedAt = 2026-07-19T12:10:22Z (0 restart, 维 R1926, elapsed ~30h @ 18:37Z UTC)
- env 快照 (无漂移, 与 R1957/R1958 完全一致):
  - UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_GLM5_2_NV=120, NVU_STREAM_ABSOLUTE_CAP_S=150
  - NVU_GLM52_EXP_BACKOFF **不在 env 中=关** (半成品冻结, 从未 in-vivo 激活, env 里根本无此变量)
  - MIN_OUTBOUND_INTERVAL_S=0, KEY_COOLDOWN_S=25, KEY_AUTHFAIL_COOLDOWN_S=60, NVU_BIG_INPUT_FAIL_N=1, NVU_BIG_INPUT_COOLDOWN_S=180, NV_INTEGRATE_KEY_COOLDOWN_S=90, TIER_COOLDOWN_S=25
- cc4101 env: PRIMARY_HEADER_TIMEOUT=60, CC4101_STREAM_TOTAL_DEADLINE_S=480 (R1926 改), CC4101_PRIMARY_SKIP_S=30, CC4101_PRIMARY_FAIL_THRESHOLD=3

## 决策: NOP 无据不改 (连续第 18 轮冻结)

**介入四条全不满足** → NOP 无据不改:
1. 6h SR94.0% 大样本稳态区间 (R1942-1958 93.0-95.2% 内), 30min 94.7% 小样本抖动, 非"连续 3+ 轮跌破 80%"介入线
2. 502 全 zombie+ATE+first_byte_timeout 已知类, 非新可配置类, abs_cap 30min=0/6h=0 (DB 双重确认)
3. breaker OPEN 30min=0 连续多轮, nv_gw BREAKER-FAIL 30min=2 全 CLOSED 不 OPEN (计数 2 未达 5/300s)
4. fallback 5/30min 全 FALLBACK-OK 被 ms 兜住 0 真中断, 低于 15/30min 介入线, 无新监督者激活指令 (R1928 冻结理由仍成立)

**指数退避激活决策仍冻结 (连续第 18 轮)**: R1928 冻结理由 (半成品未 in-vivo 验证 + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测) 仍成立. env NVU_GLM52_EXP_BACKOFF 根本不在容器 env 中 → 半成品代码从未激活, 冻结决定物理成立. 当前链路稳态 (6h SR94.0% 0 真中断, abs_cap 连续多轮归零, BUG-A 修复真实生效 1 次/30min, 120s 跑满类持续趋稳) + 本轮无新监督者激活指令 → 继续冻结.

## 本轮结论

- 0 改动 0 restart. 连续第 18 轮 NOP 冻结指数退避 (R1928 冻结 → R1929/R1930/R1931/R1933-1958/R1960 NOP).
- 数据与 R1958 几乎一致: 6h SR 94.0% (R1958 93.9%) 微升 0.1pp; 6h 502 分类 zombie×22 一致 / ATE×10 (R1958 12, -2 微降) / first_byte_timeout×5 一致; 30min SR 94.7% (R1958 97.5%) 小样本偏低属抖动非退化; fallback 5 (R1958 4) 微升 +1 全 FALLBACK-OK; abs_cap 30min=0/6h=0 持续归零; breaker 30min=2 全 CLOSED 不 OPEN (计数升到 2 仍 <5); BUG-A 修复 1 次/30min 持续生效.
- 用户诉求 (2026-07-19 01:40) "可以报错但不能让 cc2 中断" 仍达成 (R1960 0 真中断; 5 条 FALLBACK-OK 全被 ms_gw 兜住, 0 fallback 失败).
