# R1961 (HM2 cc2): NOP 巡检 R82 — 30min SR96.0%/6h SR94.3% 0 真中断, 连续冻结第 19 轮延续

> 轮号: R1961 (cc2 自优化, HM2 only)
> 前序: R1960 (9ea7e77, cc2 连续冻结第 18 轮 NOP R81; peer 03aa09c 占 R1960 hm2_optimize_hm1 前缀不冲突)
> 模式: nv 直连 (cc4101→nv_gw), 指数退避半成品冻结中 (env NVU_GLM52_EXP_BACKOFF 不在 env 中=关, 从未 in-vivo 激活)
> 本轮: NOP 巡检 R82, 连续第 19 轮冻结指数退避, 0 改动 0 restart

## 改前数据 (本 session 18:57Z UTC 拉取, nv_gw 已起 elapsed ~5.4h, cc4101 elapsed ~6.8h)

> 注: 本轮核实棒上 R1960 记的 "elapsed ~29h/30h @ 18:37Z" 系笔误 (误用容器 CreatedAt/时区乱).
> 实际 docker inspect: nv_gw StartedAt=2026-07-19T13:33:43Z RestartCount=0, @18:57Z UTC elapsed 实算 ~5.4h.
> StartedAt 仍维 R1933 (13:33:43Z), 0 restart 物理成立, 仅棒上几轮 elapsed 数字记错, 不影响冻结判定.

### 30min 窗口
- nv_gw 30min SR = 48/50 = **96.0%** (200:48 / 502:2), 小样本抖动区间 (R1960 94.7 / R1958 97.5 / R1957 96.8 / R1956 97.7, 本轮 96.0 区间内非退化)
- 30min 502=2 全 NVCF 上游侧已知类: **zombie_empty_completion×1** (全 glm5_2_nv, 出口 IP 段 134.195.101.0/24 同源快回空) + **stream_first_byte_timeout×1**
- abs_cap 30min=0 (DB `error_type like '%abs%'` 0 rows 双重确认; R1918 方案0 cap_origin 重置持续归零连续多轮)
- fallback **7** FALLBACK-OK (0 真中断, 0 fallback 失败):
  - 4×75s `PRIMARY-FAIL-SKIP-CIRCUIT` (< chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类 cc4101 bug3 preempt 层)
  - **3×120s** chain budget 跑满 (req=7ea872ed 120099ms / f60f0c39 120106ms / c2cf74d6 120068ms / 468bc224 120065ms — nv_gw chain 跑满 120s 触发 cc4101 PRIMARY-FAIL → ms_fb)
    - 注: 120s 跑满类 R1960=1 / R1958=0 / R1957=0, 本轮抬到 3 (+2), **120s 跑满类趋势**: R1951 4 → R1953 2 → R1954 0 → R1956 0 → R1957 0 → R1958 0 → R1960 1 → R1961 3, 区间内抖动回升但仍远未达 >15/30min 介入线, 属 NVCF 首字节持续不来 (120s chain budget 跑满) 非 nv_gw 旋钮可解
  - 全 7 条被 cc4101 切 ms, ms 救回 2.1-15.4s (ms 救回时间: 2156ms / 4623ms / 5329ms / 6392ms / 14960ms / 15439ms / 2074ms) → 0 条 fallback 失败 → CC 收 0 真 502
  - `grep 502` / `both failed` / `ms.*fail` 搜索结果为空 → 确认 0 真中断
- breaker cc4101 PRIMARY-BREAKER-OPEN 30min = **0**; nv_gw NV-ANTH-BREAKER-FAIL 30min = **1** (1 条 zombie mid-stream soft-fail → breaker recorded state=('CLOSED', 1, 0); **breaker state 仍 CLOSED** 计数 1 未达阈值 5/300s)
  - R1960 计数 2 / 本轮计数 1, 降 1 仍 CLOSED 不 OPEN, 符合已知 pattern
- BUG-A 修复 (R1913) 真实生效确认: 30min `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **2 次** (skip _try_tier_keys 第二轮省约 ~120s/fallback 请求; R1960 1 / R1958 ? / R1957 1 / R1956 2 / 本轮 2 持续生效)
- NV-PEEK-CAP-RESET 是方案0 reset 事件非真 502

### 6h 窗口
- nv_gw 6h SR = 583/618 = **94.3%** (200:583 / 502:35), 大样本稳态区间 (R1942-1960 93.0-95.2% 内, 与 R1960 94.0% 一致微升 0.3pp)
- 6h 502=35 全已知类: **zombie×22** + **all_tiers_exhausted×9** + **stream_first_byte_timeout×4**
  - zombie×22 (R1960 22, 本轮 22, 完全一致)
  - all_tiers_exhausted×9 (R1960 10, 本轮 9, -1 微降无恶化; 全 dsv4p_nv all_tiers_failed_in_mapped_tier 子类)
  - first_byte_timeout×4 (R1960 5, 本轮 4, -1 微降无恶化; 全 dsv4p_nv)
- abs_cap 6h=0 (DB `like '%abs%'` 0 rows 双重确认, R1918 方案0 持续归零连续多轮 R1931→R1942→R1943→R1946→R1947→R1949→R1951→R1952→R1953→R1954→R1956→R1957→R1958→R1960→R1961)

### 验证 (env 无漂移 + 容器状态)
- nv_gw /health: ok (nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv, nv_default_model=dsv4p_nv)
- docker ps: nv_gw Up 5 hours / cc4101 Up 7 hours / ms_gw Up 2 days / logs_db Up 3 days, 全 Up
- nv_gw StartedAt = 2026-07-19T13:33:43Z (RestartCount=0, 维 R1933, elapsed ~5.4h @ 18:57Z UTC)
- cc4101 StartedAt = 2026-07-19T12:10:22Z (RestartCount=0, 维 R1926, elapsed ~6.8h @ 18:57Z UTC)
- env 快照 (无漂移, 与 R1957/R1958/R1960 完全一致):
  - UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_GLM5_2_NV=120, NVU_STREAM_ABSOLUTE_CAP_S=150
  - NVU_GLM52_EXP_BACKOFF **不在 env 中=关** (半成品冻结, 从未 in-vivo 激活, env 里根本无此变量)
  - MIN_OUTBOUND_INTERVAL_S=0, KEY_COOLDOWN_S=25, KEY_AUTHFAIL_COOLDOWN_S=60, NVU_BIG_INPUT_FAIL_N=1, NVU_BIG_INPUT_COOLDOWN_S=180, NV_INTEGRATE_KEY_COOLDOWN_S=90, TIER_COOLDOWN_S=25
- cc4101 env: PRIMARY_HEADER_TIMEOUT=60, CC4101_STREAM_TOTAL_DEADLINE_S=480 (R1926 改), CC4101_PRIMARY_SKIP_S=30, CC4101_PRIMARY_FAIL_THRESHOLD=3

## 决策: NOP 无据不改 (连续第 19 轮冻结)

**介入四条全不满足** → NOP 无据不改:
1. 6h SR94.3% 大样本稳态区间 (R1942-1960 93.0-95.2% 内), 30min 96.0% 小样本抖动, 非"连续 3+ 轮跌破 80%"介入线
2. 502 全 zombie+ATE+first_byte_timeout 已知类, 非新可配置类, abs_cap 30min=0/6h=0 (DB 双重确认)
3. breaker OPEN 30min=0 连续多轮, nv_gw BREAKER-FAIL 30min=1 全 CLOSED 不 OPEN (计数 1 未达 5/300s)
4. fallback 7/30min 全 FALLBACK-OK 被 ms 兜住 0 真中断, 低于 15/30min 介入线, 无新监督者激活指令 (R1928 冻结理由仍成立)

**指数退避激活决策仍冻结 (连续第 19 轮)**: R1928 冻结理由 (半成品未 in-vivo 验证 + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测) 仍成立. env NVU_GLM52_EXP_BACKOFF 根本不在容器 env 中 → 半成品代码从未激活, 冻结决定物理成立. 当前链路稳态 (6h SR94.3% 0 真中断, abs_cap 连续多轮归零, BUG-A 修复真实生效 2 次/30min) + 本轮无新监督者激活指令 → 继续冻结.

## 本轮结论

- 0 改动 0 restart. 连续第 19 轮 NOP 冻结指数退避 (R1928 冻结 → R1929/R1930/R1931/R1933-1960 NOP).
- 数据与 R1960 几乎一致: 6h SR 94.3% (R1960 94.0%) 微升 0.3pp; 6h 502 分类 zombie×22 一致 / ATE×9 (R1960 10, -1 微降) / first_byte_timeout×4 (R1960 5, -1 微降); 30min SR 96.0% (R1960 94.7%) 小样本抖动非退化; fallback 7 (R1960 5) 微升 +2 全 FALLBACK-OK; abs_cap 30min=0/6h=0 持续归零; breaker 30min=1 全 CLOSED 不 OPEN (计数降到 1); BUG-A 修复 2 次/30min 持续生效.
- **关注点**: 120s 跑满类本轮抬到 3 (R1960 1, +2), 但 6h 502 总数 (35 vs 37) 反而下降, 非 NVCF 整体恶化, 属窗口内首字节慢抖动; 全被 ms 兜住 0 真中断, 未达介入线. nv_gw 旋钮 (chain budget) 解不了首字节不来, 需 NVCF 上游侧/出口 IP 段介入.
- 用户诉求 (2026-07-19 01:40) "可以报错但不能让 cc2 中断" 仍达成 (R1961 0 真中断; 7 条 FALLBACK-OK 全被 ms_gw 兜住, 0 fallback 失败).
