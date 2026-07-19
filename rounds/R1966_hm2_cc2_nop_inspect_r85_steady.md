# R1966 (HM2 cc2): NOP 巡检 R85 — 30min SR97.1%/6h SR95.0% 0 真中断, 连续冻结第 22 轮延续

> 轮号: R1966 (cc2 自优化, HM2 only)
> 前序 cc2: R1964 (7bb2aad, 连续冻结第 21 轮 NOP R84; HEAD 树里最高 cc2 round file). 之间 R1965 是 peer HM1 agent 的 hm2_optimize_hm1 轮 (HM1 侧, 对 HM2 0 影响).
> 模式: nv 直连 (cc4101→nv_gw), 指数退避半成品冻结中 (env NVU_GLM52_EXP_BACKOFF 不在 env 中=关, 从未 in-vivo 激活)
> 本轮: NOP 巡检 R85, 连续第 22 轮冻结指数退避, 0 改动 0 restart

## 改前数据 (本 session ~19:29Z UTC 拉取, nv_gw 已起 elapsed ~5h56min 维 R1933, cc4101 elapsed ~7h19min 维 R1926)

> 注: docker daemon 容器内日志时间戳为 CST (UTC+8), DB `now()` 为 UTC. 本轮用 `now()-interval` 拉取一致, 时间维度 OK. 容器日志 03:0x CST = 19:0x UTC.

### 30min 窗口
- nv_gw 30min SR = 66/68 = **97.1%** (200:66 / 502:2), 小样本抖动区间 (R1964 96.6 / R1962 96.3 / R1961 96.0 / R1960 94.7 / R1958 97.5 / R1957 96.8, 本轮 97.1 区间内偏优微升, 与 R1958 97.5 接近)
- 30min 502=2 全 NVCF 上游侧已知类: **zombie_empty_completion×2** (全 glm5_2_nv, 出口 IP 段 134.195.101.0/24 同源快回空). 与 R1964 30min 502=2 zombie×2 完全一致.
- abs_cap 30min=0 (DB `error_type like '%abs%'` 0 rows 双重确认; R1918 方案0 cap_origin 重置持续归零连续多轮)
- fallback **7** FALLBACK-OK (0 真中断, 0 fallback 失败):
  - 全 7 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (< chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类 cc4101 bug3 preempt 层): req=0328abf7(75s, ms 3145ms) / 7455c044(75s, ms 27348ms outlier) / 048a512d(75s, ms 1945ms) / 221c7447(75s, ms 3743ms) / 88c49491(75s, ms 6805ms) / e6234423(75s, ms 8985ms) / 3769543e(75s, ms 16552ms)
  - **120s 跑满类本轮 0** (R1964 0, 本轮 0; 趋势 R1951 4→R1953 2→R1954 0→R1956 0→R1957 0→R1958 0→R1960 1→R1961 3→R1962 4→R1964 0→R1966 0, 区间内抖动回落, 远未达 >15/30min 介入线, 属 NVCF 首字节持续不来非 nv_gw 旋钮可解)
  - 7 条 fallback 全集中在 03:03-03:29 CST (19:03-19:29 UTC, 近 26min 内), 比 R1964 分散度更高但全部成功无中断, 低于 15/30min 介入线
  - 全 7 条被 cc4101 在 75s 抢断切 ms, ms 救回 1945-27348ms (7455c044 这条 ms 救回 27.3s 偏慢但成功, 3769543e 16.5s 也偏慢, 其余 2-9s 常态) → 0 条 fallback 失败 → CC 收 0 真 502
  - `grep 502` / `both failed` / `ms.*fail` / `fallback.*fail` 搜索结果为空 → 确认 0 真中断
- breaker cc4101 PRIMARY-BREAKER-OPEN 30min = **0**; nv_gw NV-ANTH-BREAKER-FAIL 30min = **0** (30min nv_gw BREAKER 日志全空, 0 触发, 全 CLOSED 连续多轮不 OPEN, 计数未达阈值 5/300s)
- BUG-A 修复 (R1913) 真实生效确认: 30min `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **2 次** (skip _try_tier_keys 第二轮省约 ~120s/fallback 请求; R1964 4 / R1962 4 / R1961 2 / R1960 1 / R1957 1 / R1956 2 / 本轮 2 持续生效)
- NV-PEEK-CAP-RESET 是方案0 reset 事件非真 502
- tier 30min: pexec_success×52 + pexec_empty_200×7 (全 NVCF 上游侧)

### 6h 窗口
- nv_gw 6h SR = 628/661 = **95.0%** (200:628 / 502:33), 大样本稳态区间 (R1942-1964 93.0-95.2% 内, 与 R1964 94.7% 一致微升 0.3pp, 偏区间高端)
- 6h 502=33 全已知类: **zombie×21** + **all_tiers_exhausted×8** + **stream_first_byte_timeout×4**
  - zombie×21 (R1964 21, 本轮 21, 完全一致; 全 glm5_2_nv 出口 IP 段同源)
  - all_tiers_exhausted×8 (R1964 9, 本轮 8, -1 微抖无恶化; 全 dsv4p_nv all_tiers_failed_in_mapped_tier 子类)
  - first_byte_timeout×4 (R1964 4, 本轮 4, 完全一致; 全 dsv4p_nv)
- abs_cap 6h=0 (DB `like '%abs%'` 0 rows 双重确认, R1918 方案0 持续归零连续多轮 R1931→R1942→R1943→R1946→R1947→R1949→R1951→R1952→R1953→R1954→R1956→R1957→R1958→R1960→R1961→R1962→R1964→R1966)

### 验证 (env 无漂移 + 容器状态)
- nv_gw /health: ok (nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv, nv_default_model=dsv4p_nv, proxy_role=passthrough, port=40006)
- docker ps: nv_gw Up 6 hours (CreatedAt 07-19 00:00 CST) / cc4101 Up 7 hours (CreatedAt 07-19 20:10 CST) / ms_gw Up 2 days / logs_db Up 3 days, 全 Up
- nv_gw StartedAt = 2026-07-19T13:33:43Z (RestartCount=0, 维 R1933, elapsed ~5h56min @ 19:29Z UTC; R1933→R1966 未再 restart)
- cc4101 StartedAt = 2026-07-19T12:10:22Z (RestartCount=0, 维 R1926, elapsed ~7h19min @ 19:29Z UTC)
- env 快照 (无漂移, 与 R1957/R1958/R1960/R1961/R1962/R1964 完全一致):
  - UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_GLM5_2_NV=120, NVU_STREAM_ABSOLUTE_CAP_S=150
  - MIN_OUTBOUND_INTERVAL_S=0, KEY_COOLDOWN_S=25, KEY_AUTHFAIL_COOLDOWN_S=60
  - NVU_BIG_INPUT_FAIL_N=1, NVU_BIG_INPUT_COOLDOWN_S=180, NVU_BIG_INPUT_THRESHOLD=250000, NVU_BIG_INPUT_MODELS=glm5_2_nv
  - NV_INTEGRATE_KEY_COOLDOWN_S=90, NV_KEY_INTEGRATE_KEYS=dsv4p_nv:5, TIER_COOLDOWN_S=25
  - NVU_GLM52_EXP_BACKOFF 不在 env 中=关 (半成品冻结, 从未 in-vivo 激活, env 里根本无此变量)

## 决策: NOP — 介入四条全不满足

**介入四条全不满足** → NOP 无据不改:
1. 6h SR 95.0% 大样本稳态区间 (R1942-1964 93.0-95.2% 内, 偏优非退化), 30min 97.1% 小样本偏优, **非**"连续 3+ 轮跌破 80%"介入线.
2. 502 全 zombie+ATE+first_byte_timeout NVCF 上游侧已知类, **非**新可配置类, abs_cap 30min=0/6h=0 (DB 双重确认).
3. breaker OPEN 30min=0 连续多轮 (nv_gw 30min BREAKER 日志全空, 全 CLOSED 计数未达 5/300s).
4. fallback 7/30min 全 FALLBACK-OK 被 ms 兜住 **0 真中断** 0 fallback 失败, 低于 15/30min 介入线, 无新监督者激活指令 (R1928 冻结理由仍成立).

**指数退避激活决策仍冻结 (连续第 22 轮)**: R1928 冻结理由 (半成品未 in-vivo 验证 + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测) 仍成立. env NVU_GLM52_EXP_BACKOFF 根本不在容器 env 中 → 半成品代码从未激活, 冻结决定物理成立. 当前链路稳态 (6h SR95.0% 0 真中断, abs_cap 连续多轮归零, BUG-A 修复真实生效 2 次/30min, 120s 跑满类持续趋零) + 本轮无新监督者激活指令 → 继续冻结. **等监督者再授权激活或数据恶化 (SR 连续 3+ 轮跌破 80%) 再动**.

## 改动
- 0 改动 0 restart (NOP 巡检, 维 R1933 nv_gw StartedAt 13:33:43Z / R1926 cc4101 StartedAt 12:10:22Z)
- 不碰 proxy/ms-gw/ (40007 热备保留)

## 下一轮该做什么
- **继续 NOP 巡检 R86**. 下一轮拉 30min 数据看 SR/fallback/breaker 抖动是否仍在已知区间. 当前 6h SR 95.0% 是区间稳态, 链路稳 — 502 全 zombie+ATE+first_byte_timeout (出口 IP 段同源/已知上游侧), fallback 全 75s SKIP-CIRCUIT 被 ms 兜住 0 真中断.
- **关注点**: 7 条 fallback 全集中在近 26min 内 (比 R1964 分散度高), 但全部成功无中断, 低于介入线. 继续看 fallback 集中度是否持续 + 120s 跑满类是否持续低位 + breaker 是否开始 OPEN (当前全 CLOSED).
- **指数退避激活决策仍冻结 (连续第 22 轮)**: env NVU_GLM52_EXP_BACKOFF 不在容器 env 中 → 半成品代码从未激活, 冻结决定物理成立. 等监督者再授权激活或数据恶化 (SR 连续 3+ 轮跌破 80%) 再动.
- **指数退避若激活需同步的 4 个坑 (R1924 核对 + 监督者 21:15 清单)**: (1) chain_budget NVU_TIER_BUDGET_GLM5_2_NV 120→420 (2) cc4101 PRIMARY_HEADER_TIMEOUT 60→450 (3) post-200 软挂换 key 未实现 (handlers.py 5 处 zombie/abs_cap/no_content_gap 分支) (4) abs_cap NVU_STREAM_ABSOLUTE_CAP_S 150→250+ 容指数退避 (或 abs_cap 触发时换 key 而非直接 502). R1926 已铺路 cc4101 STREAM_TOTAL_DEADLINE 360→480 扫清坑 (1)(2) 的 cc4101 抢断前提.
- 若连续 3+ 轮 SR 跌破 80% **且** 502 分类出现真正新可配置类 (非 zombie/empty200/timeout/SSLEOFError/abs_cap/all_tiers_exhausted/500_nv_error), 再考虑动 env.
- 若 SKIP-CIRCUIT 75s 或 120s 跑满类抬头突然飙升 (>15/30min) **且** breaker 开始 OPEN, 才考虑调 breaker 阈值或 TIER_TIMEOUT_BUDGET — 当前抬不上来属 cc4101 bug3 preempt 层 (75s) 或 NVCF 首字节持续不来 (120s), nv_gw 旋钮解不了.
- 沿用给监督者方向: abs_cap/zombie/empty200/all_tiers_exhausted 同源首字节慢/空/出口侧不可达是 NVCF 上游侧 + 出口 IP 段 (134.195.101.0/24 zombie 单点续; dsv4p_nv 出口 egress 空), 需换出口 IP 段 / 联系 NVCF 运维 / 核查 function 出口路由, 非 nv_gw 单参数可解.
- peer HM1 agent 持续在 HM1 侧写 "HM2→HM1" 轮 (前缀 hm2_optimize_hm1 不同, 只改 HM1 对 HM2 0 影响; 最新 R1965 commit b81f002). **写轮 commit 后立即 push** (R1962 cc2 commit 曾被 peer 挤成孤儿, 见 R1964 round file 警示), 别给 peer 留挤掉窗口.

## 仓库历史异常提醒 (R1964 发现, 本轮继承)
- peer 与 cc2 共享同一本地仓库 working tree. cc2 写轮 commit 后**立即 push** `git push origin main`, 否则 peer 基于旧 HEAD 推后续 commit 会把 cc2 本地 commit 挤成孤儿 (R1962 cc2 commit 3178a28 就这么丢的, round file 丢失, 仅 reflog 可读).
- 若 `git pull --ff-only` 失败 (本地有未 push commit), 别 reset, 先 stash 再 pull 再 stash pop 或 rebase 保住本地 commit.
