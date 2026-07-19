# R1935 (HM2 cc2): NOP 巡检 R65 — R1933 NameError 修复后稳态持续 (SR100%/30min), 连续第 4 轮冻结指数退避

**铁律遵守**: 改前必有数据 / 改后必有验证 / 聚焦 nv_gw(40006) / 所有修改写入仓库 / 只改 HM2 不改 HM1 / 改 .py 必须 restart 非 up-d / 不碰 ms_gw(40007)

## 本轮性质: NOP 巡检 (0 源码改动 0 env 改动 0 restart)

本轮新 session 接手时发现 STATE.md 基线严重过时 (仍停留 R1931 "连续第 3 轮 NOP 冻结"), 但 git log 实际已推进到 R1934, 中间经历了**两轮真改动** (R1932 + R1933, 由同一 cc2 lineage 的 past session 完成, round 文件已入库):

- **R1932** (commit 2cddb85, peer): `oai_to_anth.py finish()` 补读 `saw_real_tool_call` flag → 根治 CC SDK "tool call could not be parsed (retry also failed)" session 中断 (2d 窗口 132 malformed retry + 3 session 中断).
- **R1933** (本 lineage, 已物理改 + restart + 验证, round 文件 R1934 补提交): 紧急修复 R1928 半成品指数退避裸名 NameError — R1932 restart 重新加载源码让一直潜在未触发的 R1928 半成品 `NVU_GLM52_EXP_BACKOFF` 裸名 (upstream.py:1032 引用但 from import 列表漏) 显形 → nv_gw 每个 glm5_2_nv 请求 NameError crash → 链路半瘫痪. R1933 补 `upstream.py:57` 的 `from .config import (...)` 加 3 个名字 → 根治.
- **R1934** (commit a7ca520): NOP 巡检 R64, 补提交 R1933 round 文件 + 验证 R1933 修复稳态 (SR100%/30min NameError 根治) + R1932 tool-call fix 无回归.

本轮职责: 继续巡检 R1933/R1934 修复后的持续稳态, 确认无回归无新 bug, 0 改动 0 restart.

## 数据 (本 session 拉取, DB 时钟 = 2026-07-19 14:01:43Z UTC, nv_gw StartedAt 13:33:43Z = 已起 28min)

### nv_gw 健康 + 源码状态
- nv_gw StartedAt = **2026-07-19T13:33:43Z** (= R1933 restart, 与 R1934 记录一致, 未被后续再 restart).
- cc4101 StartedAt = 2026-07-19T12:10:22Z (= R1926 step2.0 env up-d).
- /health ok (nv_num_keys=5, pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv).
- docker ps 全 Up.
- **源码状态 = R1933 已验证后状态** (无漂移):
  - upstream.py vs upstream.py.bak.R1933 diff = **仅 1 行** (line 57 R1933 import 行).
  - NVU_GLM52_EXP_BACKOFF env **未设=关** (R1928 半成品冻结, 从未 in-vivo 激活, 连续第 4 轮).

### 30min nv_gw 成功率 (核心指标)
- SR = 47/47 = **100%** (200:47 / 502:**0**) — 持续 R1933 修复后的稳态 (R1934 100%, R1935 100%, 非退化).
- avg 42.2s, max 362s (单条 max 362s 是 NVCF 慢但活, 仍成功).
- 5min 窗口: 14 条全 200, avg 40.5s — **持续在产出 nv 流量** (正反馈核心: 我自己每条请求都在产生 glm5_2_nv 数据), 0 fallback.
- abs_cap 30min = **0** (R1918 方案0 持续归零, 连续多轮).

### 6h 502 分类 (全 NVCF 上游侧已知类)
- zombie_empty_completion×21 / all_tiers_exhausted×12 / stream_first_byte_timeout×4 / stream_absolute_cap×3 — 与 R1934 6h 完全一致 (zombie 出口 IP 段同源 / abs_cap R1918 方案0 已让 30min 归零 6h 残留 / all_tiers_exhausted 链路兜底 / first_byte_timeout 指数退避靶子但未激活), **无新增可配置类**.
- abs_cap 6h detail: 3 条全 status=502 fallback_occurred=f, avg 185.5s, max 195s, **全 fb=f 真 502** (BUG-B 方案0 未动, 持续低频 0.5/h, 低于 R1916 "数据偏少先观测" 的 1.7/h 判断线, 继续攒数据).

### NameError 根治持续验证 (R1933 核心目标)
- since 20m: `grep -cE "NameError"` = **0** ← R1933 import 修复持续生效 (R1934=0, R1935=0).
- since 30m: 4 条 NameError 全集中在 restart 前残留窗口 (日志缓冲边界), 稳态期 0.

### fallback 率 (负向核心指标)
- 30min: 17 FALLBACK-OK (含 restart 恢复窗口 21:31-21:33 的 11 条残留 + 稳态期 21:38-21:59 的 6 条).
- 稳态期 (21:38 后 ~24min): 6 条, 全 `PRIMARY-FAIL-SKIP-CIRCUIT primary timeout after 75s < chain budget 120s` (cc4101 75s 抢断 bug3 preempt 层, 非 nv_gw 旋钮可解) + 1 条 120s 正常超时. 全 FALLBACK-OK (ms 2.5-13s 救回).
- 5min: 1 / 10min: 3 — **稳态 fallback ≤3/10min 低位**, 与 R1934 (≤1/10min) 量级一致, 远好于 R1931 的 10/30min.
- breaker OPEN 8 次全在 21:31-21:33 (R1933 restart 恢复窗口残留), **稳态期 0 新 OPEN** ← cc4101 circuit breaker 已恢复 CLOSED, nv 流量回流 nv_gw.
- **0 真中断**: 17 fallback 全 FALLBACK-OK, 0 fallback 失败 → CC 收 0 真 502.
- 用户诉求 (2026-07-19 01:40) "可以报错但不能让 cc2 中断" 仍达成.

### R1932 tool-call fix 持续无回归 (R1932 目标)
- R1932 restart 时间 = 2026-07-19T13:20:36Z (~42min 前).
- 30min 502=0, 无 zombie 命中 (R1932 改 converter 输出 stop_reason, 当前窗口无 zombie 触发, 无回归验证压力, 但也无新增 "could not be parsed" 信号).
- 6h zombie×21 全在 R1932 restart 前窗口 (NameError crash 期), restart 后稳态期 zombie 量级下降 (30min 0).

## 介入四条全不满足 → NOP 无据不改

1. **SR 100%/30min** (R1934=100%, R1935=100%), 远高于"连续 3+ 轮跌破 80%"介入线 — 链路稳态持续.
2. **502=0/30min**, 6h 502 全 NVCF 上游侧已知类 (zombie/abs_cap/first_byte_timeout/all_tiers_exhausted), 非新可配置类.
3. **breaker OPEN 0 稳态期** (8 次全 restart 恢复窗口残留), 非 nv_gw 旋钮可解的持续 OPEN.
4. **指数退避 env 仍关 (NVU_GLM52_EXP_BACKOFF 未设=关)**, R1928 半成品现在 R1933 import 修复后"可安全冻结加载", 激活决策仍冻结 (连续第 4 轮), 无新监督者激活指令. R1928 冻结理由 (半成品未 in-vivo 验证 + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测) 仍成立.

## 为何本轮 = NOP 巡检而非激活指数退避 / 动 BUG-B 方案0

- **链路刚经历 R1932/R1933 改动 + restart, 处于恢复稳固期** (StartedAt 13:33:43Z = 28min 前), 不宜立即再动结构层. 小步快走, 一轮只动一个点, 当前无紧急.
- **BUG-B 方案0 (abs_cap fb=f 时 peek 通过后重置 cap_origin)** 虽监督者 19:50 已给最小修复 (1 行, 风险极低, R1818 bug7 逻辑补), 但当前 abs_cap 频次 3 条/6h = 0.5/h, 远低于 R1916 "数据偏少先观测" 的 1.7/h 判断线. 铁律1 有数据但数据稀疏, 攒样本后再动. 与 R1934 决定一致.
- **指数退避激活**: 当前 SR100% 0 真中断, 链路稳态, 边际收益小. 激活需同步 4 个坑 (chain_budget 120→420 / cc4101 header 60→450 / post-200 软挂换 key 未实现 / abs_cap 150→250+), 风险/收益不对等. 等监督者再授权激活或数据恶化 (SR 连续 3+ 轮跌破 80%) 再动.

## 验证

- env 无漂移 (与 R1934 完全一致): UPSTREAM_TIMEOUT=66 / TIER_TIMEOUT_BUDGET_S=180 / NVU_TIER_BUDGET_GLM5_2_NV=120 / NVU_STREAM_ABSOLUTE_CAP_S=150 / NVU_GLM52_EXP_BACKOFF 未设=关 / MIN_OUTBOUND_INTERVAL_S=0 / KEY_COOLDOWN_S=25 / TIER_COOLDOWN_S=25.
- cc4101 env 无漂移: PRIMARY_HEADER_TIMEOUT=60 (分档 25/60/120) / CC4101_STREAM_TOTAL_DEADLINE_S=480 (R1926) / CC4101_PRIMARY_SKIP_S=30 / CC4101_PRIMARY_FAIL_THRESHOLD=3.
- /health ok, docker ps 全 Up, nv_gw StartedAt 13:33:43Z (0 restart 本轮), cc4101 StartedAt 12:10:22Z.
- 0 源码改动 0 env 改动 0 restart (NOP).

## 预期效果

- 无改动, 预期 SR 维持 100%/30min 稳态, fallback 维持 ≤3/10min 低位, breaker OPEN 0 稳态期, 0 真中断.
- 下一轮若数据仍稳, 继续 NOP 巡检 R66.

## 24h 观测清单

- [ ] SR 维持 ≥95% (30min 窗口)
- [ ] fallback ≤5/10min (稳态期, 排除 restart 恢复窗口)
- [ ] breaker OPEN 0 (稳态期)
- [ ] 0 真中断 (0 fallback 失败)
- [ ] NameError 0 (R1933 持续)
- [ ] abs_cap 频次: 若从 0.5/h 升至 ≥1.7/h, 考虑动 BUG-B 方案0 (peek 通过后重置 cap_origin)
- [ ] cc2 jsonl 无新增 "could not be parsed (retry also failed)" (R1932 持续)
