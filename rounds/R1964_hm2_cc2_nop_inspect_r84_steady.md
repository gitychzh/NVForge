# R1964 (HM2 cc2): NOP 巡检 R84 — 30min SR96.6%/6h SR94.7% 0 真中断, 连续冻结第 21 轮延续

> 轮号: R1964 (cc2 自优化, HM2 only)
> 前序 cc2: R1961 (bcdf8d2, 连续冻结第 19 轮 NOP R82; HEAD 树里最高 cc2 round file). 之间 R1962 cc2 round file 丢失见下.
> 模式: nv 直连 (cc4101→nv_gw), 指数退避半成品冻结中 (env NVU_GLM52_EXP_BACKOFF 不在 env 中=关, 从未 in-vivo 激活)
> 本轮: NOP 巡检 R84, 连续第 21 轮冻结指数退避, 0 改动 0 restart

## ⚠️ 仓库历史异常: R1962 cc2 commit 丢失 (本轮发现并记录)

- `git pull --ff-only origin main` 后 origin/main = aaf064c (peer R1963 hm2_optimize_hm1). HEAD 树里 cc2 round file 最高止于 R1961 (R1961_hm2_cc2_nop_inspect_r82_steady.md).
- reflog 证据: `3178a28 R1962 (HM2 cc2)` (上一个 cc2 session commit, 父=9915440) **不在 origin/main 历史里** — `git merge-base --is-ancestor 3178a28 origin/main` 返回 NO.
- 原因推断: 上一个 cc2 session 跑完 R1962 commit 3178a28 (基于 9915440) 后, peer 在同一本地仓库 `~/hm_ps/hermes_improve_self` 上基于 9915440 (而非 3178a28) 推了后续 commit (8203e22→9915440→aaf064c 序列), 把 origin/main 推到 aaf064c; cc2 下次 session `git pull --ff-only` 时本地 reset 到 origin/main (reflog HEAD@{2} `reset: moving to origin/main`), 3178a28 成孤儿 commit 被丢.
- **实质损失**: R1962 是 NOP 巡检 0 改动 0 restart, round file 丢失 = 记录断 (无源码/配置/env 损失). 上一个 session 的 R1962 数据 (30min SR96.3%/6h SR94.6%) 已从 reflog `git show 3178a28:rounds/R1962_hm2_cc2_nop_inspect_r83_steady.md` 恢复阅读, 不重发 (避免与 R1962 peer commit 撞号, 且本轮 R1964 已记录该事实).
- 本轮 R1964 round file 直接基于 R1961 前序 + 本 session 实测数据写, 不依赖丢失的 R1962 记录.
- **给下一个 session**: peer 与 cc2 共享同一本地仓库 working tree, 写轮 commit 后**立即 push** (`git push origin main`), 别给 peer 留挤掉窗口; 若 `git pull --ff-only` 失败 (本地有未 push commit) 别 reset, 先 stash 再 pull 再 stash pop 或用 rebase 保住本地 commit.

## 改前数据 (本 session ~19:16Z UTC 拉取, nv_gw 已起 elapsed ~29.7h, cc4101 elapsed ~31.1h)

> 注: docker daemon 容器内日志时间戳为 CST (UTC+8), DB `now()` 为 UTC. 本轮用 `now()-interval` 拉取一致, 时间维度 OK. 容器日志 02:5x CST = 18:5x UTC.

### 30min 窗口
- nv_gw 30min SR = 57/59 = **96.6%** (200:57 / 502:2), 小样本抖动区间 (R1962 96.3 / R1961 96.0 / R1960 94.7 / R1958 97.5 / R1957 96.8, 本轮 96.6 区间内非退化, 与 R1962 96.3 几乎一致微升 0.3pp)
- 30min 502=2 全 NVCF 上游侧已知类: **zombie_empty_completion×2** (全 glm5_2_nv, 出口 IP 段 134.195.101.0/24 同源快回空)
- abs_cap 30min=0 (DB `error_type like '%abs%'` 0 rows 双重确认; R1918 方案0 cap_origin 重置持续归零连续多轮)
- fallback **7** FALLBACK-OK (0 真中断, 0 fallback 失败):
  - 全 7 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (< chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类 cc4101 bug3 preempt 层): req=938ae1dd(75s, ms 4621ms) / fd0a641f(75s, ms 5942ms) / 0328abf7(75s, ms 3145ms) / 7455c044(75s, ms 27348ms outlier) / 048a512d(75s, ms 1945ms) + 2 条同窗
  - **120s 跑满类本轮 0** (R1962 抖到 4, 本轮回 0; 趋势 R1951 4→R1953 2→R1954 0→R1956 0→R1957 0→R1958 0→R1960 1→R1961 3→R1962 4→R1964 0, 区间内抖动回落, 远未达 >15/30min 介入线, 属 NVCF 首字节持续不来非 nv_gw 旋钮可解)
  - 全 7 条被 cc4101 在 75s 抢断切 ms, ms 救回 1945-27348ms (7455c044 这条 ms 救回 27.3s 偏慢但成功, 其余 2-6s 常态) → 0 条 fallback 失败 → CC 收 0 真 502
  - `grep 502` / `both failed` / `ms.*fail` 搜索结果为空 → 确认 0 真中断
- breaker cc4101 PRIMARY-BREAKER-OPEN 30min = **0**; nv_gw NV-ANTH-BREAKER-FAIL 30min = **0** (4 条 NV-MS-FB-SERVED 全 `state=CLOSED`, 计数未达阈值 5/300s, breaker state 仍 CLOSED 连续多轮不 OPEN)
- BUG-A 修复 (R1913) 真实生效确认: 30min `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **4 次** (skip _try_tier_keys 第二轮省约 ~120s/fallback 请求; R1962 4 / R1961 2 / R1960 1 / R1957 1 / R1956 2 / 本轮 4 持续生效)
- NV-PEEK-CAP-RESET 是方案0 reset 事件非真 502

### 6h 窗口
- nv_gw 6h SR = 608/642 = **94.7%** (200:608 / 502:34), 大样本稳态区间 (R1942-1962 93.0-95.2% 内, 与 R1962 94.6% 几乎一致微升 0.1pp)
- 6h 502=34 全已知类: **zombie×21** + **all_tiers_exhausted×9** + **stream_first_byte_timeout×4**
  - zombie×21 (R1962 21, 本轮 21, 完全一致; 全 glm5_2_nv 出口 IP 段同源)
  - all_tiers_exhausted×9 (R1962 9, 本轮 9, 完全一致; 全 dsv4p_nv all_tiers_failed_in_mapped_tier 子类)
  - first_byte_timeout×4 (R1962 4, 本轮 4, 完全一致; 全 dsv4p_nv)
- abs_cap 6h=0 (DB `like '%abs%'` 0 rows 双重确认, R1918 方案0 持续归零连续多轮 R1931→R1942→R1943→R1946→R1947→R1949→R1951→R1952→R1953→R1954→R1956→R1957→R1958→R1960→R1961→R1962→R1964)

### 验证 (env 无漂移 + 容器状态)
- nv_gw /health: ok (nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv, nv_default_model=dsv4p_nv)
- docker ps: nv_gw Up 6 hours / cc4101 Up 7 hours / ms_gw Up 2 days / logs_db Up 3 days, 全 Up
- nv_gw StartedAt = 2026-07-19T13:33:43Z (RestartCount=0, 维 R1933, elapsed ~29.7h @ 19:16Z UTC; R1933→R1964 未再 restart)
- cc4101 StartedAt = 2026-07-19T12:10:22Z (RestartCount=0, 维 R1926, elapsed ~31.1h @ 19:16Z UTC)
- env 快照 (无漂移, 与 R1957/R1958/R1960/R1961/R1962 完全一致):
  - UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_GLM5_2_NV=120, NVU_STREAM_ABSOLUTE_CAP_S=150
  - MIN_OUTBOUND_INTERVAL_S=0, KEY_COOLDOWN_S=25, KEY_AUTHFAIL_COOLDOWN_S=60
  - NVU_BIG_INPUT_FAIL_N=1, NVU_BIG_INPUT_COOLDOWN_S=180, NV_INTEGRATE_KEY_COOLDOWN_S=90, TIER_COOLDOWN_S=25
  - **NVU_GLM52_EXP_BACKOFF 不在容器 env 中** (env|grep -c NVU_GLM52_EXP_BACKOFF = 0, 半成品冻结物理成立, 从未 in-vivo 激活)
- cc4101 env: PRIMARY_HEADER_TIMEOUT=60, CC4101_STREAM_TOTAL_DEADLINE_S=480 (R1926 改), CC4101_PRIMARY_SKIP_S=30, CC4101_PRIMARY_FAIL_THRESHOLD=3

## 决策: NOP (无据不改)

介入四条全不满足:
1. 6h SR 94.7% 大样本稳态区间 (R1942-1962 93.0-95.2% 内), 30min 96.6% 小样本偏优, 非"连续 3+ 轮跌破 80%"介入线.
2. 502 全 zombie+all_tiers_exhausted+first_byte_timeout 已知类 (出口 IP 段同源/已知上游侧), abs_cap 30min=0/6h=0 (DB 双重确认), 无新可配置类.
3. breaker OPEN 30min=0 连续多轮, nv_gw BREAKER-FAIL 30min=0, breaker state 仍 CLOSED (4 条 NV-MS-FB-SERVED 全 CLOSED).
4. fallback 7/30min 全 FALLBACK-OK 被 ms 兜住 0 真中断 0 fallback 失败, 低于 15/30min 介入线, 无新监督者激活指令 (R1928 冻结理由仍成立).

R1928 冻结理由 (连续第 21 轮仍成立): 半成品未经 in-vivo 验证 (env 开关从未激活, NVU_GLM52_EXP_BACKOFF 根本不在容器 env 中) + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测窗口. 风险/收益不对等 (当前 6h SR94.7% 0 真中断, abs_cap 连续多轮归零, BUG-A 修复真实生效 4 次/30min, 120s 跑满类本轮回 0, 边际收益小).

## 本轮改动

- **0 改动 0 restart**. 仅拉数据 + 写 round file + 覆写 STATE.md.
- 未碰 proxy/ms-gw/ (40007 热备保留).
- 未碰 HM1 (peer 主机).

## 下轮建议

- 继续 NOP 巡检 R85. 拉下个 30min 窗口看 SR/fallback/breaker 抖动是否仍在已知区间.
- 关注点: 120s 跑满类 (R1962 抖到 4, 本轮回 0) 是否持续低位 + breaker 是否开始 OPEN (当前仍 CLOSED).
- 指数退避激活决策仍冻结 (连续第 21 轮). 等监督者再授权激活或数据恶化 (SR 连续 3+ 轮跌破 80%) 再动.
- **本轮新发现给下轮**: peer 与 cc2 共享本地仓库 working tree, commit 后立即 push 防挤掉; `git pull --ff-only` 失败别 reset, 先 stash 再 pull.
