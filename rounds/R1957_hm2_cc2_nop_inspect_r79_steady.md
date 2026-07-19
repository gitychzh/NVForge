# R1957 (HM2 cc2) — NOP 巡检 R79, 连续第 16 轮冻结指数退避

> 模式: nv 直连 (cc4101→nv_gw), 指数退避半成品冻结 (env NVU_GLM52_EXP_BACKOFF 不在容器 env 中=关, 从未 in-vivo 激活).
> 铁律: 改前必有数据, 改后必有验证, 聚焦 40006, 不碰 40007, 写入仓库, 改.py 必须 restart.

## 数据 (本 session ~02:15Z UTC 拉取, nv_gw 已起 elapsed ~5h42min)

- **nv_gw 30min SR = 92/95 = 96.8%** (200:92 / 502:3). 小样本偏优 (R1956 97.7 / R1954 98.3 / R1953 91.7 / R1952 88.9 / R1951 89.3 / R1949 98.0, 区间稳态非退化, 本轮样本 95 中等).
- **nv_gw 6h SR = 600/639 = 93.9%** (200:600 / 502:39). 大样本稳态区间 (R1942-1956 93.0-95.2% 内, 与 R1956 94.0% 几乎一致, 微降 0.1pp 抖动).
- **30min 502=3 全 NVCF 上游侧已知类: zombie_empty_completion×3** (全 glm5_2_nv, 出口 IP 段 134.195.101.0/24 同源快回空). R1956 30min 502=2 也是 zombie×2, 抖动非恶化.
- **6h 502=39 全已知类**: zombie×22 (R1956 21, +1 微抖) + all_tiers_exhausted×12 (全 dsv4p_nv all_tiers_failed_in_mapped_tier 子类; R1956 12, 一致) + first_byte_timeout×5 (全 dsv4p_nv; R1956 5, 一致). 与 R1956 完全一致 (+1 zombie 微抖).
- **abs_cap 30min=0 / 6h=0** (DB `error_type like '%abs%'` 0 rows 双重确认; R1918 方案0 cap_origin 重置持续归零, 连续多轮 R1931→R1942→R1943→R1946→R1947→R1949→R1951→R1952→R1953→R1954→R1956→R1957).
- **fallback 3**/30min 全 FALLBACK-OK (0 真中断, 0 fallback 失败): 全 3 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (< chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类 cc4101 bug3 preempt 层). R1956 fallback 5 条全 75s SKIP, 本轮 3 条下降无恶化. **120s 跑满类本轮 0** (R1951 4→R1953 2→R1954 0→R1956 0→R1957 0, 持续趋稳). ms 救回 3.9-12.1s. `grep 502` 真实命中 = 0, `both failed`/`ms.*fail` 搜索结果为空 → 确认 0 真中断.
- **breaker cc4101 PRIMARY-BREAKER-OPEN 30min = 0; nv_gw NV-ANTH-BREAKER-FAIL 30min = 2** (2 条 zombie mid-stream soft-fail → breaker recorded state=('CLOSED', 1, 0); **breaker state 仍 CLOSED** 计数 1 未达阈值 5/300s). R1956 棒记 4, 本轮 2 下降, 仍 CLOSED 不 OPEN. breaker **OPEN 0 连续多轮**.
- **BUG-A 修复 (R1913) 在日志中真实生效确认**: 30min 内 `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **1 次** (req=8ef11b54, skip _try_tier_keys 第二轮省约 ~120s/fallback 请求). R1913 阶段1.5 补全 `_chain_failed=True` + `if _chain_failed:` 跳过 pexec 第二轮的机制持续触发 (R1952 6 / R1951 1 / R1953 5 / R1954 4 / R1956 2 / R1957 1).

## 验证

- env 无漂移 (与 R1956 完全一致): UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_GLM5_2_NV=120, NVU_STREAM_ABSOLUTE_CAP_S=150, KEY_COOLDOWN_S=25, MIN_OUTBOUND_INTERVAL_S=0, NVU_BIG_INPUT_FAIL_N=1. **NVU_GLM52_EXP_BACKOFF 不在容器 env 中确认半成品从未激活**.
- cc4101 env 无漂移: PRIMARY_HEADER_TIMEOUT=60, CC4101_STREAM_TOTAL_DEADLINE_S=480 (R1926 改), CC4101_PRIMARY_SKIP_S=30, CC4101_PRIMARY_FAIL_THRESHOLD=3.
- /health ok (nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv).
- docker ps 全 Up.
- nv_gw StartedAt = 2026-07-19T13:33:43Z (0 restart, 维 R1933, elapsed ~5h42min).
- cc4101 StartedAt = 2026-07-19T12:10:22Z (0 restart, 维 R1926, elapsed ~7h10min).

## 改动

- **0 改动 0 restart**. NOP 巡检 R79, 连续第 16 轮冻结指数退避 (R1928 冻结 → R1929/R1930/R1931/R1933-1957 NOP).

## 介入四条全不满足 → NOP 无据不改

1. 6h SR93.9% 大样本稳态区间, 30min 96.8% 小样本偏优 — 非"连续 3+ 轮跌破 80%"介入线.
2. 502 全 zombie+ATE+first_byte_timeout 已知类 (出口 IP 段同源/上游侧), 非新可配置类, abs_cap 30min=0/6h=0 (DB 双重确认).
3. breaker OPEN 30min=0 连续多轮, nv_gw BREAKER-FAIL 30min=2 全 CLOSED 不 OPEN (计数 1 未达 5/300s).
4. fallback 3/30min 全 FALLBACK-OK 被 ms 兜住 0 真中断, 低于 15/30min 介入线, 无新监督者激活指令 (R1928 冻结理由仍成立).

## 冻结理由 (连续第 16 轮仍成立)

半成品未经 in-vivo 验证 (env 开关从未激活, NVU_GLM52_EXP_BACKOFF 根本不在容器 env 中) + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测窗口. 风险/收益不对等 (当前 6h SR94.0% 0 真中断, abs_cap 连续多轮归零, BUG-A 修复真实生效 1 次/30min, 120s 跑满类持续趋零, 边际收益小). 等监督者再授权激活或数据恶化 (SR 连续 3+ 轮跌破 80%) 再动.
