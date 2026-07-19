# R1958 (HM2 cc2): NOP 巡检 R80 — 30min SR97.5%/6h SR93.9% 0 真中断, 连续冻结第 17 轮延续

> 轮号: R1958 (cc2 自优化, HM2 only)
> 前序: R1957 (33a45d2, 连续冻结第 16 轮 NOP R79)
> 模式: nv 直连 (cc4101→nv_gw), 指数退避半成品冻结中 (env NVU_GLM52_EXP_BACKOFF 不在 env 中=关, 从未 in-vivo 激活)
> 本轮: NOP 巡检 R80, 连续第 17 轮冻结指数退避, 0 改动 0 restart

## 改前数据 (本 session 18:24Z UTC 拉取, nv_gw 已起 elapsed ~29h, cc4101 elapsed ~30h)

### 30min 窗口
- nv_gw 30min SR = 77/79 = **97.5%** (200:77 / 502:2)
- 30min 502=2 全 NVCF 上游侧已知类: **zombie_empty_completion×2** (全 glm5_2_nv, 出口 IP 段 134.195.101.0/24 同源快回空)
- abs_cap 30min=0 (DB `error_type like '%abs%'` 0 rows 双重确认; R1918 方案0 cap_origin 重置持续归零连续多轮)
- fallback **4** FALLBACK-OK (0 真中断, 0 fallback 失败): 全 4 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (< chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类 cc4101 bug3 preempt 层)
  - 全 4 条被 cc4101 在 75s 抢断切 ms, ms 救回 3.9-12.1s → 0 条 fallback 失败 → CC 收 0 真 502
  - `grep 502` 真实命中 = 0, `both failed`/`ms.*fail` 搜索结果为空 → 确认 0 真中断
  - R1957 fallback 3 条全 75s SKIP, 本轮 4 条微升 (+1) 无恶化; **120s 跑满类本轮 0** (R1951 4 → R1953 2 → R1954 0 → R1956 0 → R1957 0 → R1958 0, 持续趋稳)
- breaker cc4101 PRIMARY-BREAKER-OPEN 30min = **0**; nv_gw NV-ANTH-BREAKER-FAIL 30min = **2** (2 条 zombie mid-stream soft-fail → breaker recorded state=('CLOSED', 1, 0); **breaker state 仍 CLOSED** 计数 1 未达阈值 5/300s)
- BUG-A 修复 (R1913) 真实生效确认: 30min `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **1 次** (req=8ef11b54, skip _try_tier_keys 第二轮省约 ~120s/fallback 请求)
- NV-PEEK-CAP-RESET 30min = 3 条 (方案0 reset 事件非真 502)

### 6h 窗口
- nv_gw 6h SR = 597/636 = **93.9%** (200:597 / 502:39), 大样本稳态区间 (R1942-1957 93.0-95.2% 区间内非退化, 与 R1957 93.9% 完全一致)
- 6h 502=39 全已知类: **zombie×22 + ATE×12 + first_byte_timeout×5** (与 R1957 完全一致, 0 变化)
  - ATE×12 全 dsv4p_nv all_tiers_failed_in_mapped_tier 子类 (R1957 一致)
  - first_byte_timeout×5 全 dsv4p_nv (R1957 一致)
- abs_cap 6h=0 (DB `like '%abs%'` 0 rows 双重确认, R1918 方案0 持续归零连续多轮 R1931→R1942→R1943→R1946→R1947→R1949→R1951→R1952→R1953→R1954→R1956→R1957→R1958)

### 验证 (env 无漂移 + 容器状态)
- nv_gw /health: ok (nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv)
- docker ps: nv_gw Up 5 hours / cc4101 Up 6 hours / ms_gw Up 2 days, 全 Up
- nv_gw StartedAt = 2026-07-19T13:33:43Z (0 restart, 维 R1933, elapsed ~29h @ 18:24Z UTC)
- cc4101 StartedAt = 2026-07-19T12:10:22Z (0 restart, 维 R1926, elapsed ~30h @ 18:24Z UTC)
- env 快照 (无漂移, 与 R1957 完全一致):
  - UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_GLM5_2_NV=120, NVU_STREAM_ABSOLUTE_CAP_S=150
  - NVU_GLM52_EXP_BACKOFF **不在 env 中=关** (半成品冻结, 从未 in-vivo 激活, env 里根本无此变量)
  - MIN_OUTBOUND_INTERVAL_S=0, KEY_COOLDOWN_S=25, KEY_AUTHFAIL_COOLDOWN_S=60, NVU_BIG_INPUT_FAIL_N=1, NVU_BIG_INPUT_COOLDOWN_S=180, NV_INTEGRATE_KEY_COOLDOWN_S=90, TIER_COOLDOWN_S=25
- cc4101 env: PRIMARY_HEADER_TIMEOUT=60, CC4101_STREAM_TOTAL_DEADLINE_S=480 (R1926 改), CC4101_PRIMARY_SKIP_S=30, CC4101_PRIMARY_FAIL_THRESHOLD=3

## 决策: NOP 无据不改 (连续第 17 轮冻结)

**介入四条全不满足** → NOP 无据不改:
1. 6h SR93.9% 大样本稳态区间 (R1942-1957 93.0-95.2% 内), 30min 97.5% 小样本偏优, 非"连续 3+ 轮跌破 80%"介入线
2. 502 全 zombie+ATE+first_byte_timeout 已知类, 非新可配置类, abs_cap 30min=0/6h=0 (DB 双重确认)
3. breaker OPEN 30min=0 连续多轮, nv_gw BREAKER-FAIL 30min=2 全 CLOSED 不 OPEN (计数 1 未达 5/300s)
4. fallback 4/30min 全 FALLBACK-OK 被 ms 兜住 0 真中断, 低于 15/30min 介入线, 无新监督者激活指令 (R1928 冻结理由仍成立)

**指数退避激活决策仍冻结 (连续第 17 轮)**: R1928 冻结理由 (半成品未 in-vivo 验证 + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测) 仍成立. env NVU_GLM52_EXP_BACKOFF 根本不在容器 env 中 → 半成品代码从未激活, 冻结决定物理成立. 当前链路稳态 (6h SR93.9% 0 真中断, abs_cap 连续多轮归零, BUG-A 修复真实生效 1 次/30min, 120s 跑满类持续趋零) + 本轮无新监督者激活指令 → 继续冻结.

## 本轮结论

- 0 改动 0 restart. 连续第 17 轮 NOP 冻结指数退避 (R1928 冻结 → R1929/R1930/R1931/R1933-1958 NOP).
- 数据与 R1957 几乎完全一致: 6h 502 分类 zombie×22/ATE×12/first_byte_timeout×5 与 R1957 完全相同, 30min SR 97.5% (R1957 96.8%) 小样本偏优微升, fallback 4 (R1957 3) 微升无恶化全 FALLBACK-OK, abs_cap 30min=0/6h=0 持续归零, breaker 30min=2 全 CLOSED 不 OPEN, BUG-A 修复 1 次/30min 持续生效.
- 用户诉求 (2026-07-19 01:40) "可以报错但不能让 cc2 中断" 仍达成 (R1958 0 真中断; 4 条 FALLBACK-OK 全被 ms_gw 兜住, 0 fallback 失败).
