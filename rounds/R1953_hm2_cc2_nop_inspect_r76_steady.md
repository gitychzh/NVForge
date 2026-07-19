# R1953 (HM2 cc2) — NOP 巡检 R76, 连续第 13 轮冻结指数退避

> 模式: nv 直连 (cc4101→nv_gw 40006), 半成品指数退避冻结 (env NVU_GLM52_EXP_BACKOFF 未设=关, R1928 起)。
> 铁律遵循: 改前有数据/改后验证/聚焦 40006/不碰 40007/写入仓库/只改 HM2。本轮 0 改动 0 restart。

## 数据 (本 session ~17:31Z UTC 拉取)

### nv_gw 成功率
- **30min**: 200:55 / 502:5 → SR = 55/60 = **91.7%** (小样本抖动, R1952 88.9 / R1951 89.3 / R1949 98.0 / R1947 92.9, 区间稳态非退化)
- **6h**: 200:553 / 502:40 → SR = 553/593 = **93.3%** (大样本稳态区间, R1952 93.2 / R1951 93.0 / R1942-R1952 93.0-95.2% 区间内, 与 R1952 93.2% 几乎一致)

### 502 错误分类 (全 NVCF 上游侧已知类, 无新可配置类)
- **30min**: zombie_empty_completion×4 (glm5_2_nv, 出口 IP 段 134.195.101.0/24 同源快回空) + stream_first_byte_timeout×1
- **6h**: zombie×23 + all_tiers_exhausted×12 (全 dsv4p_nv, all_tiers_failed_in_mapped_tier 子类; R1952 是 12, 本轮 12 一致) + first_byte_timeout×5 (R1952 是 5, 本轮 5 一致)
- **abs_cap 30min=0 / 6h=0** (R1918 方案0 cap_origin 重置持续归零, 502 分类中无 stream_absolute_cap, 连续多轮归零)

### fallback (cc4101 30min)
- **7 条 FALLBACK-OK** (0 真中断, 0 fallback 失败): 全 7 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (< chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类 cc4101 bug3 preempt 层)。全被 cc4101 在 75s 抢断切 ms, ms 2.1-9.7s 救回 → 0 真中断。
- R1952 fallback 7 条 (5×75s SKIP + 2×120s chain 跑满), 本轮 7 条全 75s SKIP (120s 跑满类本轮 0, R1952 是 2, 下降无恶化)。
- `grep 502` 真实命中 = 0; `both failed`/`ms.*fail` 搜索为空 → 0 真中断确认。

### breaker
- cc4101 PRIMARY-BREAKER-OPEN 30min = **0**; nv_gw NV-ANTH-BREAKER-FAIL 30min = **0**; **OPEN 0 连续多轮**。

### BUG-A 修复 (R1913) 真实生效确认
- 30min 内 `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **5 次** (R1952 6 / R1951 1 / 本轮 5), skip _try_tier_keys 第二轮省约 ~120s/fallback 请求。R1913 阶段1.5 补全 `_chain_failed=True` + `if _chain_failed:` 跳过 pexec 第二轮机制持续触发, 验证 BUG-A 修复长期生效。

## 验证
- /health: ok (nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv)
- docker ps: nv_gw/cc4101/ms_gw/logs_db 全 Up
- env 无漂移 (与 R1951/R1952 快照完全一致): UPSTREAM_TIMEOUT=66 / TIER_TIMEOUT_BUDGET_S=180 / NVU_TIER_BUDGET_GLM5_2_NV=120 / NVU_STREAM_ABSOLUTE_CAP_S=150 / NVU_GLM52_EXP_BACKOFF 未设=关 / KEY_COOLDOWN_S=25 / NVU_BIG_INPUT_FAIL_N=1
- nv_gw StartedAt = **2026-07-19T13:33:43Z** (docker inspect 核实, R1933 restart NameError 修复后基线)
- cc4101 StartedAt = **2026-07-19T12:10:22Z** (R1926 step2.0 env up-d 后)
- 0 改动 0 restart, 维 R1933/ R1926 基线

## 决策: NOP 无据不改
介入四条全不满足:
1. 6h SR 93.3% 大样本稳态区间, 30min 91.7% 小样本抖动, 非"连续 3+ 轮跌破 80%"介入线
2. 502 全 zombie + ATE + first_byte_timeout 已知类, 非新可配置类, abs_cap 30min=0/6h=0
3. breaker OPEN 30min=0 连续多轮, nv_gw BREAKER-FAIL 30min=0
4. fallback 7/30min 全 FALLBACK-OK 被 ms 兜住 0 真中断, 低于 15/30min 介入线, 无新监督者激活指令

指数退避激活决策仍冻结 (连续第 13 轮): R1928 冻结理由 (半成品未 in-vivo 验证 + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测) 仍成立。当前链路稳态 (6h SR93.3% 0 真中断, abs_cap 连续多轮归零, BUG-A 修复真实生效 5 次/30min) + 本轮无新监督者激活指令 → 继续冻结。等监督者再授权激活或数据恶化 (SR 连续 3+ 轮跌破 80%) 再动。
