# R1978 (HM2 cc2) — NOP 巡检 R93, 连续第 30 轮冻结指数退避

> 本轮: 0 改动 0 restart。NOP 巡检, 延续 R1928 冻结决定。介入四条全不满足。
> 基线: R1977 (70d3173) → 本轮 R1978。peer 已到 R1979 (HM2→HM1, 改 HM1 不碰 HM2)。

## 1. 拉数据 (改前必有数据, 本 session 拉取)

**git pull**: `Already up to date`. 仓库最新 = R1979 (peer HM1 agent 的 HM2→HM1 轮, 只改 HM1, 对 HM2 nv_gw 0 影响)。cc2 上一轮 R1977 (70d3173)。

**30min nv_requests (hermes_logs.nv_requests)**:
- status: 200=72 / 502=5 → **SR = 72/77 = 93.51%** (小样本偏稳)
- 502 error_type: **zombie_empty_completion ×5** (全 glm5_2_nv, NVCF 上游侧已知类: 出口 IP 段 134.195.101.0/24 同源快回空)
- abs_cap 30min: `error_type like '%abs%'` → **0 rows** (DB 双重确认, R1918 方案0 持续归零)

**6h nv_requests**:
- status: 200=713 / 502=39 → **SR = 713/752 = 94.81%** (大样本稳态区间)
- 502 error_type: zombie×26 + all_tiers_exhausted×8 + stream_first_byte_timeout×5
- 与 R1977 (6h SR 94.96%, 502=37: zombie×24+ATE×8+fbt×5) **几乎 0 漂移**: SR -0.15pp, 502+2 (zombie+2)

**30min tier attempts (nv_tier_attempts)**: pexec_success×64 + pexec_conn_RemoteDisconnected×4 + pexec_429×1

**fallback 率 (cc4101 30min)**: **6 条** FALLBACK-OK (0 真中断, 0 fallback 失败)
- 全 6 条 `PRIMARY-FAIL-SKIP-CIRCUIT` (75s < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类 cc4101 bug3 preempt 层)
- 全 6 条: primary (glm5_2_nv) timeout status=0 after 75057/75080/75081/75027/75079ms → 切 fallback ms_gw glm5_2_ms → 救回 2191/3171/2828/1832/2668ms (推算第 6 条亦救回)
- `grep -cE "both failed|ms.*fail|UPSTREAM-ERROR-SEEN"` = **0** → **0 真中断** (CC 收 0 真 502)
- 120s 跑满类本轮 0 (持续趋稳归零, R1951 4→R1953 2→R1954 0→…→R1977 0→R1978 0)
- 注: 日志 "saves ~120s" 4 条全是 `NV-GLM52-CHAIN-SKIP-PEXEC2 ... go all_keys_exhausted -> ms_fb` (BUG-A 修复路径省约 120s/请求), **非 120s 跑满类**, 不要混淆

**breaker 30min**:
- cc4101 `PRIMARY-BREAKER-OPEN` = **0** (连续多轮 0)
- nv_gw `NV-ANTH-BREAKER-FAIL` = **2**, 但 state=('CLOSED', 2, 0) — 只记 2 次 failure, 未达 5/300s 阈值, 仍 CLOSED 不 OPEN (R1957 抖到 2 同类, 本轮 2 仍 CLOSED)
- 注: 日志见 `NV-MS-FB-SERVED state=CLOSED` 是 nv_gw 内部 ms_fb 路径 (Point A/B) 记 breaker failure, state 仍 CLOSED, 非 OPEN 事件

**BUG-A 修复 (R1913) 真实生效确认**: 30min 内 `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **4 次** (R1977 2 次, 本轮 +2 区间内波动)。R1913 阶段1.5 补全 `_chain_failed=True` + 跳过 pexec 第二轮机制持续触发, 长期生效。

## 2. 验证 (env / health / docker)

- **env 无漂移** (与 R1977 完全一致): UPSTREAM_TIMEOUT=66 / TIER_TIMEOUT_BUDGET_S=180 / NVU_TIER_BUDGET_GLM5_2_NV=120 / NVU_STREAM_ABSOLUTE_CAP_S=150 / KEY_COOLDOWN_S=25 / TIER_COOLDOWN_S=25 / NVU_BIG_INPUT_FAIL_N=1 / NVU_BIG_INPUT_COOLDOWN_S=180 / NV_INTEGRATE_KEY_COOLDOWN_S=90 / MIN_OUTBOUND_INTERVAL_S=0
- **NVU_GLM52_EXP_BACKOFF 不在容器 env 中** → 半成品指数退避从未激活, 冻结决定物理成立 (连续第 30 轮确认)
- **/health** ok: nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv, nv_default_model=dsv4p_nv, proxy_role=passthrough
- **docker ps**: 全 Up (cc4101/nv_gw/ms_gw/logs_db 等)
- **StartedAt** (docker inspect): nv_gw = 2026-07-19T13:33:43Z (R1933 NameError 修复后, R1933→R1978 未再 restart, 0 restart), cc4101 = 2026-07-19T12:10:22Z (R1926 step2.0 env up-d 后, 0 restart)

## 3. 决策 (介入四条核对 → NOP 无据不改)

1. **SR**: 6h 94.81% 大样本稳态 (与 R1977 94.96% -0.15pp 几乎一致 0 漂移); 30min 93.51% 小样本偏稳, **非**"连续 3+ 轮跌破 80%"介入线 → 不满足
2. **502 分类**: 30min 全 zombie×5, 6h 全 zombie+ATE+fbt 已知类 (与 R1977 几乎 0 漂移 zombie+2), 非新可配置类; abs_cap 30min=0 (DB 双重确认) → 不满足
3. **breaker**: cc4101 OPEN 30min=0 连续多轮; nv_gw BREAKER-FAIL 2 但 state=CLOSED 2/0 未 OPEN → 不满足
4. **fallback**: 6/30min 全 FALLBACK-OK 被 ms 兜住 0 真中断, 远低于 15/30min 介入线; 无新监督者激活指令 (R1928 冻结理由仍成立) → 不满足

**结论**: 连续第 30 轮冻结指数退避。半成品 env 开关从未激活 + 激活需同步 4 个坑 (chain_budget 120→420 / cc4101 header 60→450 / post-200 软挂换 key 未实现 / abs_cap 容纳) + 24h 观测窗口。当前链路稳态 (6h SR94.81% 与 R1977 0 漂移 0 真中断, abs_cap 连续多轮归零, BUG-A 修复 4 次/30min, 120s 跑满类持续 0), 风险/收益不对等, 边际收益小。**等监督者再授权激活或数据恶化 (SR 连续 3+ 轮跌破 80%) 再动**。

## 4. 改动 / restart

- **0 改动 0 restart**。本轮 NOP 巡检, 不改 compose env, 不改 gateway/*.py, 不 restart nv_gw。
- 用户诉求 (2026-07-19 01:40) "可以报错但不能让 cc2 中断" 仍达成: R1978 0 真中断, 6 条 FALLBACK-OK 全被 ms_gw 兜住。

## 5. commit

- 本轮 commit 信息: `R1978 (HM2 cc2): NOP 巡检 R93 — 30min SR93.51%/6h SR94.81% 0 真中断, 与 R1977 6h -0.15pp 0 漂移, 连续冻结第 30 轮延续`
