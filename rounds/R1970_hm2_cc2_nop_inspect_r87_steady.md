# R1970 (HM2 cc2) — NOP 巡检 R87, 连续第 24 轮冻结指数退避

> 改前必有数据, 改后必有验证。本轮 0 改动 0 restart, 巡检确认链路稳态。
> 写轮前 peer HM1 agent 已占 R1968/R1969 (hm2_optimize_hm1 前缀), cc2 从 R1970 起避开撞号。

## 数据 (本 session 拉取, nv_gw 已起 elapsed ~6h+, 维 R1933 restart)

### nv_gw 成功率
- **30min SR = 56/57 = 98.2%** (200:56 / 502:1, 小样本偏优; R1967 98.2 / R1966 97.1 / R1964 96.6 / R1961 96.0 / R1960 94.7, 区间稳态非退化, 本轮与 R1967 持平)。
- **6h SR = 638/672 = 94.9%** (200:638 / 502:34, 大样本稳态区间; R1967 94.9 / R1966 95.0 / R1964 94.7 / R1961 94.3 / R1960 94.0, 与 R1967 完全一致 0 抖动)。

### 502 分类 (全 NVCF 上游侧已知类)
- 30min 502=1 全 **zombie_empty_completion** (glm5_2_nv 出口 IP 段 134.195.101.0/24 同源快回空)。
- 6h 502=34 全已知类: **zombie×22** (R1967 22, 一致) + **all_tiers_exhausted×8** (dsv4p_nv all_tiers_failed_in_mapped_tier 子类; R1967 8, 一致) + **stream_first_byte_timeout×4** (全 dsv4p_nv; R1967 4, 一致)。与 R1967 完全一致, 0 漂移。
- **abs_cap 30min=0 / 6h=0** (DB `error_type like '%abs%'` 0 rows 双重确认; R1918 方案0 cap_origin 重置持续归零, 连续多轮 R1931→R1942→R1946→R1949→R1951→R1953→R1954→R1956→R1957→R1960→R1961→R1964→R1966→R1967→R1970)。
- nv_tier 30min: pexec_success×44 + pexec_empty_200×5 (pexec_empty_200 是 zombie 上游侧表现, 非新可配置类)。

### fallback (负向核心指标)
- **fallback 7**/30min 全 FALLBACK-OK, **0 真中断, 0 fallback 失败**。
- 全 7 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (< chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类 cc4101 bug3 preempt 层)。ms 救回 1.8-9.7s (req=10847826 2.3s / 98dbfa48 7.3s / 9aba55bc 9.7s / e002e9e6 1.8s / 820143fc 1.8s / be2e9492 ms_fb / 5671ce03 ms_fb + 其余)。
- **120s 跑满类 30min=0** (R1951 4 → R1953 2 → R1954 0 → R1956 0 → R1957 0 → ... → R1967 0 → R1970 0, 持续趋稳归零, R1951 担心点持续反证)。
- grep 502 命中=0, `both failed`/`ms.*fail`/`UPSTREAM-ERROR-SEEN` 搜索结果为空 → 确认 0 真中断。
- 注: 日志见 4 条 `NV-MS-FB-SERVED ms_gw served glm5_2_nv fallback (state=CLOSED)` — 这是 nv_gw 内部 ms_fb 路径 (Point A/B) 记 breaker failure, state 仍 CLOSED (计数未达 5/300s), 非 NV-ANTH-BREAKER-FAIL 事件, 与 breaker OPEN 无关。

### breaker
- cc4101 PRIMARY-BREAKER-OPEN 30min = **0**。
- nv_gw NV-ANTH-BREAKER-FAIL 30min = **0** (R1957 抖到 2, R1967 0, 本轮 0, 连续多轮 CLOSED 不 OPEN)。
- breaker OPEN 30min=0 连续多轮。

### BUG-A 修复 (R1913) 真实生效确认
- 30min 内 `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **4 次**, skip _try_tier_keys 第二轮省约 ~120s/fallback 请求。R1913 阶段1.5 补全 `_chain_failed=True` + `if _chain_failed:` 跳过 pexec 第二轮的机制持续触发 (R1951 1 / R1952 6 / R1953 5 / R1954 4 / R1956 2 / R1957 1 / R1967 2 / R1970 4)。

## 验证
- env 无漂移 (UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_GLM5_2_NV=120, NVU_STREAM_ABSOLUTE_CAP_S=150, **NVU_GLM52_EXP_BACKOFF 不在 env 中**确认半成品从未激活, MIN_OUTBOUND_INTERVAL_S=0, KEY_COOLDOWN_S=25, KEY_AUTHFAIL_COOLDOWN_S=60, NVU_BIG_INPUT_FAIL_N=1, NVU_BIG_INPUT_COOLDOWN_S=180, NV_INTEGRATE_KEY_COOLDOWN_S=90, TIER_COOLDOWN_S=25)。
- /health: ok (nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv, nv_default_model=dsv4p_nv)。
- docker ps: nv_gw/cc4101/ms_gw/logs_db 全 Up。
- nv_gw StartedAt = 2026-07-19T13:33:43Z (R1933 restart NameError 修复后, R1933→R1970 未再 restart, 0 restart 维持; elapsed ~30h+ @ 本 session 拉取)。
- cc4101 StartedAt = 2026-07-19T12:10:22Z (R1926 step2.0 env up-d 后; elapsed ~31h+ @ 本 session 拉取)。

## 介入四条全不满足 → NOP 无据不改
1. **6h SR 94.9% 大样本稳态区间, 30min 98.2% 小样本偏优** — 非"连续 3+ 轮跌破 80%"介入线。
2. **502 全 zombie+ATE+first_byte_timeout 已知类**, 非新可配置类; abs_cap 30min=0/6h=0 (DB 双重确认)。
3. **breaker OPEN 30min=0 连续多轮**, nv_gw BREAKER-FAIL 30min=0 全 CLOSED 不 OPEN。
4. **fallback 7/30min 全 FALLBACK-OK 被 ms 兜住 0 真中断**, 低于 15/30min 介入线, 无新监督者激活指令 (R1928 冻结理由仍成立)。

## 结论
连续第 24 轮冻结指数退避 (R1928 冻结 → R1929/R1930/R1931/R1933-1966/R1967/R1970 NOP)。链路稳态: 6h SR 94.9% 0 真中断, abs_cap 连续多轮归零, BUG-A 修复真实生效 4 次/30min, 120s 跑满类持续趋零。半成品代码 (upstream.py:1027-1037 + config.py:522-527) env 开关 NVU_GLM52_EXP_BACKOFF 从未激活, 冻结决定物理成立。本轮 NOP 0 改动 0 restart。

## 用户诉求达成
"可以报错但不能让 cc2 中断" (2026-07-19 01:40) — R1970 0 真中断 (7 条 FALLBACK-OK 全被 ms_gw 兜住, 0 fallback 失败, grep 502=0)。

---
*Co-Authored-By: Claude <noreply@anthropic.com>*
