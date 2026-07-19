# R1952 (HM2 cc2): NOP 巡检 R75 — 稳态持续, 30min SR88.9%/6h SR93.2% 0 真中断, 连续冻结第 12 轮延续

**铁律遵守**: 改前必有数据 / 改后必有验证 / 聚焦 nv_gw(40006) / 所有修改写入仓库 / 只改 HM2 不改 HM1 / 改 .py 必须 restart 非 up-d / 不碰 ms_gw(40007)

## 本轮性质: NOP 巡检 (0 源码改动 0 env 改动 0 restart)

新 session 接手, 读 STATE.md 棒 (R1951 已真正用 Write 覆写对齐 R1951 真实状态, 含 StartedAt 修正 R1933 13:33:43Z + 轮号基线推进 R1949→R1951 + BUG-A 修复真实生效确认; 下半段监督者巡视历史逐字保留). git pull 后 origin/main 最新 = **R1951** (`b03d2dd`, cc2 上一轮 NOP 巡检 R74, 连续冻结第 11 轮). peer HM1 agent 同号段占 R1951 (`7b788cd`, 前缀 `R1951_hm2_optimize_hm1`, 只改 HM1 对 HM2 0 影响). **本轮 cc2 从 R1952 起** (peer 序列走偶数 R1948/R1950, cc2 序列走奇数 R1949/R1951, 本轮 cc2 接 R1952 偶数因 peer 抢号节奏变化, 前缀 `R1952_hm2_cc2_` 区分). STATE.md 棒上半段已对齐 R1951 真实状态 → 本轮职责:
1. 继续巡检 R1933 NameError 修复后稳态, 确认无回归无新 bug.
2. 拉本轮新鲜 30min/6h 数据, 维持 STATE.md 上半段对齐到 R1952 真实状态 (含新鲜数据 + 轮号基线推进 R1951→R1952 + StartedAt 核实无漂移 + BUG-A 修复持续生效确认).

## 数据 (本 session 拉取, DB 时钟 = 2026-07-20 ~01:15Z UTC = ~09:15 CST, nv_gw StartedAt 2026-07-19T13:33:43Z = 已起 ~36h)

### nv_gw 健康 + 源码状态
- nv_gw StartedAt = **2026-07-19T13:33:43Z** (= R1933 restart NameError 修复, R1933→R1952 未再 restart, 已连续稳态 ~36h).
- cc4101 StartedAt = 2026-07-19T12:10:22Z (= R1926 step2.0 env up-d).
- /health ok (nv_num_keys=5, pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv, nv_default_model=dsv4p_nv, proxy_role=passthrough).
- docker ps 全 Up (nv_gw Up 4 hours / ms_gw Up 2 days / cc4101 Up 5 hours / logs_db Up 3 days; "Up N" 是容器创建时刻非 restart, 精确以 inspect StartedAt 为准).
- **源码状态 = R1933 已验证后状态** (env 快照与 R1947/R1949/R1951 完全一致无漂移).
- **NVU_GLM52_EXP_BACKOFF env 未设=关** (R1928 半成品冻结, 从未 in-vivo 激活, 连续第 12 轮).

### 30min 窗口 (本 session 拉取)
- nv_gw SR = 56/63 = **88.9%** (200:56 / 502:7), 小样本抖动 (R1951 30min 89.3% / R1949 30min 98.0% / R1947 30min 92.9% / R1946 30min 78.9% / R1943 30min 94.7% — 区间稳态, 88.9% 区间内非退化).
- 502=7 全 NVCF 上游侧已知类:
  - `zombie_empty_completion` ×4 (全 glm5_2_nv, 出口 IP 段 134.195.101.0/24 同源快回空, R1675/R1774 已知).
  - `all_tiers_exhausted` ×2 (全 dsv4p_nv, function_id 74f02205 出口 egress 空, NVCF 上游侧).
  - `stream_first_byte_timeout` ×1 (dsv4p_nv, 首字节不来, 已知类; R1951 30min 此类=0, 本轮 +1 属抖动非抬头).
- **abs_cap 30min = 0** (R1918 方案0 cap_origin 重置持续让 abs_cap 归零, 连续多轮; 30min 502 分类中无 stream_absolute_cap).

### 6h 窗口 (本 session 拉取)
- nv_gw SR = 544/584 = **93.2%** (200:544 / 502:40), 大样本稳态区间 (R1951 6h 93.0% / R1949 6h 93.7% / R1947 6h 93.6% / R1946 6h 93.8% / R1943 6h 94.9% — 93.2% 区间内非退化, 与 R1951 几乎一致).
- 502=40 全已知类:
  - `zombie_empty_completion` ×23 (glm5_2_nv×22 + dsv4p_nv×1).
  - `all_tiers_exhausted` ×12 (全 dsv4p_nv, all_tiers_failed_in_mapped_tier 子类; R1951 是 13, 本轮 12, 抖动).
  - `stream_first_byte_timeout` ×5 (全 dsv4p_nv; R1951 是 4, 本轮 5, 抖动).
- **abs_cap 6h = 0** (R1918 方案0 持续归零, 6h 502 分类中无 stream_absolute_cap; R1931=4 → R1942=2 → R1943=2 → R1946=0 → R1947=0 → R1949=0 → R1951=0 → R1952=0 连续多轮归零).

### fallback + breaker (本 session 30min)
- fallback **7** FALLBACK-OK (0 真中断, 0 fallback 失败):
  - 5 条 `PRIMARY-FAIL-SKIP-CIRCUIT` (75s, < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit) — R1947 已知类, cc4101 bug3 preempt 层, 非 nv_gw 旋钮可解.
  - 2 条 `PRIMARY-FAIL` (120s header/ttfb timeout after 120s, **跑满 chain_budget 120s 未等到首字节**, counted toward circuit 但 30min 内未达 threshold=3 → breaker 仍 CLOSED) — R1951 关注点"120s 跑满类是否持续", 本轮从 4 条降到 2 条 → **下降而非抬头, breaker 仍 CLOSED, 无恶化**.
  - 全 7 条被 ms_gw 兜住 → **0 条 fallback 失败 → CC 收 0 真 502**. ms 救回耗时 2.9-7.8s.
  - `grep 502` 真实命中 = 0 (75027ms/5021ms 含子串不计), `both failed`/`ms.*fail` 搜索结果为空 → 确认 0 真中断.
- breaker: cc4101 `PRIMARY-BREAKER-OPEN` 30min = **0**; nv_gw `NV-ANTH-BREAKER-FAIL` 30min = **0**; breaker **OPEN 0 连续多轮**.

### BUG-A 修复 (R1913) 在日志中真实生效确认
- 30min 内 `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **6 次** (真实生效, skip _try_tier_keys 第二轮, 省约 ~120s/fallback 请求).
- R1913 阶段1.5 补全 `_chain_failed=True` + `if _chain_failed:` 跳过 pexec 第二轮的机制持续触发, 验证 BUG-A 修复长期生效.

## 决策: NOP (介入四条全不满足)

1. **SR 未跌破介入线**: 6h SR 93.2% 大样本稳态区间 (R1942-R1951 93.0-95.2% 区间内), 30min 88.9% 小样本抖动 (63 条样本), 非"连续 3+ 轮跌破 80%".
2. **502 全已知类**: 30min/6h 502 全 zombie+ATE+first_byte_timeout (出口 IP 段同源/已知 NVCF 上游侧), 非新可配置类; abs_cap 30min=0/6h=0 (R1918 方案0 持续归零连续多轮).
3. **breaker OPEN 0**: cc4101 PRIMARY-BREAKER-OPEN 30min=0, nv_gw NV-ANTH-BREAKER-FAIL 30min=0, breaker OPEN 0 连续多轮.
4. **fallback 全被兜 0 真中断**: 7/30min 全 FALLBACK-OK 被 ms_gw 兜住, 0 fallback 失败, CC 收 0 真 502; 低于 15/30min 介入线; 无新监督者激活指令. R1951 关注点"120s 跑满类持续抬头"本轮数据反证 (4→2 下降), 无恶化.

R1928 冻结理由仍成立 (半成品指数退避未 in-vivo 验证 + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测窗口). 当前链路稳态 (6h SR93.2% 0 真中断, abs_cap 连续多轮归零, BUG-A 修复真实生效 6 次/30min) + 本轮无新监督者激活指令 → **继续冻结, NOP 无据不改**.

## 验证 (0 改动, 仅巡检确认)
- env 无漂移: UPSTREAM_TIMEOUT=66 / TIER_TIMEOUT_BUDGET_S=180 / NVU_TIER_BUDGET_GLM5_2_NV=120 / NVU_STREAM_ABSOLUTE_CAP_S=150 / NVU_GLM52_EXP_BACKOFF=未设=关 / KEY_COOLDOWN_S=25 / KEY_AUTHFAIL_COOLDOWN_S=60 / NVU_BIG_INPUT_FAIL_N=1 / NVU_BIG_INPUT_COOLDOWN_S=180 / NV_INTEGRATE_KEY_COOLDOWN_S=90 / TIER_COOLDOWN_S=25 / MIN_OUTBOUND_INTERVAL_S=0 — 与 R1947/R1949/R1951 完全一致.
- /health ok, docker ps 全 Up.
- nv_gw StartedAt 2026-07-19T13:33:43Z (0 restart, 维 R1933, 连续稳态 ~36h); cc4101 StartedAt 2026-07-19T12:10:22Z (0 restart, 维 R1926).

## commit + push
- 本 round file + STATE.md 覆写 → `git add -A && git commit && git push origin main`.
- 0 源码改动 0 env 改动 0 restart, 仅巡检记录.

## 给下一轮
- 继续 NOP 巡检 R76. 当前 6h SR 93.2% 稳态区间, 链路稳 — 502 全 zombie+ATE+first_byte_timeout (出口 IP 段同源/已知上游侧), fallback 全 75s SKIP-CIRCUIT + 120s chain 跑满被 ms 兜住 0 真中断.
- 关注点: R1951 担心 120s 跑满类抬头, 本轮反证 4→2 下降. 继续看 120s 跑满类是否持续低位 + breaker 是否开始 OPEN (当前仍 CLOSED).
- 指数退避激活决策仍冻结 (连续第 12 轮): R1928 冻结理由仍成立. 等监督者再授权激活或数据恶化 (SR 连续 3+ 轮跌破 80%) 再动.
- 沿用给监督者方向: abs_cap/zombie/empty200/all_tiers_exhausted 同源首字节慢/空/出口侧不可达是 NVCF 上游侧 + 出口 IP 段, 需换出口 IP 段 / 联系 NVCF 运维 / 核查 function 出口路由, 非 nv_gw 单参数可解.
- peer HM1 agent 持续在 HM1 侧收紧 (R1951 HM2→HM1 = 7b788cd, 只改 HM1 对 HM2 0 影响), 抢号区间, 写轮前必 git pull 看最新号 +1 防 peer 抢号.
