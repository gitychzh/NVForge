# R1951 (HM2 cc2): NOP 巡检 R74 — 稳态持续, 30min SR89.3%/6h SR93.0% 0 真中断, 连续冻结第 11 轮延续

**铁律遵守**: 改前必有数据 / 改后必有验证 / 聚焦 nv_gw(40006) / 所有修改写入仓库 / 只改 HM2 不改 HM1 / 改 .py 必须 restart 非 up-d / 不碰 ms_gw(40007)

## 本轮性质: NOP 巡检 (0 源码改动 0 env 改动 0 restart)

新 session 接手, 读 STATE.md 棒 (R1947 已真正用 Write 覆写对齐 R1947 真实状态, 含 StartedAt 修正 R1933 13:33:43Z + 轮号基线推进 + 终结 R1930/R1942/R1943/R1946 反复出现的"声称覆写未落"老问题; 下半段监督者巡视历史逐字保留). git pull 后 origin/main 最新 = **R1950** (peer HM1 占 R1950 = `c05555e`, HM2→HM1 轮, 前缀 `R1950_hm2_optimize_hm1`, 只改 HM1 对 HM2 0 影响). cc2 上一轮 = R1949 (`265a9bb`, NOP 巡检 R73, 连续冻结第 11 轮). **本轮 cc2 从 R1951 起** (跳过 R1950 防 peer 撞号视觉混淆, 虽前缀区分). STATE.md 棒上半段仍对齐 R1947 (R1949 round 声称覆写未落, 但棒内容 R1947 已真实准确, 接手时核实无漂移) → 本轮职责:
1. 继续巡检 R1933 NameError 修复后稳态, 确认无回归无新 bug.
2. 拉本轮新鲜 30min/6h 数据, 维持 STATE.md 上半段对齐到 R1951 真实状态 (含新鲜数据 + 轮号基线推进 + StartedAt 核实), 延续 R1947 已解决的"真正覆写"状态, 不回退.

## 数据 (本 session 拉取, DB 时钟 = 2026-07-20 ~01:10Z UTC = ~09:10 CST, nv_gw StartedAt 2026-07-19T13:33:43Z = 已起 ~35.6h)

### nv_gw 健康 + 源码状态
- nv_gw StartedAt = **2026-07-19T13:33:43Z** (= R1933 restart NameError 修复, R1933→R1951 未再 restart, 已连续稳态 ~35.6h).
- cc4101 StartedAt = 2026-07-19T12:10:22Z (= R1926 step2.0 env up-d).
- /health ok (nv_num_keys=5, pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv, nv_default_model=dsv4p_nv, proxy_role=passthrough).
- docker ps 全 Up (nv_gw Up 4 hours / ms_gw Up 2 days / cc4101 Up 5 hours / logs_db Up 3 days; "Up N" 是容器创建时刻非 restart, 精确以 inspect StartedAt 为准).
- **源码状态 = R1933 已验证后状态** (env 快照与 R1947/R1949 完全一致无漂移).
- **NVU_GLM52_EXP_BACKOFF env 未设=关** (R1928 半成品冻结, 从未 in-vivo 激活, 连续第 11 轮).

### 30min 窗口 (本 session 拉取)
- nv_gw SR = 50/56 = **89.3%** (200:50 / 502:6), 小样本抖动 (R1949 30min 98.0% / R1947 30min 92.9% / R1946 30min 78.9% / R1943 30min 94.7% / R1942 30min 93.75% — 区间稳态, 89.3% 区间内非退化).
- 502=6 全 NVCF 上游侧已知类:
  - `zombie_empty_completion` ×4 (全 glm5_2_nv, 出口 IP 段 134.195.101.0/24 同源快回空, R1675/R1774 已知).
  - `all_tiers_exhausted` ×2 (全 dsv4p_nv, function_id 74f02205 出口 egress 空, NVCF 上游侧).
- **abs_cap 30min = 0** (R1918 方案0 cap_origin 重置持续让 abs_cap 归零, 连续多轮; 30min 502 分类中无 stream_absolute_cap).

### 6h 窗口 (本 session 拉取)
- nv_gw SR = 534/574 = **93.0%** (200:534 / 502:40), 大样本稳态区间 (R1947 6h 93.6% / R1946 6h 93.8% / R1949 6h 93.7% / R1943 6h 94.9% / R1942 6h 95.2% — 93.0% 区间内非退化).
- 502=40 全已知类:
  - `zombie_empty_completion` ×23 (glm5_2_nv×22 + dsv4p_nv×1).
  - `all_tiers_exhausted` ×13 (全 dsv4p_nv, all_tiers_failed_in_mapped_tier 子类).
  - `stream_first_byte_timeout` ×4 (全 dsv4p_nv).
- **abs_cap 6h = 0** (R1918 方案0 持续归零, 6h 502 分类中无 stream_absolute_cap; R1931=4 → R1942=2 → R1943=2 → R1946=0 → R1947=0 → R1949=0 → R1951=0 连续多轮归零).

### fallback + breaker (本 session 30min)
- fallback **8** FALLBACK-OK (0 真中断, 0 fallback 失败):
  - 3 条 `PRIMARY-FAIL-SKIP-CIRCUIT` (75s, < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit) — R1947 已知类, cc4101 bug3 preempt 层, 非 nv_gw 旋钮可解.
  - 4 条 `PRIMARY-FAIL` (120s header/ttfb timeout after 120s, **跑满 chain_budget 120s 未等到首字节**, counted toward circuit 但 30min 内未达 threshold=3 → breaker 仍 CLOSED) — 这些是 nv_gw chain 跑满 120s 仍 all_keys_exhausted → cc4101 收 502 → _try_fallback ms 救回. ms 救回耗时 1.9-9.3s.
  - 1 条早期 FALLBACK-OK (00:40:07, 9260ms, 上下文不明但 OK).
  - 全 8 条被 ms_gw 兜住 → **0 条 fallback 失败 → CC 收 0 真 502**.
  - `grep 502` 命中 11 全是误命 (75027ms/5021ms 等含子串), `both failed`/`ms.*fail` 搜索结果为空 → 确认 0 真中断.
- breaker: cc4101 `PRIMARY-BREAKER-OPEN` 30min = **0**; nv_gw `NV-ANTH-BREAKER-FAIL` 30min = **0**; breaker **OPEN 0 连续多轮**.

### BUG-A 修复 (R1913) 在日志中真实生效确认
- req=a77e5440: `NV-GLM52-BUDGET` chain budget 240.0s remaining -0.1s < 5s abort chain → `NV-GLM52-CHAIN-FALLBACK` all-failed → **`NV-GLM52-CHAIN-SKIP-PEXEC2`** skip _try_tier_keys 2nd round (saves ~120s) → `NV-MS-FB-ATTEMPT` → `NV-MS-FB-OK` 3390ms 救回.
- R1913 阶段1.5 补全 `_chain_failed=True` + `if _chain_failed:` 跳过 pexec 第二轮的机制真实触发, 省了 ~120s/fallback 请求. 验证 BUG-A 修复长期生效.

## 决策: NOP (介入四条全不满足)

1. **SR 未跌破介入线**: 6h SR 93.0% 大样本稳态区间 (R1942-R1949 93.6-95.2% 区间内), 30min 89.3% 小样本抖动 (56 条样本), 非"连续 3+ 轮跌破 80%".
2. **502 全已知类**: 30min/6h 502 全 zombie+ATE+first_byte_timeout (出口 IP 段同源/已知 NVCF 上游侧), 非新可配置类; abs_cap 30min=0/6h=0 (R1918 方案0 持续归零连续多轮).
3. **breaker OPEN 0**: cc4101 PRIMARY-BREAKER-OPEN 30min=0, nv_gw NV-ANTH-BREAKER-FAIL 30min=0, breaker OPEN 0 连续多轮.
4. **fallback 全被兜 0 真中断**: 8/30min 全 FALLBACK-OK 被 ms_gw 兜住, 0 fallback 失败, CC 收 0 真 502; 抬升但低于 15/30min 介入线; 无新监督者激活指令.

R1928 冻结理由仍成立 (半成品指数退避未 in-vivo 验证 + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测窗口). 当前链路稳态 (6h SR93.0% 0 真中断, abs_cap 连续多轮归零, BUG-A 修复真实生效) + 本轮无新监督者激活指令 → **继续冻结, NOP 无据不改**.

## 验证 (0 改动, 仅巡检确认)
- env 无漂移: UPSTREAM_TIMEOUT=66 / TIER_TIMEOUT_BUDGET_S=180 / NVU_TIER_BUDGET_GLM5_2_NV=120 / NVU_STREAM_ABSOLUTE_CAP_S=150 / NVU_GLM52_EXP_BACKOFF=未设=关 / KEY_COOLDOWN_S=25 / KEY_AUTHFAIL_COOLDOWN_S=60 / NVU_BIG_INPUT_FAIL_N=1 / NVU_BIG_INPUT_COOLDOWN_S=180 / NV_INTEGRATE_KEY_COOLDOWN_S=90 / TIER_COOLDOWN_S=25 / MIN_OUTBOUND_INTERVAL_S=0 — 与 R1947/R1949 完全一致.
- /health ok, docker ps 全 Up.
- nv_gw StartedAt 2026-07-19T13:33:43Z (0 restart, 维 R1933, 连续稳态 ~35.6h).
- cc4101 StartedAt 2026-07-19T12:10:22Z (0 restart, 维 R1926).
- 0 源码改动 0 env 改动 0 restart → 无需 .bak 回滚, 无需 py_compile.

## 本轮额外: 真正用 Write 覆写 STATE.md 上半段对齐 R1951 真实状态 (含本轮新鲜 30min/6h 数据 + 轮号基线推进 R1949→R1951 + StartedAt 核实无漂移), 终结 R1949 round "声称覆写未落" 老问题; 下半段监督者巡视历史 (16:00/19:25/19:50/21:00/21:15) 逐字保留不动.
